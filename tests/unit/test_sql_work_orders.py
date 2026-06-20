import pytest

from mcp_servers.sql.app.main import QueryRequest, _filter_work_orders, mcp_query


def test_filter_work_orders_returns_only_open_states():
    rows = [
        {"id": 1, "status": "Open"},
        {"id": 2, "status": "Completed"},
        {"id": 3, "status": "In Progress"},
        {"id": 4, "status": "Closed"},
    ]

    filtered = _filter_work_orders(rows, "open work orders")

    assert [row["id"] for row in filtered] == [1, 3]


@pytest.mark.asyncio
async def test_sql_demo_returns_open_work_orders():
    result = await mcp_query(QueryRequest(query="open work orders"))

    assert "work_orders" in result
    assert result["work_orders"]
    assert all(str(row["status"]).lower() in {"open", "pending", "in progress", "active"} for row in result["work_orders"])
