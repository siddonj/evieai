# MCP Server Tools & Usage Improvement Plan

> Comprehensive strategy to improve MCP server discoverability, performance, reliability, documentation, and capabilities.
> **Status**: Planning phase | **Priority**: High

---

## 📊 Current State Assessment

### MCP Server Inventory
| Server | Port | Purpose | Status |
|--------|------|---------|--------|
| file_share | 8001 | File search & retrieval | 🟡 Needs improvement |
| o365_mail | 8002 | Outlook emails | 🟢 Basic working |
| onedrive | 8003 | OneDrive/SharePoint files | 🟢 Basic working |
| memory | 8004 | User context, profiles | 🟡 Limited features |
| knowledge_base | 8005 | Policies, SOPs | 🟢 Basic working |
| document_generation | 8006 | Reports, documents | 🟡 Needs improvement |
| analytics | 8007 | KPIs, metrics, trends | 🟡 Needs improvement |
| sql | 8008 | Multifamily properties, CRM | 🟡 Needs improvement |
| dashboard | 8009 | Metrics aggregation | 🟢 Basic working |
| postgresql | TBD | Operational tables | 🔴 Unclear usage |
| DAB (SQL Data API) | 5000 | Auto-generated REST API | 🟢 Deployed |

### Key Issues Identified
- ❌ Tool descriptions too generic → LLM picks wrong tool
- ❌ No error context in responses → Hard to debug failures
- ❌ No caching → Repeated queries are slow
- ❌ Missing API documentation → Users don't know what tools can do
- ❌ Inconsistent response formats → Integration complexity
- ❌ No health checks → Can't tell if MCP is ready
- ❌ Limited test coverage → Regressions go unnoticed

---

## 🎯 Improvement Priority Matrix

```
HIGH IMPACT + LOW EFFORT:
├─ Tool descriptions with data catalogs
├─ Standardized response format
├─ Health check endpoints
└─ Error context in responses

HIGH IMPACT + MEDIUM EFFORT:
├─ Query caching layer
├─ API documentation
├─ Test suite for each server
└─ Structured logging

MEDIUM IMPACT + LOW EFFORT:
├─ Usage examples in docstrings
├─ Deprecation warnings
└─ Rate limit headers

HIGH IMPACT + HIGH EFFORT:
├─ New query types (aggregations, filters)
├─ User preference personalization
└─ Real-time streaming responses
```

---

## 🔧 Improvement Categories

### 1. Tool Descriptions & Routing (QUICK WIN ✅)

**Current Issue**: LLM defaults to wrong tool. Descriptions are too generic.

**Improvements**:
- [ ] **file_share**: Add explicit "Contains: Employee-Roster.csv, Q1-Financial-Report.txt, Product-Roadmap-2026.txt, Meeting-Notes, Technical-Specs"
- [ ] **sql**: Add explicit "ONLY for real estate/brokerage: properties, contacts, deals, pipeline. NOT for employees/policies"
- [ ] **document_generation**: List all available templates (executive summary, board briefing, sales report)
- [ ] **analytics**: List all available metrics (occupancy, cap rate, NOI, commission, pipeline)
- [ ] Add "Use this tool when..." guidance to each description
- [ ] Add "Do NOT use for..." constraints

**Effort**: 1–2 hours | **Impact**: 🟢 High (prevents tool selection errors)

**Files to Update**:
- `orchestrator/app/main.py` → TOOLS array descriptions ✅ (Already done in last session)

---

### 2. Performance & Efficiency

#### 2.1 Query Caching
**Current Issue**: Same query executed repeatedly = slow response

**Solution**: Add Redis/in-memory cache with TTL
```python
# Pseudo-code
@cache(ttl=300)  # 5 minutes
async def query_files(query: str):
    # Return cached result if query already cached
    pass
```

**Benefits**:
- Repeated queries return in <10ms instead of 1–2s
- Reduced load on Graph API, SQL database
- Better user experience for common queries

**Implementation**:
- [ ] Add caching decorator to high-traffic endpoints
- [ ] Start with file_share, analytics (high read, low write)
- [ ] Make cache optional (disable for real-time data)

**Effort**: 4–6 hours | **Impact**: 🟢 High (50%+ faster for repeated queries)

**Affected Servers**: file_share, analytics, knowledge_base, sql

#### 2.2 Connection Pooling
**Current Issue**: Creating new connection per request = slow startup

**Solution**: Reuse database connections, Graph API sessions

**Implementation**:
- [ ] sql: Connection pool for multifamily database
- [ ] o365_mail, onedrive: Session pooling for Graph API calls
- [ ] Add connection pool metrics (active, idle, waiting)

**Effort**: 3–4 hours | **Impact**: 🟡 Medium (improves on cold start)

---

### 3. Error Handling & Reliability

#### 3.1 Structured Error Responses
**Current Issue**: Errors don't provide enough context. User sees "Something went wrong"

**Standard Error Format**:
```json
{
  "error": {
    "code": "FILE_NOT_FOUND",
    "message": "Employee-Roster.csv not found in file share",
    "details": {
      "query": "employees",
      "searched_in": ["HR", "General"],
      "available_files": ["Q1-Financial-Report.txt", "Product-Roadmap-2026.txt"]
    },
    "timestamp": "2026-05-29T14:23:45Z",
    "trace_id": "abc-123-def"
  }
}
```

**Benefits**:
- User knows what went wrong
- Orchestrator can suggest alternatives
- Easier to debug in logs

**Implementation**:
- [ ] Define error codes per server (FILE_NOT_FOUND, PERMISSION_DENIED, TIMEOUT, etc.)
- [ ] Add structured logging with trace_id
- [ ] Include available alternatives in error response
- [ ] Add retry guidance (when to retry vs. when to fail)

**Effort**: 3–4 hours | **Impact**: 🟢 High (improves debuggability)

**Files to Create/Update**:
- `mcp_servers/common/errors.py` → Centralized error definitions
- All MCP servers → Use standard error format

#### 3.2 Health Checks
**Current Issue**: Can't tell if MCP server is healthy. Container Apps probe timeout detection is slow.

**Solution**: Add `/health` endpoint to every MCP server

```python
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": "2026-05-29T14:23:45Z",
        "checks": {
            "database": "✅ Connected (1.2ms)",
            "graph_api": "✅ Authenticated (450ms)",
            "cache": "✅ Redis up (2.1ms)"
        }
    }
```

**Benefits**:
- Container Apps can detect unhealthy instances faster
- Can diagnose problems before user sees them
- Easy to monitor in dashboards

**Implementation**:
- [ ] Add health check to every MCP server
- [ ] Check dependencies (databases, APIs, cache)
- [ ] Include timing info (latency per check)
- [ ] Graceful degradation (warn if dependency slow, fail if timeout)

**Effort**: 2–3 hours | **Impact**: 🟢 High (reduces MTTR)

#### 3.3 Input Validation & Sanitization
**Current Issue**: No validation of user queries. Could cause SQL injection, API errors.

**Solution**: Add schema validation before processing

```python
from pydantic import BaseModel

class FileQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    limit: int = Field(default=10, ge=1, le=100)
    filters: Optional[Dict[str, str]] = None
```

**Benefits**:
- Prevents malformed requests
- Clear error messages to user
- Reduces downstream errors

**Effort**: 2–3 hours | **Impact**: 🟡 Medium (improves robustness)

---

### 4. Documentation & Examples

#### 4.1 API Reference Documentation
**Current Issue**: Users don't know what each MCP server can do.

**Solution**: Auto-generate API docs + usage examples

**Create**:
- [ ] `docs/MCP_API_REFERENCE.md` → Full API for all 11 servers
- [ ] Example queries per server (curl, Python, JavaScript)
- [ ] Response examples (success + error cases)
- [ ] Rate limits, timeout values, constraints

**Structure**:
```markdown
## file_share

### Query Files
**Endpoint**: POST /query_files

**Parameters**:
- query (string, required): Search query, e.g. "employees", "financial report"

**Returns**:
```json
{
  "results": [
    {
      "name": "Employee-Roster.csv",
      "description": "13-person employee roster with salary data",
      "size": "2.3 KB",
      "content": "..."
    }
  ]
}
```

**Examples**:
```bash
curl -X POST http://localhost:8001/query_files \
  -H "Content-Type: application/json" \
  -d '{"query": "employees"}'
```
```

**Effort**: 4–6 hours | **Impact**: 🟢 High (enables self-service)

#### 4.2 Docstring Examples in Code
**Current Issue**: Code has no examples of how to use each tool.

**Solution**: Add docstring examples to every tool

```python
async def query_files(query: str) -> dict:
    """
    Search files in Azure File Share.
    
    Contains: Employee-Roster.csv, Q1-Financial-Report.txt, Product-Roadmap-2026.txt,
              Meeting-Notes-Executive.txt, Technical-Spec-Service-Restart.txt
    
    Args:
        query: Natural language search, e.g. "employees", "financial report"
    
    Returns:
        {"results": [{"name": "...", "content": "..."}]}
    
    Examples:
        # Search for employee data
        result = await query_files("employees")
        assert result["results"][0]["name"] == "Employee-Roster.csv"
        
        # Search for financial data
        result = await query_files("financial")
        assert any("Financial" in r["name"] for r in result["results"])
    """
```

**Effort**: 2–3 hours | **Impact**: 🟡 Medium (helps developers)

---

### 5. Standardized Response Formats

**Current Issue**: Different servers return different formats. Hard to integrate.

**Solution**: Define standard response envelope for all MCP servers

```python
# Standard success response
{
  "status": "success",
  "data": {
    # Tool-specific data here
  },
  "metadata": {
    "request_id": "abc-123",
    "timestamp": "2026-05-29T14:23:45Z",
    "latency_ms": 145,
    "cache_hit": false
  }
}

# Standard error response
{
  "status": "error",
  "error": {
    "code": "FILE_NOT_FOUND",
    "message": "Employee-Roster.csv not found"
  },
  "metadata": {
    "request_id": "abc-123",
    "timestamp": "2026-05-29T14:23:45Z"
  }
}
```

**Benefits**:
- Orchestrator has predictable response shape
- Easier error handling
- Better logging & monitoring

**Effort**: 3–4 hours | **Impact**: 🟡 Medium (improves consistency)

**Files to Create/Update**:
- `mcp_servers/common/response.py` → Reusable ResponseEnvelope class
- All MCP servers → Use ResponseEnvelope

---

### 6. Test Coverage

**Current Issue**: No tests for MCP servers. Regressions go unnoticed.

**Solution**: Create test suite per server

**Test Types**:
- ✅ **Unit tests**: Mock Graph API, databases. Test query parsing, error handling
- ✅ **Integration tests**: Real database/API calls. Test end-to-end workflows
- ✅ **Load tests**: Simulate 100+ concurrent requests. Measure latency, throughput

**Test Structure**:
```
tests/
├── mcp_servers/
│   ├── file_share/
│   │   ├── test_query_files.py (unit + integration)
│   │   └── test_health.py
│   ├── sql/
│   │   ├── test_query_sql.py (unit + integration)
│   │   └── test_error_handling.py
│   └── ...
```

**Coverage Targets**:
- [ ] file_share: 80% code coverage + 10 integration tests
- [ ] sql: 85% code coverage + 15 integration tests
- [ ] analytics: 75% code coverage + 8 integration tests
- [ ] document_generation: 70% code coverage + 6 integration tests

**Effort**: 8–10 hours | **Impact**: 🟢 High (catches regressions early)

---

### 7. Monitoring & Observability

**Current Issue**: Can't see what's happening inside MCP servers. No metrics.

**Solution**: Add structured logging + metrics collection

**What to Track**:
- ✅ Request count per tool (success, errors, timeouts)
- ✅ Latency histogram (p50, p95, p99)
- ✅ Cache hit rate
- ✅ Dependency health (Graph API, databases, cache)
- ✅ Query patterns (top queries, slow queries)

**Implementation**:
- [ ] Add logging middleware to FastAPI
- [ ] Instrument database queries (time, row count)
- [ ] Instrument Graph API calls (latency, error rate)
- [ ] Export metrics to Application Insights (already in use)

**Effort**: 4–5 hours | **Impact**: 🟡 Medium (helps with optimization)

---

### 8. New Features & Capabilities (Priority Servers)

#### file_share Improvements
- [ ] **Smart filtering**: Already implemented (match "employees" to Employee-Roster.csv)
- [ ] **Full-text search**: Search inside CSV/text files, not just filenames
- [ ] **Metadata preview**: Return file size, creation date, author
- [ ] **Version history**: Show previous versions of files
- [ ] **Bulk operations**: Download multiple files at once

**Implementation Details**:
```python
# Current: Match query to filename
if "employees" in query.lower():
    return filter_files(category="HR")

# Enhanced: Full-text search inside files
async def search_file_content(query: str):
    for file in files:
        if await contains_text(file, query):
            yield {
                "name": file,
                "preview": extract_matching_lines(file, query),
                "matches": count_matches(file, query)
            }
```

**Effort**: 6–8 hours | **Impact**: 🟢 High (much more powerful)

#### sql Improvements
- [ ] **Advanced filtering**: Filter by date range, status, agent
- [ ] **Aggregations**: SUM, AVG, COUNT grouped by property type, market, agent
- [ ] **Sorting**: Sort by occupancy, cap rate, commission
- [ ] **Relationship queries**: "Show properties managed by [agent]"
- [ ] **Alerts**: Flag unusual values (occupancy <50%, cap rate >10%)

**Example Enhanced Query**:
```
Current: "Show multifamily properties"
→ "Show multifamily properties in Memphis with >80% occupancy, sorted by cap rate"
```

**Effort**: 8–10 hours | **Impact**: 🟢 High (enables complex analysis)

#### document_generation Improvements
- [ ] **Template library**: Executive summary, board briefing, sales report, market analysis
- [ ] **Data binding**: Pull live data from sql/analytics into template
- [ ] **Custom branding**: Logo, colors, fonts
- [ ] **Export formats**: HTML, PDF, DOCX
- [ ] **Scheduling**: Generate weekly/monthly reports automatically

**Example**:
```python
await generate_document(
    template="executive_summary",
    data_source="analytics",  # Pull live KPIs
    date_range="Q2_2026",
    export_format="pdf"
)
```

**Effort**: 10–12 hours | **Impact**: 🟢 High (powerful new capability)

#### analytics Improvements
- [ ] **Custom KPIs**: Define custom formulas (e.g., (NOI / Property Value) * 100)
- [ ] **Trend analysis**: Show month-over-month or year-over-year trends
- [ ] **Anomaly detection**: Flag outliers
- [ ] **Forecasting**: Predict occupancy/cap rate for next quarter
- [ ] **Benchmarking**: Compare portfolio against market averages

**Example**:
```
User: "How is our occupancy trending?"
→ Analytics: "Overall occupancy: 85.2% (↑1.3% from April). 
   Memphis: 86% (↓0.5%), Nashville: 84% (↑2.1%)
   Forecast Q3: ~87% based on current trend"
```

**Effort**: 8–10 hours | **Impact**: 🟢 High (adds intelligence)

---

## 🚀 Implementation Roadmap

### Phase 1: Quick Wins (Week 1–2) — START HERE
- [ ] Tool descriptions with data catalogs ✅ (Done in last session)
- [ ] Health check endpoints (all servers)
- [ ] Structured error responses (file_share, sql, analytics)
- [ ] Input validation (all servers)

**Effort**: 8–10 hours | **ROI**: High (fixes immediate issues)

### Phase 2: Stability & Observability (Week 3–4)
- [ ] Query caching (file_share, analytics, knowledge_base)
- [ ] Connection pooling (sql, o365_mail, onedrive)
- [ ] Monitoring & metrics (all servers)
- [ ] Test suite (start with file_share, sql)

**Effort**: 16–20 hours | **ROI**: High (prevents problems)

### Phase 3: Documentation & Experience (Week 5–6)
- [ ] API documentation (mcp_API_REFERENCE.md)
- [ ] Docstring examples (all servers)
- [ ] Standardized response format (all servers)
- [ ] User guide (best practices, common queries)

**Effort**: 10–12 hours | **ROI**: Medium (enables self-service)

### Phase 4: Advanced Features (Week 7–10)
- [ ] file_share: Full-text search, version history
- [ ] sql: Advanced filtering, aggregations, alerts
- [ ] analytics: Custom KPIs, trends, forecasting
- [ ] document_generation: Template library, data binding, scheduling

**Effort**: 30–35 hours | **ROI**: High (major new capabilities)

---

## 📋 Checklist: Quick Wins (Phase 1 — Do This First)

### Health Checks
- [ ] Add `/health` endpoint to file_share
- [ ] Add `/health` endpoint to sql
- [ ] Add `/health` endpoint to analytics
- [ ] Add `/health` endpoint to document_generation
- [ ] Add `/health` endpoint to other servers (copy-paste)
- [ ] Test with `curl http://localhost:8001/health`

### Structured Errors
- [ ] Create `mcp_servers/common/errors.py` with error codes
- [ ] Add ErrorResponse dataclass with code, message, details
- [ ] Update file_share to return structured errors
- [ ] Update sql to return structured errors
- [ ] Update analytics to return structured errors
- [ ] Document error codes in API reference

### Input Validation
- [ ] Create Pydantic models for each endpoint
- [ ] Add validation to file_share.query_files
- [ ] Add validation to sql.query_sql
- [ ] Add validation to analytics.query_analytics
- [ ] Add validation to document_generation endpoints
- [ ] Test with invalid inputs (empty string, special chars, huge limit)

### Testing Health Checks
- [ ] Write unit test for each health endpoint
- [ ] Write integration test that calls health during errors
- [ ] Add health check to CI/CD pipeline

---

## 📊 Success Metrics

After implementing these improvements, measure:

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Tool selection accuracy | >95% | ~85% | 📈 Improving |
| Avg response latency | <200ms | ~500ms | 📉 Target |
| Cache hit rate | >40% | 0% | 📊 New |
| Test coverage | >80% | ~10% | 📈 Improving |
| Error recovery rate | >90% | ~50% | 📊 New |
| Server health check time | <100ms | N/A | 📊 New |

---

## 🎓 References

- AGENTS.md → MCP server architecture & port assignments
- docs/ARCHITECTURE.md → High-level system design
- docker-compose.yml → Service definitions & health checks
- orchestrator/app/main.py → Tool definitions & descriptions

