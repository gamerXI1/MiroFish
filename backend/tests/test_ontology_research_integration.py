import io

from app import create_app
from app.api import graph as graph_api
from app.models.project import ProjectManager, ProjectStatus
from app.services.external_research_client import (
    ExternalResearchItem,
    ExternalResearchResult,
)


def _post_ontology(client, **extra_form):
    data = {
        "simulation_requirement": "Simulate the discussion.",
        "files": (io.BytesIO(b"A short source document."), "source.md"),
    }
    data.update(extra_form)
    return client.post(
        "/api/graph/ontology/generate",
        data=data,
        content_type="multipart/form-data",
    )


class _RecordingGenerator:
    def __init__(self, sink):
        self.sink = sink

    def generate(self, **kwargs):
        self.sink.update(kwargs)
        return {
            "entity_types": [{"name": "Entity"}],
            "edge_types": [{"name": "RELATED_TO"}],
            "analysis_summary": "ok",
        }


def test_ontology_api_enriches_additional_context_and_persists_research(tmp_path, monkeypatch):
    captured = {}

    class FakeResearchClient:
        def query(self, **kwargs):
            captured["research_query"] = kwargs
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

    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(tmp_path))
    monkeypatch.setattr(graph_api, "OntologyGenerator", lambda: _RecordingGenerator(captured))
    monkeypatch.setattr(graph_api.FileParser, "extract_text", lambda _path: "A short source document.")
    monkeypatch.setattr(graph_api.TextProcessor, "preprocess_text", lambda text: text)
    monkeypatch.setattr(graph_api, "ExternalResearchClient", lambda: FakeResearchClient(), raising=False)

    app = create_app()
    app.config.update(TESTING=True)
    response = _post_ontology(
        app.test_client(),
        additional_context="Operator note.",
        research_enabled="true",
        research_query="latest alpha",
    )

    assert response.status_code == 200
    assert response.json["success"] is True
    assert captured["research_query"] == {
        "query": "latest alpha",
        "max_sources": 5,
        "trusted_domains": None,
        "browser_fallback": False,
    }
    assert "Operator note." in captured["additional_context"]
    assert "外部现实世界参考资料" in captured["additional_context"]
    assert "Alpha headline" in captured["additional_context"]
    assert "https://example.com/alpha" in captured["additional_context"]

    project_id = response.json["data"]["project_id"]
    project = ProjectManager.get_project(project_id)
    assert project.status == ProjectStatus.ONTOLOGY_GENERATED
    research_context = ProjectManager.get_research_context(project_id)
    assert research_context is not None
    assert research_context["query"] == "latest alpha"
    assert research_context["provider"] == "hermes-web-search"


def test_ontology_api_research_failure_does_not_block_generation(tmp_path, monkeypatch):
    captured = {}

    class FakeResearchClient:
        def query(self, **kwargs):
            captured["research_query"] = kwargs
            return ExternalResearchResult(
                success=False,
                query="latest alpha",
                retrieved_at=None,
                items=[],
                provider=None,
                error="research_unavailable",
            )

    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(tmp_path))
    monkeypatch.setattr(graph_api, "OntologyGenerator", lambda: _RecordingGenerator(captured))
    monkeypatch.setattr(graph_api.FileParser, "extract_text", lambda _path: "A short source document.")
    monkeypatch.setattr(graph_api.TextProcessor, "preprocess_text", lambda text: text)
    monkeypatch.setattr(graph_api, "ExternalResearchClient", lambda: FakeResearchClient(), raising=False)

    app = create_app()
    app.config.update(TESTING=True)
    response = _post_ontology(
        app.test_client(),
        research_enabled="true",
        research_query="latest alpha",
    )

    assert response.status_code == 200
    assert response.json["success"] is True
    assert captured["research_query"]["query"] == "latest alpha"
    assert captured["additional_context"] is None

    project_id = response.json["data"]["project_id"]
    assert ProjectManager.get_research_context(project_id) is None


def test_ontology_api_without_research_flag_preserves_old_behavior(tmp_path, monkeypatch):
    captured = {}

    def unexpected_client():
        raise AssertionError("external research client should not be created")

    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(tmp_path))
    monkeypatch.setattr(graph_api, "OntologyGenerator", lambda: _RecordingGenerator(captured))
    monkeypatch.setattr(graph_api.FileParser, "extract_text", lambda _path: "A short source document.")
    monkeypatch.setattr(graph_api.TextProcessor, "preprocess_text", lambda text: text)
    monkeypatch.setattr(graph_api, "ExternalResearchClient", unexpected_client, raising=False)

    app = create_app()
    app.config.update(TESTING=True)
    response = _post_ontology(app.test_client())

    assert response.status_code == 200
    assert response.json["success"] is True
    assert captured["additional_context"] is None

    project_id = response.json["data"]["project_id"]
    assert ProjectManager.get_research_context(project_id) is None


def test_ontology_api_rejects_invalid_research_enabled_value(tmp_path, monkeypatch):
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(tmp_path))

    app = create_app()
    app.config.update(TESTING=True)
    response = _post_ontology(app.test_client(), research_enabled="maybe")

    assert response.status_code == 400
    assert response.json["success"] is False
    assert "research_enabled" in response.json["error"]
