from __future__ import annotations

import asyncio
import json
import logging
import os
import urllib.parse
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress
from datetime import datetime
from typing import Any, Literal

import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncAzureOpenAI
from pydantic import BaseModel, Field
from starlette.responses import StreamingResponse

from app.security import _limiter, validate_and_sanitize

try:
    from app.auth import TEAMS_SSO_ENABLED, get_obo_exchange
except ImportError:
    TEAMS_SSO_ENABLED = False

    def get_obo_exchange():
        return None
from app.actions_service import ActionsService
from app.actions_store import compute_action_metrics, get_actions_store
from app.auth_router import router as auth_router
from app.bitemporal_store import get_bitemporal_store
from app.cache import get as cache_get
from app.cache import set as cache_set
from app.connector_runtime import (
    build_connector_registry,
    connector_runtime_summary,
    load_connector_config,
)
from app.connector_sync_store import get_connector_sync_store
from app.event_signal_store import get_event_signal_store
from connectors.adapters.webhook_adapter import WebhookAdapter, WebhookEnvelope
from connectors.registry import ConnectorRegistry
from connectors.types import Capability, SyncCursor

CONNECTOR_CONFIG = load_connector_config()
CONNECTOR_REGISTRY: ConnectorRegistry = build_connector_registry(CONNECTOR_CONFIG)
CONNECTOR_RUNTIME = connector_runtime_summary(CONNECTOR_REGISTRY, CONNECTOR_CONFIG)
BITEMPORAL_STORE = get_bitemporal_store()
CONNECTOR_SYNC_STORE = get_connector_sync_store()
EVENT_SIGNAL_STORE = get_event_signal_store()
ACTION_STORE = get_actions_store()
ACTION_SERVICE = ActionsService(store=ACTION_STORE, registry=CONNECTOR_REGISTRY)
WEBHOOK_SOURCE_SECRET_ENV = os.getenv("WEBHOOK_SOURCE_SECRET_ENV", "WEBHOOK_SHARED_SECRET")
WEBHOOK_ADAPTER = WebhookAdapter(source_id="webhook")

logger = logging.getLogger("orchestrator")
logger.info("Connector runtime initialized: %s", CONNECTOR_RUNTIME)

SCHEDULER_TASK: asyncio.Task[Any] | None = None
SCHEDULER_WORKER_ID = os.getenv("CONNECTOR_SYNC_WORKER_ID", f"worker-{uuid.uuid4()}")
SCHEDULER_POLL_SECONDS = max(2, int(os.getenv("CONNECTOR_SYNC_POLL_SECONDS", "5")))
SCHEDULER_LEASE_SECONDS = max(10, int(os.getenv("CONNECTOR_SYNC_LEASE_SECONDS", "60")))


def _normalize_schedule(source_id: str, entity_type: str, row: dict[str, Any] | None) -> dict[str, Any]:
    if not row:
        return {
            "source_id": source_id,
            "entity_type": entity_type,
            "scheduled": False,
        }
    return {
        "source_id": row["source_id"],
        "entity_type": row["entity_type"],
        "scheduled": True,
        "schedule_id": row["id"],
        "enabled": row["enabled"],
        "limit": row["limit_value"],
        "interval_seconds": row["interval_seconds"],
        "next_run_at": row["next_run_at"],
        "lease_owner": row["lease_owner"],
        "lease_until": row["lease_until"],
        "last_status": row["last_status"],
        "last_error": row["last_error"],
        "last_run_started_at": row["last_run_started_at"],
        "last_run_finished_at": row["last_run_finished_at"],
        "updated_at": row["updated_at"],
    }


async def _durable_scheduler_loop() -> None:
    logger.info(
        "Starting durable connector scheduler loop worker_id=%s poll=%ss lease=%ss",
        SCHEDULER_WORKER_ID,
        SCHEDULER_POLL_SECONDS,
        SCHEDULER_LEASE_SECONDS,
    )
    while True:
        claimed = CONNECTOR_SYNC_STORE.claim_due_schedule(
            worker_id=SCHEDULER_WORKER_ID,
            lease_seconds=SCHEDULER_LEASE_SECONDS,
        )
        if not claimed:
            await asyncio.sleep(SCHEDULER_POLL_SECONDS)
            continue

        schedule_id = int(claimed["id"])
        try:
            _run_sync_once(
                source_id=str(claimed["source_id"]),
                entity_type=str(claimed["entity_type"]),
                limit=int(claimed["limit_value"]),
                use_saved_cursor=True,
            )
            CONNECTOR_SYNC_STORE.complete_claimed_schedule(
                schedule_id=schedule_id,
                worker_id=SCHEDULER_WORKER_ID,
                success=True,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "durable scheduled sync failed schedule_id=%s source=%s entity=%s error=%s",
                schedule_id,
                claimed.get("source_id"),
                claimed.get("entity_type"),
                exc,
            )
            CONNECTOR_SYNC_STORE.complete_claimed_schedule(
                schedule_id=schedule_id,
                worker_id=SCHEDULER_WORKER_ID,
                success=False,
                error_text=str(exc),
            )

        await asyncio.sleep(0)


async def _start_scheduler() -> None:
    global SCHEDULER_TASK
    if SCHEDULER_TASK is None or SCHEDULER_TASK.done():
        SCHEDULER_TASK = asyncio.create_task(_durable_scheduler_loop())


async def _stop_scheduler() -> None:
    global SCHEDULER_TASK
    task = SCHEDULER_TASK
    if task is not None:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
    SCHEDULER_TASK = None


async def _scheduled_sync_loop(*_args: Any, **_kwargs: Any) -> None:
    """Deprecated in Phase 5: in-memory loops replaced by durable DB-backed scheduler."""
    return None


def _schedule_key(source_id: str, entity_type: str) -> str:
    return f"{source_id}:{entity_type}"


def _run_connector_fetch(
    *,
    source_id: str,
    entity_type: str,
    limit: int,
    cursor_value: str | None,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    if not CONNECTOR_REGISTRY.has(source_id):
        raise HTTPException(status_code=404, detail=f"Unknown connector '{source_id}'.")

    reg = CONNECTOR_REGISTRY.get_registration(source_id)
    if not reg.enabled:
        raise HTTPException(status_code=409, detail=f"Connector '{source_id}' is disabled.")

    cursor = SyncCursor(value=cursor_value) if cursor_value else None
    page = reg.connector.fetch(entity_type=entity_type, cursor=cursor, limit=limit)
    persist_result = BITEMPORAL_STORE.persist_page(
        source_id=source_id,
        entity_type=entity_type,
        records=page.records,
        idempotency_key=idempotency_key,
    )

    next_cursor = page.next_cursor.value if page.next_cursor else None
    if next_cursor is not None:
        CONNECTOR_SYNC_STORE.upsert_cursor(source_id, entity_type, next_cursor)

    return {
        "source_id": source_id,
        "entity_type": entity_type,
        "count": len(page.records),
        "persisted": persist_result.get("persisted", 0),
        "duplicate": bool(persist_result.get("duplicate", False)),
        "store_backend": persist_result.get("backend"),
        "idempotency_key": persist_result.get("idempotency_key"),
        "next_cursor": next_cursor,
        "records": page.records,
    }


def _run_sync_once(
    *,
    source_id: str,
    entity_type: str,
    limit: int,
    use_saved_cursor: bool,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    run_id = str(uuid.uuid4())
    run_row_id = CONNECTOR_SYNC_STORE.start_run(run_id=run_id, source_id=source_id, entity_type=entity_type)

    cursor_value = CONNECTOR_SYNC_STORE.get_cursor(source_id, entity_type) if use_saved_cursor else None

    try:
        result = _run_connector_fetch(
            source_id=source_id,
            entity_type=entity_type,
            limit=limit,
            cursor_value=cursor_value,
            idempotency_key=idempotency_key,
        )
        CONNECTOR_SYNC_STORE.finish_run(
            run_row_id,
            status="success",
            fetched_count=int(result.get("count", 0)),
            persisted_count=int(result.get("persisted", 0)),
            duplicate=bool(result.get("duplicate", False)),
        )
        return {"run_id": run_id, **result}
    except Exception as exc:  # noqa: BLE001
        CONNECTOR_SYNC_STORE.finish_run(
            run_row_id,
            status="failed",
            fetched_count=0,
            persisted_count=0,
            duplicate=False,
            error_text=str(exc),
        )
        CONNECTOR_SYNC_STORE.add_dead_letter(
            source_id=source_id,
            entity_type=entity_type,
            cursor_value=cursor_value,
            payload={"limit": limit, "idempotency_key": idempotency_key},
            error_text=str(exc),
        )
        raise


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    await _start_scheduler()
    try:
        yield
    finally:
        await _stop_scheduler()


app = FastAPI(title="orchestrator", version="0.4.0", lifespan=lifespan)


def _connector_health_snapshot() -> dict[str, Any]:
    report: dict[str, Any] = {}
    for source_id, health in CONNECTOR_REGISTRY.health_report().items():
        report[source_id] = {
            "ok": health.ok,
            "detail": health.detail,
            "checked_at": health.checked_at.isoformat(),
        }
    return report


def _connector_config_snapshot() -> list[dict[str, Any]]:
    return [
        {
            "type": spec.type,
            "source_id": spec.source_id,
            "enabled": spec.enabled,
            "tenant_id": spec.tenant_id,
            "base_url": spec.base_url,
            "api_key_env": spec.api_key_env,
        }
        for spec in CONNECTOR_CONFIG.connectors
    ]

_cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MCP_SQL_URL = os.getenv("MCP_SQL_URL", "http://localhost:5000/mcp")
MCP_POSTGRESQL_URL = os.getenv("MCP_POSTGRESQL_URL", "")
MCP_FILES_URL = os.getenv("MCP_FILES_URL", "http://localhost:8001/mcp")
MCP_MAIL_URL = os.getenv("MCP_MAIL_URL", "http://localhost:8002/mcp")
MCP_ONEDRIVE_URL = os.getenv("MCP_ONEDRIVE_URL", "http://localhost:8003/mcp")
MCP_MEMORY_URL = os.getenv("MCP_MEMORY_URL", "http://localhost:8004/mcp")
MCP_KB_URL = os.getenv("MCP_KB_URL", "http://localhost:8005/mcp")
MCP_DOC_URL = os.getenv("MCP_DOC_URL", "http://localhost:8006/mcp")
MCP_ANALYTICS_URL = os.getenv("MCP_ANALYTICS_URL", "http://localhost:8007/mcp")
MCP_DASHBOARD_URL = os.getenv("MCP_DASHBOARD_URL", "")

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")


def _base(url: str) -> str:
    return url.rsplit("/mcp", 1)[0] if url.endswith("/mcp") else url


MCP_ENDPOINTS = {
    "sql": MCP_SQL_URL,
    "files": MCP_FILES_URL,
    "mail": MCP_MAIL_URL,
    "onedrive": MCP_ONEDRIVE_URL,
    "memory": MCP_MEMORY_URL,
    "knowledge_base": MCP_KB_URL,
    "document_generation": MCP_DOC_URL,
    "analytics": MCP_ANALYTICS_URL,
}
if MCP_POSTGRESQL_URL:
    MCP_ENDPOINTS["postgresql"] = MCP_POSTGRESQL_URL
if MCP_DASHBOARD_URL:
    MCP_ENDPOINTS["dashboard"] = MCP_DASHBOARD_URL

# ─── Runtime Admin Config ─────────────────────────────────────────────
MCP_ENABLED: dict[str, bool] = dict.fromkeys(MCP_ENDPOINTS, True)
_MCP_DISABLED_AT: dict[str, float] = {}  # Timestamp when auto-disabled (for auto-recovery)
MCP_COOLDOWN_SECONDS = 30  # Auto-re-enable after this many seconds

_TOOL_NAME_TO_KEY: dict[str, str] = {
    "query_files": "files",
    "query_mail": "mail",
    "query_onedrive": "onedrive",
    "query_sql": "sql",
    "query_postgresql": "postgresql",
    "query_knowledge_base": "knowledge_base",
    "query_memory": "memory",
    "query_document_generation": "document_generation",
    "query_analytics": "analytics",
    "query_dashboard": "dashboard",
    "get_connector_freshness": "sql",
    "get_entity_lineage": "sql",
    "get_confidence_breakdown": "sql",
    "query_as_of": "sql",
    "diff_between": "sql",
}

_TOOL_LABELS: dict[str, str] = {
    "query_files": "Files → File Share",
    "query_mail": "Mail → Outlook",
    "query_onedrive": "OneDrive → Documents",
    "query_sql": "SQL → Property Database",
    "query_postgresql": "PostgreSQL → Operational DB",
    "query_knowledge_base": "Knowledge Base → Policies",
    "query_memory": "Memory → User Context",
    "query_document_generation": "Docs → Report Generation",
    "query_analytics": "Analytics → MF KPIs & Trends",
    "query_dashboard": "Dashboard → Portfolio Views",
    "get_connector_freshness": "Bitemporal → Connector Freshness",
    "get_entity_lineage": "Bitemporal → Entity Lineage",
    "get_confidence_breakdown": "Bitemporal → Confidence",
    "query_as_of": "Bitemporal → As-Of Query",
    "diff_between": "Bitemporal → Diff",
}

# Tool schemas presented to the Azure OpenAI model
TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "query_files",
            "description": "Search or list files from the local file share / Azure Files storage.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query describing what files to find."},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_mail",
            "description": "Search or retrieve emails from the Office 365 Outlook mailbox.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Email search query, e.g. sender, subject, or topic."},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_onedrive",
            "description": "Search or list files and documents stored in OneDrive.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query for OneDrive files or documents."},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_sql",
            "description": "Query the SQL database for multifamily properties, contacts, deals, and brokerage activities.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural language query for the SQL database."},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_postgresql",
            "description": "Query a PostgreSQL database for relational operational data and schema/table insights.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural language query for PostgreSQL, or prefix with 'sql:' for read-only SQL."},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_knowledge_base",
            "description": "Search the company knowledge base for SOPs (Standard Operating Procedures), employee handbook policies, and governance documents. ALWAYS use this tool when the user asks about company rules, procedures, HR policies, IT security, workplace conduct, expense reimbursement, vacation, onboarding, or any official company documentation. Do NOT use query_files or query_onedrive for policies, SOPs, or handbook topics.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural language query about company policies, SOPs, or handbook topics."},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_memory",
            "description": "Retrieve the user's personal context, profile, preferences, recent topics, bookmarks, and role-based defaults from the Memory MCP. Use this when the user asks about 'my' information, their role, preferences, bookmarks, recent history, or when you need to personalize a response based on who they are.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural language query about the user's profile, preferences, bookmarks, or recent history."},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_document_generation",
            "description": "Generate structured documents, reports, executive summaries, board briefings, sales reports, and security assessments. Use this when the user asks to create, generate, draft, or write a document, report, summary, briefing, or any formatted content. Returns pre-built document templates with sections, metrics, and action items.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural language query describing the document or report to generate, e.g. 'executive summary', 'board briefing', 'sales report', 'security assessment'."},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_analytics",
            "description": "Retrieve multifamily and brokerage analytics — portfolio KPIs, deal pipeline metrics, market trends, and agent performance. Use this when the user asks about occupancy, cap rates, NOI, deal stages, commissions, or market data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural language query for analytics, e.g. 'portfolio performance', 'deal pipeline KPIs', 'Memphis market trends', 'commission tracker'."},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_dashboard",
            "description": "Returns structured dashboard views for multifamily brokerage — portfolio overview, deal pipeline funnel, market analytics, and upcoming activities. Use this when the user asks for a dashboard view, summary, or snapshot of the business.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural language query for dashboard view, e.g. 'portfolio dashboard', 'pipeline summary', 'market view', 'my activities'."},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_connector_freshness",
            "description": "Get connector/entity freshness lag and latest recorded timestamps.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Optional JSON: {\"source_id\":\"...\",\"entity_type\":\"...\",\"limit\":100}."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_entity_lineage",
            "description": "Get lineage/history + audit chain for a specific source record.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "JSON: {\"source_id\":\"...\",\"entity_type\":\"...\",\"source_record_id\":\"...\",\"limit\":50}."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_confidence_breakdown",
            "description": "Get confidence statistics grouped by source/entity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Optional JSON: {\"source_id\":\"...\",\"entity_type\":\"...\"}."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_as_of",
            "description": "Return entity snapshot records as-of a system timestamp.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "JSON: {\"as_of\":\"ISO-8601\",\"source_id\":\"...\",\"entity_type\":\"...\",\"limit\":100}."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "diff_between",
            "description": "Compute added/removed/changed records between two as-of timestamps.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "JSON: {\"t1\":\"ISO-8601\",\"t2\":\"ISO-8601\",\"source_id\":\"...\",\"entity_type\":\"...\",\"limit\":100}."}
                },
                "required": ["query"]
            }
        }
    },
]

_TOOL_TO_ROUTE: dict[str, str] = {
    "query_files": "files",
    "query_mail": "mail",
    "query_onedrive": "onedrive",
    "query_sql": "sql",
    "query_postgresql": "postgresql",
    "query_knowledge_base": "knowledge_base",
    "query_memory": "memory",
    "query_document_generation": "document_generation",
    "query_analytics": "analytics",
    "query_dashboard": "dashboard",
    "get_connector_freshness": "sql",
    "get_entity_lineage": "sql",
    "get_confidence_breakdown": "sql",
    "query_as_of": "sql",
    "diff_between": "sql",
}


class ChatRequest(BaseModel):
    message: str
    user_id: str | None = None
    history: list[dict[str, Any]] | None = None
    teams_token: str | None = None


class ChatResponse(BaseModel):
    reply: str
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    mcp_results: list[dict[str, Any]] = Field(default_factory=list)


class PerformanceDashboardResponse(BaseModel):
    generated_at: str
    overview: dict[str, Any]
    pipeline: dict[str, Any]
    activities: dict[str, Any]
    top_properties_by_noi: list[dict[str, Any]]


# ─── SSE Helpers ──────────────────────────────────────────────────────

def _sse(data: dict[str, Any]) -> str:
    return f"data: {json.dumps(data)}\n\n"


def _summarize_mcp_result(result: dict[str, Any]) -> str:
    """Produce a short human-readable summary of an MCP tool result."""
    if result.get("error"):
        return f"Error: {result['error'][:80]}"
    if "files" in result and isinstance(result["files"], list):
        return f"Found {len(result['files'])} file(s)"
    if "messages" in result and isinstance(result["messages"], list):
        return f"Found {len(result['messages'])} email(s)"
    if "companies" in result and isinstance(result["companies"], list):
        return f"Found {len(result['companies'])} companies, {len(result.get('contacts', []))} contacts"
    if "documents" in result and isinstance(result["documents"], list):
        return f"Found {len(result['documents'])} policy document(s)"
    if "generated_documents" in result and isinstance(result["generated_documents"], list):
        docs = result["generated_documents"]
        titles = ", ".join(d.get("title", "?") for d in docs[:3])
        return f"Generated {len(docs)} doc(s): {titles}"
    if "kpi_cards" in result and isinstance(result["kpi_cards"], list):
        return f"Loaded {len(result['kpi_cards'])} KPI(s)"
    if "profile" in result:
        return f"Loaded profile for {result['profile'].get('name', 'user')}"
    summary = result.get("summary", "")
    return str(summary)[:120] if summary else "Data retrieved"


# ─── MCP Calling ──────────────────────────────────────────────────────

async def _call_mcp(tool_name: str, query: str, user_id: str | None = None) -> dict[str, Any]:
    local_bitemporal_tools = {
        "get_connector_freshness",
        "get_entity_lineage",
        "get_confidence_breakdown",
        "query_as_of",
        "diff_between",
    }
    if tool_name in local_bitemporal_tools:
        parsed: dict[str, Any] = {}
        if query:
            try:
                parsed = json.loads(query)
            except json.JSONDecodeError as exc:
                return {"error": f"Invalid JSON query payload for {tool_name}: {exc.msg}"}

        try:
            if tool_name == "get_connector_freshness":
                return BITEMPORAL_STORE.get_connector_freshness(
                    source_id=parsed.get("source_id"),
                    entity_type=parsed.get("entity_type"),
                    limit=int(parsed.get("limit", 100)),
                )
            if tool_name == "get_entity_lineage":
                return BITEMPORAL_STORE.get_entity_lineage(
                    source_id=str(parsed["source_id"]),
                    entity_type=str(parsed["entity_type"]),
                    source_record_id=str(parsed["source_record_id"]),
                    limit=int(parsed.get("limit", 50)),
                )
            if tool_name == "get_confidence_breakdown":
                return BITEMPORAL_STORE.get_confidence_breakdown(
                    source_id=parsed.get("source_id"),
                    entity_type=parsed.get("entity_type"),
                )
            if tool_name == "query_as_of":
                return BITEMPORAL_STORE.query_as_of(
                    as_of=str(parsed["as_of"]),
                    source_id=parsed.get("source_id"),
                    entity_type=parsed.get("entity_type"),
                    limit=int(parsed.get("limit", 100)),
                )
            if tool_name == "diff_between":
                return BITEMPORAL_STORE.diff_between(
                    t1=str(parsed["t1"]),
                    t2=str(parsed["t2"]),
                    source_id=parsed.get("source_id"),
                    entity_type=parsed.get("entity_type"),
                    limit=int(parsed.get("limit", 100)),
                )
        except KeyError as exc:
            return {"error": f"Missing required field for {tool_name}: {exc.args[0]}"}
        except Exception as exc:  # noqa: BLE001
            return {"error": f"{tool_name} failed: {exc}"}

    route = _TOOL_TO_ROUTE[tool_name]

    if route not in MCP_ENDPOINTS:
        return {"error": f"MCP {route} is not configured."}

    # Auto-recovery: re-enable after cooldown
    if not MCP_ENABLED.get(route, True):
        import time
        disabled_at = _MCP_DISABLED_AT.get(route, 0)
        if time.time() - disabled_at >= MCP_COOLDOWN_SECONDS:
            MCP_ENABLED[route] = True
            _MCP_DISABLED_AT.pop(route, None)
            logger.info("MCP %s auto-recovered — re-enabled after cooldown", route)
        else:
            remaining = int(MCP_COOLDOWN_SECONDS - (time.time() - disabled_at))
            return {"error": f"MCP {route} temporarily unavailable — retrying in ~{remaining}s."}

    cache_key = (query, user_id or "")
    cached = cache_get("mcp", route, *cache_key)
    if cached is not None:
        return cached

    endpoint = f"{_base(MCP_ENDPOINTS[route])}/mcp/query"
    payload: dict[str, Any] = {"query": query}
    if user_id:
        payload["user_id"] = user_id

    result: dict[str, Any]
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
            resp = await client.post(endpoint, json=payload)
            if resp.status_code in (301, 302, 307, 308) and "location" in resp.headers:
                resp = await client.post(resp.headers["location"], json=payload)
            if resp.status_code >= 400:
                raise MCPError(f"MCP {route} returned {resp.status_code}: {resp.text[:200]}")
            if not resp.content:
                raise MCPError(f"MCP {route} returned empty body")
            result = resp.json()
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        import time
        MCP_ENABLED[route] = False
        _MCP_DISABLED_AT[route] = time.time()
        logger.warning("MCP %s unreachable — auto-disabling for %ss: %s", route, MCP_COOLDOWN_SECONDS, exc)
        return {"error": f"MCP {route} unreachable — auto-disabled for {MCP_COOLDOWN_SECONDS}s. {exc!s}"}
    except MCPError as exc:
        import time
        MCP_ENABLED[route] = False
        _MCP_DISABLED_AT[route] = time.time()
        logger.warning("MCP %s error — auto-disabling for %ss: %s", route, MCP_COOLDOWN_SECONDS, exc)
        return {"error": f"MCP {route} error — auto-disabled for {MCP_COOLDOWN_SECONDS}s. {exc!s}"}
    except Exception as exc:
        return {"error": f"MCP {route} request failed: {type(exc).__name__}: {exc!s}"}

    if "error" not in result:
        cache_set("mcp", result, 60, route, *cache_key)
    return result


class MCPError(Exception):
    """HTTP or protocol error from an MCP server."""


# ─── Streaming Chat ───────────────────────────────────────────────────

async def _stream_chat_response(
    payload: ChatRequest,
    rate_key: str,
) -> AsyncGenerator[str, None]:
    """Core streaming chat logic: SSE generator yielding events."""
    # --- Auto-fetch memory context ---
    memory_context = ""
    if payload.user_id and MCP_MEMORY_URL and MCP_ENABLED.get("memory", True):
        try:
            mem_result = await _call_mcp("query_memory", payload.message, payload.user_id)
            if "error" not in mem_result:
                profile = mem_result.get("profile", {})
                prefs = mem_result.get("preferences", {})
                snippets = mem_result.get("relevant_snippets", [])
                parts: list[str] = []
                if profile.get("name"):
                    parts.append(f"User: {profile['name']} ({profile.get('role', 'User')})")
                if profile.get("department"):
                    parts.append(f"Department: {profile['department']}")
                focus = prefs.get("data_focus", [])
                if focus:
                    parts.append(f"Focus areas: {', '.join(focus)}")
                style = prefs.get("communication_style", "")
                if style:
                    parts.append(f"Communication preference: {style}")
                if snippets:
                    parts.append("Recent context: " + "; ".join(
                        s["content"] if isinstance(s.get("content"), str) else s.get("content", {}).get("reason", "")
                        for s in snippets[:3]
                    ))
                memory_context = "\n".join(parts)
        except Exception as exc:
            logger.warning("Memory context fetch failed: %s", exc)

    user_hint = f" The current user is {payload.user_id}." if payload.user_id else ""
    system_content = (
        "You are a helpful enterprise Q&A assistant."
        + user_hint
        + (f"\n\nUser Context (for personalization only — NOT a substitute for data retrieval):\n{memory_context}" if memory_context else "")
        + "\n\nIMPORTANT: When the user asks for files, documents, emails, contacts, companies, "
        "analytics, KPIs, pipeline data, metrics, SQL data, or any factual business information, "
        "you MUST call the appropriate tool to retrieve real data. Never answer a data query from "
        "memory context alone — the context is for personalization only. "
        "Always use the available tools to fetch actual data before answering: "
        "query_files for file listings, query_mail for emails, query_onedrive for OneDrive files, "
        "query_sql for CRM/contacts/companies/pipeline/metrics, "
        "query_postgresql for PostgreSQL operational tables and read-only SQL, "
        "query_knowledge_base for SOPs/policies/handbook, "
        "query_analytics for KPIs/trends/insights, "
        "query_document_generation for creating reports/documents, "
        "query_memory for user profile/bookmarks (auto-provided)."
        "\n\nBitemporal policy: for connector/entity recency, provenance, trust, or historical comparison, "
        "use tools get_connector_freshness, get_entity_lineage, get_confidence_breakdown, query_as_of, and diff_between. "
        "When responding with facts from connector/entity data, include freshness timestamp/lag, source lineage, and confidence. "
        "If freshness is stale or confidence is low for the claim, clearly warn and avoid overstating certainty."
    )

    messages: list[dict[str, Any]] = [{"role": "system", "content": system_content}]
    if payload.history:
        for h in payload.history:
            content = h.get("content") or h.get("text", "")
            role = h.get("role", "user")
            if role in ("user", "assistant", "system"):
                messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": payload.message})

    if not AZURE_OPENAI_ENDPOINT or not AZURE_OPENAI_API_KEY:
        yield _sse({"type": "error", "message": "Azure OpenAI not configured. Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY."})
        return

    openai_client = AsyncAzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version="2024-02-01",
    )

    yield _sse({"type": "start"})

    tool_calls_log: list[dict[str, Any]] = []
    mcp_results_log: list[dict[str, Any]] = []
    full_reply = ""
    max_turns = 5

    for _turn in range(max_turns):
        accumulated_tool_calls: list[dict[str, Any]] = []

        try:
            stream = await openai_client.chat.completions.create(
                model=AZURE_OPENAI_DEPLOYMENT,
                messages=messages,
                tools=_active_tools(),
                tool_choice="auto",
                stream=True,
                stream_options={"include_usage": False},
            )
        except Exception as exc:
            yield _sse({"type": "error", "message": f"OpenAI API error: {exc!s}"})
            return

        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if not delta:
                continue

            # Stream content tokens
            if delta.content:
                full_reply += delta.content
                yield _sse({"type": "token", "content": delta.content})

            # Accumulate tool call deltas
            if delta.tool_calls:
                for tc_delta in delta.tool_calls:
                    idx = tc_delta.index if tc_delta.index is not None else 0
                    while len(accumulated_tool_calls) <= idx:
                        accumulated_tool_calls.append({
                            "id": "",
                            "type": "function",
                            "function": {"name": "", "arguments": ""},
                        })
                    ac = accumulated_tool_calls[idx]
                    if tc_delta.id:
                        ac["id"] = tc_delta.id
                    if tc_delta.function:
                        if tc_delta.function.name:
                            ac["function"]["name"] = tc_delta.function.name
                        if tc_delta.function.arguments:
                            ac["function"]["arguments"] += tc_delta.function.arguments

        # After stream: check for tool calls
        if accumulated_tool_calls:
            # Build assistant message with accumulated tool calls
            assistant_msg: dict[str, Any] = {"role": "assistant"}
            if full_reply:
                assistant_msg["content"] = full_reply
            assistant_msg["tool_calls"] = accumulated_tool_calls
            messages.append(assistant_msg)

            for tc in accumulated_tool_calls:
                name = tc["function"]["name"]
                try:
                    args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    args = {}
                query = args.get("query", "")

                label = _TOOL_LABELS.get(name, name)
                yield _sse({"type": "tool", "name": name, "label": label, "status": "calling"})

                mcp_result = await _call_mcp(name, query, payload.user_id)
                route = _TOOL_TO_ROUTE.get(name, "")
                mcp_result = _augment_files_with_urls(mcp_result, route)

                summary = _summarize_mcp_result(mcp_result)
                yield _sse({"type": "tool", "name": name, "label": label, "status": "done", "summary": summary})

                tool_calls_log.append({"name": name, "args": args})
                if route != "memory":
                    mcp_results_log.append(mcp_result)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": json.dumps(mcp_result),
                })

            # Reset reply text — model will continue answering after tool results
            full_reply = ""
            continue  # Next turn — model processes tool results

        # No tool calls — final answer
        yield _sse({"type": "done", "reply": full_reply, "tool_calls": tool_calls_log, "mcp_results": mcp_results_log})
        return

    # Max turns exhausted
    yield _sse({"type": "done", "reply": full_reply or "I wasn't able to fully answer after multiple rounds. Please try rephrasing.", "tool_calls": tool_calls_log, "mcp_results": mcp_results_log})


async def _collect_batch(generator: AsyncGenerator[str, None]) -> ChatResponse:
    """Consume the SSE stream and produce a single ChatResponse."""
    reply = ""
    tool_calls: list[dict[str, Any]] = []
    mcp_results: list[dict[str, Any]] = []
    async for event_str in generator:
        for line in event_str.strip().split("\n"):
            if not line.startswith("data: "):
                continue
            try:
                event = json.loads(line[6:])
            except json.JSONDecodeError:
                continue
            if event.get("type") == "done":
                reply = event.get("reply", reply)
                tool_calls = event.get("tool_calls", [])
                mcp_results = event.get("mcp_results", [])
            elif event.get("type") == "error":
                reply = f"Error: {event.get('message', 'Unknown error')}"
    return ChatResponse(reply=reply or "No response", tool_calls=tool_calls, mcp_results=mcp_results)


# ─── Routes ───────────────────────────────────────────────────────────

@app.get("/")
def root() -> dict[str, str]:
    return {"service": "orchestrator", "status": "ok", "mode": "openai-tool-calling-sse"}


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "healthy",
        "connectors": {
            "runtime": CONNECTOR_RUNTIME,
            "config": _connector_config_snapshot(),
            "health": _connector_health_snapshot(),
        },
        "reliability": CONNECTOR_SYNC_STORE.get_reliability_metrics(),
    }


@app.get("/ready")
async def ready() -> dict[str, Any]:
    status: dict[str, Any] = {}
    async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
        for name, mcp_url in MCP_ENDPOINTS.items():
            health_url = f"{_base(mcp_url)}/health"
            try:
                resp = await client.get(health_url)
                entry: dict[str, Any] = {
                    "reachable": resp.status_code == 200,
                    "url": health_url,
                    "status_code": resp.status_code,
                }
                if resp.status_code != 200:
                    entry["body_preview"] = resp.text[:200]
                status[name] = entry
            except Exception as exc:
                status[name] = {"reachable": False, "url": health_url, "error": str(exc)}
    return {"status": "ready", "dependencies": status}


@app.get("/dashboard/performance", response_model=PerformanceDashboardResponse)
async def performance_dashboard(user_id: str | None = None) -> dict[str, Any]:
    overview_result = await _call_mcp("query_dashboard", "overview dashboard summary", user_id)
    pipeline_result = await _call_mcp("query_dashboard", "deal pipeline funnel stage summary", user_id)
    activities_result = await _call_mcp("query_dashboard", "upcoming activities and tasks", user_id)
    portfolio_result = await _call_mcp("query_dashboard", "portfolio properties by noi", user_id)

    overview_data = (overview_result.get("data") or {}) if isinstance(overview_result, dict) else {}
    pipeline_data = (pipeline_result.get("data") or {}) if isinstance(pipeline_result, dict) else {}
    activities_data = (activities_result.get("data") or {}) if isinstance(activities_result, dict) else {}
    portfolio_data = (portfolio_result.get("data") or {}) if isinstance(portfolio_result, dict) else {}

    properties = portfolio_data.get("properties") if isinstance(portfolio_data, dict) else []
    top_properties = []
    if isinstance(properties, list):
        ordered = sorted(
            [p for p in properties if isinstance(p, dict)],
            key=lambda p: float(p.get("noi", 0) or 0),
            reverse=True,
        )
        top_properties = [
            {
                "name": p.get("name", ""),
                "city": p.get("city", ""),
                "noi": p.get("noi", 0),
                "value": p.get("value", 0),
                "cap": p.get("cap", 0),
            }
            for p in ordered[:5]
        ]

    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "overview": overview_data,
        "pipeline": {
            "pipeline_total": pipeline_data.get("pipeline_total", 0),
            "commission_pipeline": pipeline_data.get("commission_pipeline", 0),
            "by_stage": pipeline_data.get("by_stage", {}),
        },
        "activities": {
            "upcoming_count": activities_data.get("upcoming_count", 0),
            "completed_count": activities_data.get("completed_count", 0),
            "by_type": activities_data.get("by_type", {}),
        },
        "top_properties_by_noi": top_properties,
    }


def _augment_files_with_urls(result: dict[str, Any], service: str) -> dict[str, Any]:
    """Inject download URLs into files/items arrays so the frontend can download them."""
    for key in ("files", "items"):
        entries = result.get(key)
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if isinstance(entry, dict) and "name" in entry and "url" not in entry:
                entry["url"] = f"/download/{service}/{urllib.parse.quote(entry['name'], safe='')}"
            elif isinstance(entry, str) and key == "items":
                result[key] = [
                    {"name": e, "url": f"/download/{service}/{urllib.parse.quote(e, safe='')}"}
                    for e in entries
                ]
                break
    return result


@app.post("/chat")
async def chat(payload: ChatRequest, request: Request) -> StreamingResponse:
    """Streaming chat endpoint — returns SSE text/event-stream."""
    rate_key = payload.user_id or (request.client.host if request.client else "unknown")
    if not _limiter.is_allowed(rate_key):
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit reached. {_limiter.remaining(rate_key)} requests remaining.",
        )

    payload.message = validate_and_sanitize(payload.message, payload.user_id)
    return StreamingResponse(
        _stream_chat_response(payload, rate_key),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/chat/batch")
async def chat_batch(payload: ChatRequest, request: Request) -> ChatResponse:
    """Batch chat endpoint — returns full JSON response after LLM completes."""
    rate_key = payload.user_id or (request.client.host if request.client else "unknown")
    if not _limiter.is_allowed(rate_key):
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit reached. {_limiter.remaining(rate_key)} requests remaining.",
        )
    payload.message = validate_and_sanitize(payload.message, payload.user_id)
    return await _collect_batch(_stream_chat_response(payload, rate_key))


# ─── File Download Proxy ──────────────────────────────────────────────

@app.get("/download/{service}/{file_name:path}")
async def download_file(service: str, file_name: str) -> Response:
    if service not in MCP_ENDPOINTS:
        raise HTTPException(status_code=404, detail=f"Unknown service: {service}")
    mcp_base = _base(MCP_ENDPOINTS[service])
    download_url = f"{mcp_base}/mcp/files/{urllib.parse.quote(file_name, safe='')}/download"
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        resp = await client.get(download_url)
        if resp.status_code >= 400:
            raise HTTPException(status_code=resp.status_code, detail=resp.text[:500])
        content_type = resp.headers.get("content-type", "application/octet-stream")
        disposition = resp.headers.get("content-disposition", "")
        headers: dict[str, str] = {}
        if disposition:
            headers["Content-Disposition"] = disposition
        return Response(content=resp.content, media_type=content_type, headers=headers)


# ─── Teams SSO / OBO ─────────────────────────────────────────────────

class TeamsTokenRequest(BaseModel):
    token: str


class ConnectorSetEnabledRequest(BaseModel):
    enabled: bool


class ConnectorFetchRequest(BaseModel):
    entity_type: str
    limit: int = 100
    cursor: str | None = None
    idempotency_key: str | None = None


class ConnectorSyncRequest(BaseModel):
    entity_type: str
    limit: int = 100
    use_saved_cursor: bool = True
    idempotency_key: str | None = None


class ConnectorReplayRequest(BaseModel):
    dead_letter_id: int


class ConnectorSyncScheduleRequest(BaseModel):
    source_id: str
    entity_type: str
    limit: int = 100
    interval_seconds: int = 300


class WebhookIngressRequest(BaseModel):
    source_id: str = "webhook"
    event_type: str
    entity_type: str
    source_record_id: str
    occurred_at: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class BitemporalFreshnessQuery(BaseModel):
    source_id: str | None = None
    entity_type: str | None = None
    limit: int = 100


class BitemporalLineageQuery(BaseModel):
    source_id: str
    entity_type: str
    source_record_id: str
    limit: int = 50


class BitemporalConfidenceQuery(BaseModel):
    source_id: str | None = None
    entity_type: str | None = None


class BitemporalAsOfQuery(BaseModel):
    as_of: str
    source_id: str | None = None
    entity_type: str | None = None
    limit: int = 100


class BitemporalDiffQuery(BaseModel):
    t1: str
    t2: str
    source_id: str | None = None
    entity_type: str | None = None
    limit: int = 100


class ActionWriteRequest(BaseModel):
    source_id: str
    entity_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str
    requested_by: str | None = None


class ActionDecisionRequest(BaseModel):
    action_id: str
    decided_by: str
    reason: str | None = None


class ActionExecuteRequest(BaseModel):
    action_id: str


class ConnectorCircuitRequest(BaseModel):
    source_id: str
    state: Literal["open", "closed"]
    reason: str | None = None


@app.post("/auth/teams-token")
def exchange_teams_token(payload: TeamsTokenRequest) -> dict[str, Any]:
    if not TEAMS_SSO_ENABLED:
        return {"error": "Teams SSO is not enabled. Set ENABLE_TEAMS_SSO=true.", "enabled": False}
    exchange = get_obo_exchange()
    if exchange is None or not exchange.configured:
        return {"error": "OBO exchange not configured.", "configured": False}
    graph_token = exchange.acquire_graph_token(payload.token)
    if graph_token is None:
        return {"error": "OBO token exchange failed.", "exchanged": False}
    return {"exchanged": True, "token_type": "Bearer", "scope": "Mail.Read Files.Read User.Read"}


# ─── Connector Admin Endpoints ────────────────────────────────────────


@app.get("/connectors")
def list_connectors(capability: str | None = None, include_disabled: bool = True) -> dict[str, Any]:
    cap_filter: Capability | None = None
    if capability:
        normalized = capability.strip().lower()
        try:
            cap_filter = Capability(normalized)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid capability '{capability}'.") from exc

    rows: list[dict[str, Any]] = []
    for reg in CONNECTOR_REGISTRY.list_all():
        connector = reg.connector
        if cap_filter is not None and cap_filter not in connector.capabilities:
            continue
        if not include_disabled and not reg.enabled:
            continue

        rows.append(
            {
                "source_id": connector.source_id,
                "display_name": connector.display_name,
                "enabled": reg.enabled,
                "tenant_id": reg.tenant_id,
                "capabilities": sorted([cap.value for cap in connector.capabilities]),
                "rate_limit": {
                    "requests_per_minute": connector.rate_limit.requests_per_minute,
                    "burst": connector.rate_limit.burst,
                },
                "entities": connector.discover_entities(),
            }
        )

    return {"count": len(rows), "connectors": rows}


@app.post("/webhooks/ingress")
def webhook_ingress(payload: WebhookIngressRequest, request: Request) -> dict[str, Any]:
    secret = os.getenv(WEBHOOK_SOURCE_SECRET_ENV, "")
    provided_sig = request.headers.get("x-webhook-signature", "")

    envelope = WebhookEnvelope(
        headers={k.lower(): v for k, v in request.headers.items()},
        payload=payload.payload,
        received_at=datetime.utcnow(),
    )

    signature_valid = True
    if secret:
        signature_valid = WEBHOOK_ADAPTER.verify_signature(envelope=envelope, secret=secret)
        if not signature_valid:
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
    elif provided_sig:
        raise HTTPException(status_code=500, detail=f"Webhook secret env '{WEBHOOK_SOURCE_SECRET_ENV}' not configured")

    occurred_at = payload.occurred_at or envelope.received_at.isoformat(timespec="microseconds") + "Z"
    ingest = EVENT_SIGNAL_STORE.ingest_event(
        source_id=payload.source_id,
        event_type=payload.event_type,
        entity_type=payload.entity_type,
        source_record_id=payload.source_record_id,
        payload=payload.payload,
        occurred_at=occurred_at,
        signature_valid=signature_valid,
    )

    return {
        "accepted": True,
        "source_id": payload.source_id,
        "event_type": payload.event_type,
        "entity_type": payload.entity_type,
        "source_record_id": payload.source_record_id,
        "event_id": ingest["event_id"],
        "signal_count": ingest["signal_count"],
        "signal_ids": ingest["signal_ids"],
        "received_at": ingest["received_at"],
    }


@app.get("/signals")
def list_signals(source_id: str | None = None, limit: int = 100) -> dict[str, Any]:
    rows = EVENT_SIGNAL_STORE.list_signals(source_id=source_id, limit=limit)
    return {"count": len(rows), "signals": rows}


@app.get("/events")
def list_events(source_id: str | None = None, limit: int = 100) -> dict[str, Any]:
    rows = EVENT_SIGNAL_STORE.list_events(source_id=source_id, limit=limit)
    return {"count": len(rows), "events": rows}


@app.post("/tools/get_connector_freshness")
def tool_get_connector_freshness(payload: BitemporalFreshnessQuery) -> dict[str, Any]:
    return BITEMPORAL_STORE.get_connector_freshness(
        source_id=payload.source_id,
        entity_type=payload.entity_type,
        limit=payload.limit,
    )


@app.post("/tools/get_entity_lineage")
def tool_get_entity_lineage(payload: BitemporalLineageQuery) -> dict[str, Any]:
    return BITEMPORAL_STORE.get_entity_lineage(
        source_id=payload.source_id,
        entity_type=payload.entity_type,
        source_record_id=payload.source_record_id,
        limit=payload.limit,
    )


@app.post("/tools/get_confidence_breakdown")
def tool_get_confidence_breakdown(payload: BitemporalConfidenceQuery) -> dict[str, Any]:
    return BITEMPORAL_STORE.get_confidence_breakdown(
        source_id=payload.source_id,
        entity_type=payload.entity_type,
    )


@app.post("/tools/query_as_of")
def tool_query_as_of(payload: BitemporalAsOfQuery) -> dict[str, Any]:
    return BITEMPORAL_STORE.query_as_of(
        as_of=payload.as_of,
        source_id=payload.source_id,
        entity_type=payload.entity_type,
        limit=payload.limit,
    )


@app.post("/tools/diff_between")
def tool_diff_between(payload: BitemporalDiffQuery) -> dict[str, Any]:
    return BITEMPORAL_STORE.diff_between(
        t1=payload.t1,
        t2=payload.t2,
        source_id=payload.source_id,
        entity_type=payload.entity_type,
        limit=payload.limit,
    )


@app.post("/actions/write")
def request_write_action(payload: ActionWriteRequest) -> dict[str, Any]:
    return ACTION_SERVICE.request_action(
        source_id=payload.source_id,
        entity_type=payload.entity_type,
        payload=payload.payload,
        idempotency_key=payload.idempotency_key,
        requested_by=payload.requested_by,
    )


@app.post("/actions/approve")
def approve_write_action(payload: ActionDecisionRequest) -> dict[str, Any]:
    return ACTION_SERVICE.approve_action(action_id=payload.action_id, approved_by=payload.decided_by)


@app.post("/actions/reject")
def reject_write_action(payload: ActionDecisionRequest) -> dict[str, Any]:
    return ACTION_SERVICE.reject_action(
        action_id=payload.action_id,
        rejected_by=payload.decided_by,
        reason=payload.reason,
    )


@app.post("/actions/execute")
def execute_write_action(payload: ActionExecuteRequest) -> dict[str, Any]:
    return ACTION_SERVICE.execute_action(action_id=payload.action_id)


@app.get("/actions")
def list_write_actions(status: str | None = None, source_id: str | None = None, limit: int = 100) -> dict[str, Any]:
    rows = ACTION_STORE.list_actions(status=status, source_id=source_id, limit=limit)
    return {"count": len(rows), "actions": rows}


@app.get("/actions/approvals")
def list_pending_approvals(status: str = "pending", limit: int = 100) -> dict[str, Any]:
    rows = ACTION_STORE.list_approval_queue(status=status, limit=limit)
    return {"count": len(rows), "approvals": rows}


@app.post("/actions/circuit")
def set_connector_circuit(payload: ConnectorCircuitRequest) -> dict[str, Any]:
    if not CONNECTOR_REGISTRY.has(payload.source_id):
        raise HTTPException(status_code=404, detail=f"Unknown connector '{payload.source_id}'.")
    state = ACTION_STORE.set_circuit_state(source_id=payload.source_id, state=payload.state, reason=payload.reason)
    return state


@app.get("/actions/circuit")
def get_connector_circuit(source_id: str) -> dict[str, Any]:
    if not CONNECTOR_REGISTRY.has(source_id):
        raise HTTPException(status_code=404, detail=f"Unknown connector '{source_id}'.")
    return ACTION_STORE.get_circuit_state(source_id)


@app.get("/actions/audit")
def list_action_audit(limit: int = 100, action_id: str | None = None) -> dict[str, Any]:
    rows = ACTION_STORE.list_audit_events(limit=limit, action_id=action_id)
    return {"count": len(rows), "events": rows}


@app.post("/connectors/{source_id}/enable")
def set_connector_enabled(source_id: str, payload: ConnectorSetEnabledRequest) -> dict[str, Any]:
    if not CONNECTOR_REGISTRY.has(source_id):
        raise HTTPException(status_code=404, detail=f"Unknown connector '{source_id}'.")

    CONNECTOR_REGISTRY.set_enabled(source_id, payload.enabled)
    return {"source_id": source_id, "enabled": CONNECTOR_REGISTRY.is_enabled(source_id)}


@app.post("/connectors/{source_id}/fetch")
def fetch_connector_records(source_id: str, payload: ConnectorFetchRequest) -> dict[str, Any]:
    try:
        return _run_connector_fetch(
            source_id=source_id,
            entity_type=payload.entity_type,
            limit=payload.limit,
            cursor_value=payload.cursor,
            idempotency_key=payload.idempotency_key,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Connector fetch failed: {exc}") from exc


@app.post("/connectors/{source_id}/sync")
def run_connector_sync(source_id: str, payload: ConnectorSyncRequest) -> dict[str, Any]:
    try:
        return _run_sync_once(
            source_id=source_id,
            entity_type=payload.entity_type,
            limit=payload.limit,
            use_saved_cursor=payload.use_saved_cursor,
            idempotency_key=payload.idempotency_key,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Connector sync failed: {exc}") from exc


@app.post("/connectors/sync/schedule")
def schedule_connector_sync(payload: ConnectorSyncScheduleRequest) -> dict[str, Any]:
    if not CONNECTOR_REGISTRY.has(payload.source_id):
        raise HTTPException(status_code=404, detail=f"Unknown connector '{payload.source_id}'.")

    row = CONNECTOR_SYNC_STORE.upsert_schedule(
        source_id=payload.source_id,
        entity_type=payload.entity_type,
        limit_value=payload.limit,
        interval_seconds=payload.interval_seconds,
        enabled=True,
    )
    return _normalize_schedule(payload.source_id, payload.entity_type, row)


@app.get("/connectors/sync/schedules")
def list_connector_sync_schedules(enabled_only: bool = False) -> dict[str, Any]:
    rows = CONNECTOR_SYNC_STORE.list_schedules(enabled_only=enabled_only)
    return {
        "count": len(rows),
        "schedules": [_normalize_schedule(r["source_id"], r["entity_type"], r) for r in rows],
    }


@app.post("/connectors/sync/stop")
def stop_connector_sync(source_id: str, entity_type: str) -> dict[str, Any]:
    changed = CONNECTOR_SYNC_STORE.set_schedule_enabled(source_id, entity_type, enabled=False)
    if not changed:
        return {"stopped": False, "reason": "not_found", "source_id": source_id, "entity_type": entity_type}

    row = CONNECTOR_SYNC_STORE.get_schedule(source_id, entity_type)
    return {
        "stopped": True,
        **_normalize_schedule(source_id, entity_type, row),
    }


@app.delete("/connectors/sync/schedule")
def delete_connector_sync_schedule(source_id: str, entity_type: str) -> dict[str, Any]:
    removed = CONNECTOR_SYNC_STORE.delete_schedule(source_id, entity_type)
    return {
        "deleted": bool(removed),
        "source_id": source_id,
        "entity_type": entity_type,
    }


@app.post("/connectors/sync/schedule/enable")
def enable_connector_sync_schedule(source_id: str, entity_type: str) -> dict[str, Any]:
    changed = CONNECTOR_SYNC_STORE.set_schedule_enabled(source_id, entity_type, enabled=True)
    if not changed:
        raise HTTPException(status_code=404, detail=f"Schedule not found for {source_id}/{entity_type}")
    row = CONNECTOR_SYNC_STORE.get_schedule(source_id, entity_type)
    return _normalize_schedule(source_id, entity_type, row)


@app.get("/connectors/sync/worker")
def connector_sync_worker_status() -> dict[str, Any]:
    return {
        "worker_id": SCHEDULER_WORKER_ID,
        "poll_seconds": SCHEDULER_POLL_SECONDS,
        "lease_seconds": SCHEDULER_LEASE_SECONDS,
        "running": bool(SCHEDULER_TASK and not SCHEDULER_TASK.done()),
    }


@app.get("/connectors/sync/runs")
def list_sync_dead_letters(status: str = "pending", limit: int = 50) -> dict[str, Any]:
    rows = CONNECTOR_SYNC_STORE.list_dead_letters(status=status, limit=limit)
    return {"count": len(rows), "dead_letters": rows}


@app.get("/connectors/sync/runs/recent")
def list_recent_sync_runs(limit: int = 100) -> dict[str, Any]:
    rows = CONNECTOR_SYNC_STORE.list_recent_runs(limit=limit)
    return {"count": len(rows), "runs": rows}


@app.get("/connectors/sync/reliability")
def connector_sync_reliability() -> dict[str, Any]:
    thresholds = {
        "max_schedule_due_lag_seconds": float(os.getenv("SLO_MAX_SCHEDULE_DUE_LAG_SECONDS", "1800")),
        "max_freshness_lag_seconds": float(os.getenv("SLO_MAX_FRESHNESS_LAG_SECONDS", "3600")),
        "min_run_success_rate": float(os.getenv("SLO_MIN_RUN_SUCCESS_RATE", "0.95")),
        "max_pending_dead_letters": int(os.getenv("SLO_MAX_PENDING_DEAD_LETTERS", "20")),
    }
    current = CONNECTOR_SYNC_STORE.get_reliability_metrics()

    checks = {
        "schedule_due_lag_ok": current["max_schedule_due_lag_seconds"] <= thresholds["max_schedule_due_lag_seconds"],
        "freshness_lag_ok": current["max_freshness_lag_seconds"] <= thresholds["max_freshness_lag_seconds"],
        "run_success_rate_ok": current["run_success_rate_last_200"] >= thresholds["min_run_success_rate"],
        "dead_letters_ok": current["pending_dead_letters"] <= thresholds["max_pending_dead_letters"],
    }
    gate_pass = all(checks.values())

    return {
        "pass": gate_pass,
        "checks": checks,
        "thresholds": thresholds,
        "current": current,
    }


@app.get("/actions/reliability")
def actions_reliability() -> dict[str, Any]:
    thresholds = {
        "min_action_success_rate": float(os.getenv("SLO_MIN_ACTION_SUCCESS_RATE", "0.95")),
        "max_write_failures": int(os.getenv("SLO_MAX_WRITE_FAILURES", "5")),
    }
    current = compute_action_metrics(ACTION_STORE)
    checks = {
        "action_success_rate_ok": current["action_success_rate"] >= thresholds["min_action_success_rate"],
        "write_failures_ok": current["write_failures"] <= thresholds["max_write_failures"],
    }
    return {
        "pass": all(checks.values()),
        "checks": checks,
        "thresholds": thresholds,
        "current": current,
    }


@app.post("/connectors/sync/replay")
def replay_dead_letter(payload: ConnectorReplayRequest) -> dict[str, Any]:
    row = CONNECTOR_SYNC_STORE.get_dead_letter(payload.dead_letter_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Dead-letter id {payload.dead_letter_id} not found")

    replay_payload = row.get("payload") or {}
    limit = int(replay_payload.get("limit", 100))
    idempotency_key = replay_payload.get("idempotency_key")

    try:
        result = _run_sync_once(
            source_id=str(row["source_id"]),
            entity_type=str(row["entity_type"]),
            limit=limit,
            use_saved_cursor=False,
            idempotency_key=idempotency_key,
        )
        CONNECTOR_SYNC_STORE.mark_dead_letter_replayed(payload.dead_letter_id, success=True)
        return {"replayed": True, "dead_letter_id": payload.dead_letter_id, "result": result}
    except Exception as exc:  # noqa: BLE001
        CONNECTOR_SYNC_STORE.mark_dead_letter_replayed(
            payload.dead_letter_id,
            success=False,
            error_text=str(exc),
        )
        raise HTTPException(status_code=502, detail=f"Replay failed: {exc}") from exc


# ─── Admin Endpoints ──────────────────────────────────────────────────

def _active_tools() -> list[dict[str, Any]]:
    """Return only tools whose MCP server is currently enabled."""
    active: list[dict[str, Any]] = []
    for tool in TOOLS:
        route = _TOOL_NAME_TO_KEY.get(tool["function"]["name"])
        if not route or route not in MCP_ENDPOINTS:
            continue
        if MCP_ENABLED.get(route, True):
            active.append(tool)
    return active


@app.get("/admin/mcp-config")
def admin_mcp_config() -> dict[str, Any]:
    """Return current MCP server configuration and enabled status."""
    return {
        "servers": [
            {
                "key": key,
                "name": key.replace("_", " ").title(),
                "enabled": MCP_ENABLED.get(key, True),
                "url": url,
                "has_admin_data": key in ("knowledge_base", "memory", "files", "document_generation", "analytics"),
            }
            for key, url in MCP_ENDPOINTS.items()
        ]
    }


class McpToggleRequest(BaseModel):
    key: str
    enabled: bool


@app.post("/admin/mcp-config")
def admin_toggle_mcp(payload: McpToggleRequest) -> dict[str, Any]:
    """Enable or disable an MCP server."""
    if payload.key not in MCP_ENDPOINTS:
        return {"error": f"Unknown MCP server: {payload.key}"}
    MCP_ENABLED[payload.key] = payload.enabled
    return {"key": payload.key, "enabled": payload.enabled}


@app.get("/admin/mcp-data/{service}")
async def admin_get_mcp_data(service: str) -> dict[str, Any]:
    """Fetch a sample of data from an MCP server's /admin/data endpoint."""
    if service not in MCP_ENDPOINTS:
        return {"error": f"Unknown service: {service}"}
    base = _base(MCP_ENDPOINTS[service])
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        try:
            resp = await client.get(f"{base}/admin/data")
            if resp.status_code == 200:
                return resp.json()
            return {"error": f"MCP returned {resp.status_code}", "body": resp.text[:200]}
        except Exception as exc:
            return {"error": str(exc)}


@app.post("/admin/mcp-data/{service}")
async def admin_post_mcp_data(service: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Add data to an MCP server's /admin/data endpoint."""
    if service not in MCP_ENDPOINTS:
        return {"error": f"Unknown service: {service}"}
    base = _base(MCP_ENDPOINTS[service])
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        try:
            resp = await client.post(f"{base}/admin/data", json=payload)
            if resp.status_code in (200, 201):
                return resp.json()
            return {"error": f"MCP returned {resp.status_code}", "body": resp.text[:200]}
        except Exception as exc:
            return {"error": str(exc)}


app.include_router(auth_router)
