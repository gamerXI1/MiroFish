import json

from app.services.external_research_client import ExternalResearchClient
from app.services.hermes_research_sidecar import (
    HermesResearchBridge,
    create_hermes_research_sidecar_app,
)


class _RecordingRunner:
    def __init__(self, output: str):
        self.output = output
        self.calls = []

    def __call__(self, *, command, prompt, timeout_seconds, hermes_home):
        self.calls.append(
            {
                "command": command,
                "prompt": prompt,
                "timeout_seconds": timeout_seconds,
                "hermes_home": hermes_home,
            }
        )
        return self.output


class _FakeBridge:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def query(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


class _FlaskSession:
    def __init__(self, client):
        self.client = client

    def post(self, url, *, json=None, headers=None, timeout=None):
        path = url.replace("http://sidecar.local", "")
        response = self.client.post(path, json=json, headers=headers)
        return _FlaskResponse(response)


class _FlaskResponse:
    def __init__(self, response):
        self.response = response
        self.status_code = response.status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise AssertionError(f"unexpected http error: {self.status_code}")

    def json(self):
        return self.response.get_json()


def test_bridge_normalizes_hermes_output_and_filters_domains():
    runner = _RecordingRunner(
        'session_id: 20260825_000000_abc123\n'
        '{"sources": ['
        '{"title": "Alpha", "url": "https://example.com/a", "summary": "A", "content_excerpt": "EA"},'
        '{"title": "Beta", "url": "https://blocked.com/b", "summary": "B", "content_excerpt": "EB"}'
        ']}'
    )
    bridge = HermesResearchBridge(
        runner=runner,
        command="hermes",
        hermes_home="/tmp/hermes-home",
        timeout_seconds=33,
    )

    result = bridge.query(
        query="latest alpha",
        max_sources=5,
        trusted_domains=["example.com"],
        browser_fallback=False,
        mode="web_search_and_extract",
    )

    assert result["success"] is True
    assert result["query"] == "latest alpha"
    assert result["provider"] == "hermes-sidecar"
    assert len(result["sources"]) == 1
    assert result["sources"][0]["url"] == "https://example.com/a"

    assert len(runner.calls) == 1
    call = runner.calls[0]
    assert call["command"] == "hermes"
    assert call["timeout_seconds"] == 33
    assert call["hermes_home"] == "/tmp/hermes-home"
    assert "web_search" in call["prompt"]
    assert "web_extract" in call["prompt"]
    assert "latest alpha" in call["prompt"]


def test_bridge_fails_closed_when_filtered_sources_empty():
    runner = _RecordingRunner(
        '{"sources": ['
        '{"title": "Blocked", "url": "https://blocked.com/b", "summary": "B", "content_excerpt": "EB"}'
        ']}'
    )
    bridge = HermesResearchBridge(runner=runner)

    result = bridge.query(
        query="latest alpha",
        max_sources=5,
        trusted_domains=["example.com"],
        browser_fallback=False,
        mode="web_search_and_extract",
    )

    assert result == {
        "success": False,
        "query": "latest alpha",
        "retrieved_at": None,
        "provider": "hermes-sidecar",
        "sources": [],
        "error": "no_sources_found",
    }


def test_sidecar_app_rejects_unsupported_request_options():
    bridge = _FakeBridge({"success": True})
    app = create_hermes_research_sidecar_app(bridge=bridge)
    client = app.test_client()

    response = client.post(
        "/research/query",
        json={
            "query": "latest alpha",
            "mode": "web_search_and_extract",
            "browser_fallback": True,
        },
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "success": False,
        "query": "latest alpha",
        "retrieved_at": None,
        "provider": "hermes-sidecar",
        "sources": [],
        "error": "browser_fallback_not_supported",
    }
    assert bridge.calls == []


def test_sidecar_app_and_external_client_contract_align():
    bridge = _FakeBridge(
        {
            "success": True,
            "query": "latest alpha",
            "retrieved_at": "2026-08-25T00:00:00Z",
            "provider": "hermes-sidecar",
            "sources": [
                {
                    "title": "Alpha headline",
                    "url": "https://example.com/alpha",
                    "summary": "Alpha summary",
                    "content_excerpt": "Alpha excerpt",
                }
            ],
        }
    )
    app = create_hermes_research_sidecar_app(bridge=bridge)
    client = ExternalResearchClient(
        base_url="http://sidecar.local",
        session=_FlaskSession(app.test_client()),
    )

    result = client.query(
        query="latest alpha",
        max_sources=3,
        trusted_domains=["example.com"],
        browser_fallback=False,
    )

    assert result.success is True
    assert result.query == "latest alpha"
    assert result.provider == "hermes-sidecar"
    assert len(result.items) == 1
    assert result.items[0].title == "Alpha headline"
    assert bridge.calls == [
        {
            "query": "latest alpha",
            "mode": "web_search_and_extract",
            "max_sources": 3,
            "trusted_domains": ["example.com"],
            "browser_fallback": False,
        }
    ]
