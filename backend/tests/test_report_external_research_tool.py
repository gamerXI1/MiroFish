from app.services import report_tool_registry as registry_module
from app.services.external_research_client import (
    ExternalResearchItem,
    ExternalResearchResult,
)
from app.services.report_tool_registry import build_report_tool_registry


class _TextResult:
    def __init__(self, value: str):
        self.value = value

    def to_text(self) -> str:
        return self.value


class _StubZepTools:
    def __init__(self):
        self.calls = []

    def quick_search(self, **kwargs):
        self.calls.append(("quick_search", kwargs))
        return _TextResult("quick-result")

    def insight_forge(self, **kwargs):
        self.calls.append(("insight_forge", kwargs))
        return _TextResult("insight-result")

    def panorama_search(self, **kwargs):
        self.calls.append(("panorama_search", kwargs))
        return _TextResult("panorama-result")

    def interview_agents(self, **kwargs):
        self.calls.append(("interview_agents", kwargs))
        return _TextResult("interview-result")

    def get_graph_statistics(self, graph_id):
        self.calls.append(("get_graph_statistics", {"graph_id": graph_id}))
        return {"graph_id": graph_id}

    def get_entity_summary(self, **kwargs):
        self.calls.append(("get_entity_summary", kwargs))
        return {"entity_name": kwargs.get("entity_name", "")}

    def get_entities_by_type(self, **kwargs):
        self.calls.append(("get_entities_by_type", kwargs))
        return []


class _StubAgent:
    def __init__(self):
        self.graph_id = "graph-1"
        self.simulation_id = "sim-1"
        self.simulation_requirement = "mock requirement"
        self.zep_tools = _StubZepTools()


def test_registry_exposes_external_research_as_a_canonical_tool():
    registry = build_report_tool_registry(_StubAgent())

    assert "external_research" in registry.valid_names()
    prompt_tools = registry.prompt_tools()
    assert "external_research" in prompt_tools
    assert "query" in prompt_tools["external_research"]["parameters"]
    assert "max_sources" in prompt_tools["external_research"]["parameters"]


def test_external_research_executes_via_adapter_not_zep(monkeypatch):
    captured = {}

    class FakeResearchClient:
        def query(self, **kwargs):
            captured["query_kwargs"] = kwargs
            return ExternalResearchResult(
                success=True,
                query="latest alpha",
                retrieved_at="2026-08-25T00:00:00Z",
                items=[
                    ExternalResearchItem(
                        title="Alpha headline",
                        url="https://example.com/alpha",
                        summary="Alpha summary",
                        excerpt="Alpha excerpt",
                    )
                ],
                provider="hermes-web-search",
                error=None,
            )

    monkeypatch.setattr(registry_module, "ExternalResearchClient", lambda: FakeResearchClient())
    agent = _StubAgent()
    registry = build_report_tool_registry(agent)

    result = registry.execute(
        "external_research",
        {"query": "latest alpha", "max_sources": "3"},
        report_context="section ctx",
    )

    assert captured["query_kwargs"] == {
        "query": "latest alpha",
        "max_sources": 3,
        "trusted_domains": None,
        "browser_fallback": False,
    }
    assert "非模拟事实" in result
    assert "Alpha headline" in result
    assert "https://example.com/alpha" in result
    assert agent.zep_tools.calls == []


def test_external_research_unavailable_stays_explicit_and_does_not_fallback(monkeypatch):
    class FakeResearchClient:
        def query(self, **kwargs):
            return ExternalResearchResult(
                success=False,
                query=kwargs["query"],
                retrieved_at=None,
                items=[],
                provider=None,
                error="research_unavailable",
            )

    monkeypatch.setattr(registry_module, "ExternalResearchClient", lambda: FakeResearchClient())
    agent = _StubAgent()
    registry = build_report_tool_registry(agent)

    result = registry.execute("external_research", {"query": "latest alpha"})

    assert "外部研究不可用" in result
    assert "research_unavailable" in result
    assert agent.zep_tools.calls == []


def test_legacy_graph_search_alias_still_resolves_to_quick_search(monkeypatch):
    class UnexpectedResearchClient:
        def query(self, **kwargs):
            raise AssertionError("external research should not be called")

    monkeypatch.setattr(registry_module, "ExternalResearchClient", lambda: UnexpectedResearchClient())
    agent = _StubAgent()
    registry = build_report_tool_registry(agent)

    result = registry.execute("search_graph", {"query": "alpha"})

    assert result == "quick-result"
    assert agent.zep_tools.calls == [
        ("quick_search", {"graph_id": "graph-1", "query": "alpha", "limit": 10})
    ]
