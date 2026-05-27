from __future__ import annotations

import json
import logging
import os
from typing import Any, Literal

from pydantic import BaseModel, Field

from connectors.adapters import PropexoAdapter
from connectors.registry import ConnectorRegistry

logger = logging.getLogger("orchestrator.connectors")


class PropexoConnectorConfig(BaseModel):
    type: Literal["propexo"] = "propexo"
    source_id: str = "propexo"
    enabled: bool = True
    tenant_id: str | None = None
    base_url: str = "https://api.propexo.com/v1"
    api_key_env: str = "PROPEXO_API_KEY"


class ConnectorConfig(BaseModel):
    connectors: list[PropexoConnectorConfig] = Field(default_factory=list)


def load_connector_config() -> ConnectorConfig:
    """Load connector config from CONNECTOR_CONFIG_JSON with env fallback."""
    raw = os.getenv("CONNECTOR_CONFIG_JSON", "").strip()
    if raw:
        try:
            payload = json.loads(raw)
            if isinstance(payload, list):
                payload = {"connectors": payload}
            return ConnectorConfig.model_validate(payload)
        except Exception as exc:  # pragma: no cover - defensive logging path
            logger.warning("Invalid CONNECTOR_CONFIG_JSON; falling back to env defaults: %s", exc)

    # Fallback path for simple env-based setup
    fallback_connectors: list[PropexoConnectorConfig] = []
    propexo_enabled = os.getenv("CONNECTOR_PROPEXO_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
    if propexo_enabled:
        fallback_connectors.append(
            PropexoConnectorConfig(
                enabled=True,
                tenant_id=os.getenv("CONNECTOR_DEFAULT_TENANT_ID"),
                base_url=os.getenv("CONNECTOR_PROPEXO_BASE_URL", "https://api.propexo.com/v1"),
                api_key_env=os.getenv("CONNECTOR_PROPEXO_API_KEY_ENV", "PROPEXO_API_KEY"),
            )
        )

    return ConnectorConfig(connectors=fallback_connectors)


def build_connector_registry(config: ConnectorConfig) -> ConnectorRegistry:
    registry = ConnectorRegistry()

    for spec in config.connectors:
        if spec.type == "propexo":
            api_key = os.getenv(spec.api_key_env, "")
            if spec.enabled and not api_key:
                logger.warning(
                    "Connector '%s' enabled but %s is empty; skipping registration",
                    spec.source_id,
                    spec.api_key_env,
                )
                continue

            connector = PropexoAdapter(api_key=api_key, base_url=spec.base_url)
            registry.register(connector, enabled=spec.enabled, tenant_id=spec.tenant_id)
            logger.info("Registered connector source_id=%s enabled=%s", spec.source_id, spec.enabled)

    return registry


def connector_runtime_summary(registry: ConnectorRegistry, config: ConnectorConfig) -> dict[str, Any]:
    enabled = registry.list_enabled()
    return {
        "configured": len(config.connectors),
        "enabled": len(enabled),
        "sources": [c.source_id for c in enabled],
    }
