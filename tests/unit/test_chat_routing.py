from app.main import _is_work_order_intent, _work_order_query


def test_work_order_intent_matches_maintenance_phrases():
    assert _is_work_order_intent("Show me the open work orders")
    assert _is_work_order_intent("What maintenance requests are still pending?")
    assert _is_work_order_intent("Which service tickets are open?")
    assert _work_order_query() == "open work orders"
