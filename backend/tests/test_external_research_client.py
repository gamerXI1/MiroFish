from urllib.error import URLError

from app.services.external_research_client import (
    ExternalResearchClient,
    ExternalResearchItem,
    ExternalResearchResult,
)


class _FakeResponse:
    def __init__(self, payload, *, http_error=None):
        self._payload = payload
        self._http_error = http_error

    def raise_for_status(self):
        if self._http_error:
            raise self._http_error

    def json(self):
        return self._payload


class _FakeSession:
    def __init__(self, *, response=None, exc=None):
        self.response = response
        self.exc = exc
        self.calls = []

    def post(self, url, *, json=None, headers=None, timeout=None):
        self.calls.append(
            {
                "url": url,
                "json": json,
                "headers": headers,
                "timeout": timeout,
            }
        )
        if self.exc:
            raise self.exc
        return self.response


def test_external_research_client_normalizes_success_response():
    session = _FakeSession(
        response=_FakeResponse(
            {
                "success": True,
                "query": "latest alpha",
                "retrieved_at": "2026-08-25T00:00:00Z",
                "provider": "hermes-web-search",
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
    )
    client = ExternalResearchClient(
        base_url="http://research.local",
        session=session,
        timeout_seconds=9.5,
    )

    result = client.query(
        query="latest alpha",
        max_sources=3,
        trusted_domains=["example.com"],
        browser_fallback=True,
    )

    assert result == ExternalResearchResult(
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
    assert session.calls == [
        {
            "url": "http://research.local/research/query",
            "json": {
                "query": "latest alpha",
                "mode": "web_search_and_extract",
                "max_sources": 3,
                "trusted_domains": ["example.com"],
                "browser_fallback": True,
            },
            "headers": {},
            "timeout": 9.5,
        }
    ]


def test_external_research_client_returns_unavailable_on_transport_failure():
    session = _FakeSession(exc=URLError("network down"))
    client = ExternalResearchClient(base_url="http://research.local", session=session)

    result = client.query(query="latest alpha")

    assert result == ExternalResearchResult(
        success=False,
        query="latest alpha",
        retrieved_at=None,
        items=[],
        provider=None,
        error="research_unavailable",
    )


def test_external_research_client_fails_closed_when_not_configured():
    client = ExternalResearchClient(base_url=None)

    result = client.query(query="latest alpha")

    assert result == ExternalResearchResult(
        success=False,
        query="latest alpha",
        retrieved_at=None,
        items=[],
        provider=None,
        error="research_not_configured",
    )
