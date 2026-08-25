import json

from app.services.report_tool_registry import (
    ReportToolRegistry,
    ToolSpec,
    build_report_tool_registry,
)


class _TextResult:
    def __init__(self, value: str):
        self.value = value

    def to_text(self) -> str:
        return self.value


class _StubZepTools:
    def __init__(self):
        self.calls = []

    def insight_forge(self, **kwargs):
        self.calls.append(("insight_forge", kwargs))
        return _TextResult(f"insight:{kwargs['query']}:{kwargs['report_context']}")

    def panorama_search(self, **kwargs):
        self.calls.append(("panorama_search", kwargs))
        return _TextResult(
            f"panorama:{kwargs['query']}:{kwargs['include_expired']}"
        )

    def quick_search(self, **kwargs):
        self.calls.append(("quick_search", kwargs))
        return _TextResult(f"quick:{kwargs['query']}:{kwargs['limit']}")

    def interview_agents(self, **kwargs):
        self.calls.append(("interview_agents", kwargs))
        return _TextResult(f"interview:{kwargs['interview_requirement']}:{kwargs['max_agents']}")

    def get_graph_statistics(self, graph_id):
        self.calls.append(("get_graph_statistics", {"graph_id": graph_id}))
        return {"graph_id": graph_id, "total_nodes": 3}

    def get_entity_summary(self, **kwargs):
        self.calls.append(("get_entity_summary", kwargs))
        return {"entity_name": kwargs["entity_name"], "summary": "ok"}

    def get_entities_by_type(self, **kwargs):
        self.calls.append(("get_entities_by_type", kwargs))
        return []


class _StubAgent:
    def __init__(self):
        self.graph_id = "graph-1"
        self.simulation_id = "sim-1"
        self.simulation_requirement = "mock requirement"
        self.zep_tools = _StubZepTools()


def test_report_tool_registry_module_exists_and_exports_contract():
    assert ToolSpec is not None
    assert ReportToolRegistry is not None
    assert callable(build_report_tool_registry)


def test_build_report_tool_registry_exposes_canonical_tools_and_aliases():
    registry = build_report_tool_registry(_StubAgent())

    assert registry.valid_names() == {
        "insight_forge",
        "panorama_search",
        "quick_search",
        "interview_agents",
        "external_research",
    }
    assert registry.resolve_name("search_graph") == "quick_search"
    assert registry.resolve_name("get_simulation_context") == "insight_forge"
    assert registry.resolve_name("get_graph_statistics") == "get_graph_statistics"


def test_report_tool_registry_preserves_alias_execution_behavior():
    agent = _StubAgent()
    registry = build_report_tool_registry(agent)

    result = registry.execute("search_graph", {"query": "alpha"}, report_context="ctx")

    assert result == "quick:alpha:10"
    assert agent.zep_tools.calls == [
        ("quick_search", {"graph_id": "graph-1", "query": "alpha", "limit": 10})
    ]


def test_report_tool_registry_preserves_legacy_statistics_tool_behavior():
    registry = build_report_tool_registry(_StubAgent())

    result = registry.execute("get_graph_statistics", {}, report_context="")

    assert json.loads(result) == {"graph_id": "graph-1", "total_nodes": 3}
