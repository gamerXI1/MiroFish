import os
from pathlib import Path

from app.services.hermes_research_sidecar import load_repo_dotenv_for_sidecar


def test_load_repo_dotenv_for_sidecar_reads_repo_root_env(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    backend_dir = repo_root / "backend"
    backend_dir.mkdir(parents=True)
    env_path = repo_root / ".env"
    env_path.write_text(
        "EXTERNAL_RESEARCH_BASE_URL=http://127.0.0.1:8788\n"
        "HERMES_RESEARCH_COMMAND=custom-hermes\n",
        encoding="utf-8",
    )

    monkeypatch.delenv("EXTERNAL_RESEARCH_BASE_URL", raising=False)
    monkeypatch.delenv("HERMES_RESEARCH_COMMAND", raising=False)

    loaded = load_repo_dotenv_for_sidecar(backend_dir / "run_hermes_research_sidecar.py")

    assert loaded == env_path
    assert os.environ["EXTERNAL_RESEARCH_BASE_URL"] == "http://127.0.0.1:8788"
    assert os.environ["HERMES_RESEARCH_COMMAND"] == "custom-hermes"


def test_load_repo_dotenv_for_sidecar_returns_none_when_missing(tmp_path, monkeypatch):
    backend_dir = tmp_path / "repo" / "backend"
    backend_dir.mkdir(parents=True)
    monkeypatch.delenv("EXTERNAL_RESEARCH_BASE_URL", raising=False)

    loaded = load_repo_dotenv_for_sidecar(backend_dir / "run_hermes_research_sidecar.py")

    assert loaded is None
    assert "EXTERNAL_RESEARCH_BASE_URL" not in os.environ
