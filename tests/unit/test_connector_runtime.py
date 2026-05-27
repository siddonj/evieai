from __future__ import annotations

import json

from orchestrator.app.connector_runtime import build_connector_registry, load_connector_config


def test_load_connector_config_env_fallback_disabled(monkeypatch):
    monkeypatch.delenv("CONNECTOR_CONFIG_JSON", raising=False)
    monkeypatch.setenv("CONNECTOR_PROPEXO_ENABLED", "false")

    cfg = load_connector_config()
    assert cfg.connectors == []


def test_load_connector_config_json_list(monkeypatch):
    payload = [
        {
            "type": "propexo",
            "source_id": "propexo",
            "enabled": True,
            "api_key_env": "PROPEXO_API_KEY",
            "base_url": "https://api.propexo.com/v1",
        }
    ]
    monkeypatch.setenv("CONNECTOR_CONFIG_JSON", json.dumps(payload))
    cfg = load_connector_config()

    assert len(cfg.connectors) == 1
    assert cfg.connectors[0].type == "propexo"


def test_build_connector_registry_skips_missing_api_key(monkeypatch):
    monkeypatch.setenv(
        "CONNECTOR_CONFIG_JSON",
        json.dumps(
            {
                "connectors": [
                    {
                        "type": "propexo",
                        "enabled": True,
                        "api_key_env": "PROPEXO_API_KEY",
                        "base_url": "https://api.propexo.com/v1",
                    }
                ]
            }
        ),
    )
    monkeypatch.delenv("PROPEXO_API_KEY", raising=False)

    cfg = load_connector_config()
    registry = build_connector_registry(cfg)

    assert registry.list_enabled() == []


def test_build_connector_registry_registers_with_api_key(monkeypatch):
    monkeypatch.setenv(
        "CONNECTOR_CONFIG_JSON",
        json.dumps(
            {
                "connectors": [
                    {
                        "type": "propexo",
                        "enabled": True,
                        "api_key_env": "PROPEXO_API_KEY",
                        "base_url": "https://api.propexo.com/v1",
                    }
                ]
            }
        ),
    )
    monkeypatch.setenv("PROPEXO_API_KEY", "test-key")

    cfg = load_connector_config()
    registry = build_connector_registry(cfg)

    enabled = registry.list_enabled()
    assert len(enabled) == 1
    assert enabled[0].source_id == "propexo"
