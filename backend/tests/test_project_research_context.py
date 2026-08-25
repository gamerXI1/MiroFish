import json

from app.models.project import ProjectManager


def test_project_manager_saves_research_context_separately_from_project_metadata(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(tmp_path))
    project = ProjectManager.create_project("Research Project")
    project_dir = tmp_path / project.project_id
    meta_path = project_dir / "project.json"
    before_meta = json.loads(meta_path.read_text(encoding="utf-8"))

    payload = {
        "source_type": "external_research",
        "query": "latest alpha",
        "retrieved_at": "2026-08-25T00:00:00Z",
        "provider": "hermes-web-search",
        "items": [
            {
                "title": "Alpha headline",
                "url": "https://example.com/alpha",
                "summary": "Alpha summary",
                "excerpt": "Alpha excerpt",
            }
        ],
    }

    ProjectManager.save_research_context(project.project_id, payload)

    research_path = project_dir / "research_context.json"
    assert research_path.exists()
    assert json.loads(research_path.read_text(encoding="utf-8")) == payload
    assert ProjectManager.get_research_context(project.project_id) == payload

    after_meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert after_meta == before_meta


def test_project_manager_returns_none_for_missing_research_context(tmp_path, monkeypatch):
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(tmp_path))
    project = ProjectManager.create_project("Research Project")

    assert ProjectManager.get_research_context(project.project_id) is None
