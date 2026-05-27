from connectors.adapters.propexo_adapter import PropexoAdapter
from connectors.registry import ConnectorRegistry
from connectors.types import Capability


def _adapter() -> PropexoAdapter:
    return PropexoAdapter(api_key="test", base_url="https://example.test")


def test_enable_disable_and_has():
    registry = ConnectorRegistry()
    adapter = _adapter()
    registry.register(adapter, enabled=True, tenant_id="tenant-a")

    assert registry.has("propexo") is True
    assert registry.is_enabled("propexo") is True

    registry.set_enabled("propexo", False)
    assert registry.is_enabled("propexo") is False
    assert registry.list_enabled() == []


def test_by_capability_filters_enabled_only():
    registry = ConnectorRegistry()
    adapter = _adapter()
    registry.register(adapter, enabled=False)

    assert registry.by_capability(Capability.READ) == []

    registry.set_enabled("propexo", True)
    matches = registry.by_capability(Capability.READ)
    assert len(matches) == 1
    assert matches[0].source_id == "propexo"
