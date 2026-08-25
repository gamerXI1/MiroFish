"""Thin fail-closed adapter for optional external research sidecars."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ..utils.logger import get_logger

logger = get_logger("mirofish.external_research_client")


@dataclass(frozen=True)
class ExternalResearchItem:
    title: str
    url: str
    summary: str
    excerpt: str


@dataclass(frozen=True)
class ExternalResearchResult:
    success: bool
    query: str
    retrieved_at: str | None
    items: list[ExternalResearchItem]
    provider: str | None
    error: str | None = None


class _UrllibResponse:
    def __init__(self, *, status_code: int, payload: dict[str, Any]):
        self.status_code = status_code
        self._payload = payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise HTTPError(url="", code=self.status_code, msg="http error", hdrs=None, fp=None)

    def json(self) -> dict[str, Any]:
        return self._payload


class _UrllibSession:
    def post(
        self,
        url: str,
        *,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> _UrllibResponse:
        request_headers = {"Content-Type": "application/json", **(headers or {})}
        data = None if json is None else __import__("json").dumps(json).encode("utf-8")
        request = Request(url, data=data, headers=request_headers, method="POST")
        with urlopen(request, timeout=timeout) as response:
            status_code = getattr(response, "status", response.getcode())
            payload = __import__("json").loads(response.read().decode("utf-8"))
        return _UrllibResponse(status_code=status_code, payload=payload)


class ExternalResearchClient:
    DEFAULT_MODE = "web_search_and_extract"
    DEFAULT_TIMEOUT_SECONDS = 60.0

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float | None = None,
        session: Any | None = None,
    ):
        self.base_url = (base_url or os.environ.get("EXTERNAL_RESEARCH_BASE_URL") or "").rstrip("/")
        self.api_key = api_key if api_key is not None else os.environ.get("EXTERNAL_RESEARCH_API_KEY")
        self.timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else float(os.environ.get("EXTERNAL_RESEARCH_TIMEOUT_SECONDS", self.DEFAULT_TIMEOUT_SECONDS))
        )
        self.session = session or _UrllibSession()

    def query(
        self,
        *,
        query: str,
        max_sources: int = 5,
        trusted_domains: list[str] | None = None,
        browser_fallback: bool = False,
    ) -> ExternalResearchResult:
        if not self.base_url:
            return self._failure(query=query, error="research_not_configured")

        payload = {
            "query": query,
            "mode": self.DEFAULT_MODE,
            "max_sources": max_sources,
            "trusted_domains": trusted_domains or [],
            "browser_fallback": browser_fallback,
        }
        headers: dict[str, str] = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            response = self.session.post(
                f"{self.base_url}/research/query",
                json=payload,
                headers=headers,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            raw = response.json()
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            logger.warning("external research unavailable", extra={"error": str(exc)})
            return self._failure(query=query, error="research_unavailable")
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            logger.warning("external research invalid response", extra={"error": str(exc)})
            return self._failure(query=query, error="research_invalid_response")

        if not raw.get("success", False):
            return self._failure(
                query=query,
                error=str(raw.get("error") or "research_unavailable"),
                provider=raw.get("provider"),
            )

        items = [
            ExternalResearchItem(
                title=str(item.get("title", "")),
                url=str(item.get("url", "")),
                summary=str(item.get("summary", "")),
                excerpt=str(item.get("content_excerpt", item.get("excerpt", ""))),
            )
            for item in raw.get("sources", [])
        ]
        return ExternalResearchResult(
            success=True,
            query=str(raw.get("query", query)),
            retrieved_at=raw.get("retrieved_at"),
            items=items,
            provider=raw.get("provider"),
            error=None,
        )

    @staticmethod
    def _failure(
        *,
        query: str,
        error: str,
        provider: str | None = None,
    ) -> ExternalResearchResult:
        return ExternalResearchResult(
            success=False,
            query=query,
            retrieved_at=None,
            items=[],
            provider=provider,
            error=error,
        )
