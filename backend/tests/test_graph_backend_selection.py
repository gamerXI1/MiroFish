from app.config import Config
from app.graph_backend_provider import (
    GraphBackendConfigError,
    GraphBackendProvider,
    get_graph_backend_provider,
)


def test_default_graph_backend_provider_is_zep_cloud(monkeypatch):
    monkeypatch.delenv('GRAPH_BACKEND_PROVIDER', raising=False)

    provider = get_graph_backend_provider()

    assert provider == GraphBackendProvider.ZEP_CLOUD


def test_graphiti_provider_requires_neo4j_env(monkeypatch):
    monkeypatch.setenv('GRAPH_BACKEND_PROVIDER', 'graphiti')
    monkeypatch.delenv('NEO4J_URI', raising=False)
    monkeypatch.delenv('NEO4J_USER', raising=False)
    monkeypatch.delenv('NEO4J_PASSWORD', raising=False)

    try:
        get_graph_backend_provider(validate_env=True)
    except GraphBackendConfigError as exc:
        assert 'NEO4J_URI' in str(exc)
        assert 'NEO4J_USER' in str(exc)
        assert 'NEO4J_PASSWORD' in str(exc)
    else:
        raise AssertionError('expected GraphBackendConfigError')


def test_graphiti_provider_accepts_neo4j_env(monkeypatch):
    monkeypatch.setenv('GRAPH_BACKEND_PROVIDER', 'graphiti')
    monkeypatch.setenv('NEO4J_URI', 'neo4j+s://example.databases.neo4j.io')
    monkeypatch.setenv('NEO4J_USER', 'neo4j')
    monkeypatch.setenv('NEO4J_PASSWORD', 'secret')

    provider = get_graph_backend_provider(validate_env=True)

    assert provider == GraphBackendProvider.GRAPHITI


def test_config_validate_allows_graphiti_without_zep_key(monkeypatch):
    monkeypatch.setenv('GRAPH_BACKEND_PROVIDER', 'graphiti')
    monkeypatch.setenv('NEO4J_URI', 'neo4j+s://example.databases.neo4j.io')
    monkeypatch.setenv('NEO4J_USER', 'neo4j')
    monkeypatch.setenv('NEO4J_PASSWORD', 'secret')
    monkeypatch.delenv('ZEP_API_KEY', raising=False)
    monkeypatch.setenv('LLM_API_KEY', 'dummy')

    errors = Config.validate()

    assert 'ZEP_API_KEY 未配置' not in errors
    assert all('ZEP_API_URL 不受支持' not in err for err in errors)
