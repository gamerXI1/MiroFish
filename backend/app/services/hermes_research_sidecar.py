"""Hermes-backed external research sidecar behind the existing /research/query contract."""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional
from urllib.parse import urlparse

from dotenv import load_dotenv
from flask import Flask, jsonify, request


HermesRunner = Callable[..., str]


def load_repo_dotenv_for_sidecar(script_path: str | os.PathLike[str]) -> Path | None:
    env_path = Path(script_path).resolve().parents[1] / ".env"
    if not env_path.exists():
        return None
    load_dotenv(env_path, override=True)
    return env_path


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def _build_prompt(*, query: str, max_sources: int, trusted_domains: list[str]) -> str:
    domain_clause = (
        "Only keep sources whose hostname is in this allowlist (or a subdomain): "
        + ", ".join(trusted_domains)
        if trusted_domains
        else "Use the most relevant externally retrieved sources you can verify."
    )
    return (
        "You are a web research sidecar for MiroFish.\n"
        "Use the web_search and web_extract tools to gather grounded external sources.\n"
        "Do not answer from memory. Do not use any tools other than web_search and web_extract.\n"
        f"Research query: {query}\n"
        f"Maximum sources: {max_sources}\n"
        f"{domain_clause}\n"
        "Return exactly one JSON object with this schema and no markdown fences or extra prose:\n"
        "{\n"
        '  "sources": [\n'
        "    {\n"
        '      "title": "source title",\n'
        '      "url": "https://...",\n'
        '      "summary": "1-2 sentence grounded summary",\n'
        '      "content_excerpt": "short supporting excerpt"\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "If you cannot find trustworthy sources, return {\"sources\": []}."
    )


def _normalize_domain(value: str) -> str:
    return value.strip().lower().lstrip('.')


def _hostname_matches(hostname: str, domain: str) -> bool:
    hostname = _normalize_domain(hostname)
    domain = _normalize_domain(domain)
    return hostname == domain or hostname.endswith('.' + domain)


def _source_allowed(url: str, trusted_domains: list[str]) -> bool:
    if not trusted_domains:
        return True
    hostname = urlparse(url).hostname or ""
    return any(_hostname_matches(hostname, domain) for domain in trusted_domains)


def _strip_markdown_fences(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _extract_json_object(text: str) -> dict[str, Any]:
    cleaned = re.sub(r"^session_id:.*$", "", text, flags=re.MULTILINE).strip()
    cleaned = _strip_markdown_fences(cleaned)
    if not cleaned:
        raise ValueError("empty_hermes_output")

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    last_obj: Optional[dict[str, Any]] = None
    for match in re.finditer(r"\{", cleaned):
        try:
            value, _ = decoder.raw_decode(cleaned[match.start():])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            last_obj = value
    if last_obj is None:
        raise ValueError("invalid_hermes_json")
    return last_obj


def _run_hermes_query(*, command: str, prompt: str, timeout_seconds: float, hermes_home: str | None) -> str:
    cmd = shlex.split(command) + [
        "chat",
        "--query-file",
        "-",
        "-Q",
        "--source",
        "tool",
        "--ignore-rules",
        "--reasoning",
        "low",
        "--max-turns",
        "12",
        "-t",
        "web",
    ]
    env = os.environ.copy()
    if hermes_home:
        env["HERMES_HOME"] = hermes_home

    completed = subprocess.run(
        cmd,
        input=prompt,
        text=True,
        capture_output=True,
        timeout=timeout_seconds,
        env=env,
        check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        raise RuntimeError(f"hermes_invocation_failed: {detail[:300]}")
    return completed.stdout


class HermesResearchBridge:
    PROVIDER_LABEL = "hermes-sidecar"

    def __init__(
        self,
        *,
        command: str | None = None,
        hermes_home: str | None = None,
        timeout_seconds: float | None = None,
        runner: HermesRunner | None = None,
    ):
        self.command = command or os.environ.get("HERMES_RESEARCH_COMMAND", "hermes")
        self.hermes_home = hermes_home or os.environ.get("HERMES_RESEARCH_HERMES_HOME")
        self.timeout_seconds = timeout_seconds or float(os.environ.get("HERMES_RESEARCH_TIMEOUT_SECONDS", "120"))
        self.runner = runner or _run_hermes_query

    def query(
        self,
        *,
        query: str,
        mode: str = "web_search_and_extract",
        max_sources: int = 5,
        trusted_domains: list[str] | None = None,
        browser_fallback: bool = False,
    ) -> dict[str, Any]:
        trusted_domains = trusted_domains or []
        normalized_query = (query or "").strip()
        if not normalized_query:
            return self._failure(query=query, error="invalid_query")
        if mode != "web_search_and_extract":
            return self._failure(query=normalized_query, error="unsupported_mode")
        if browser_fallback:
            return self._failure(query=normalized_query, error="browser_fallback_not_supported")

        try:
            max_sources = int(max_sources)
        except (TypeError, ValueError):
            return self._failure(query=normalized_query, error="invalid_max_sources")
        max_sources = max(1, min(max_sources, 10))

        try:
            raw_output = self.runner(
                command=self.command,
                prompt=_build_prompt(
                    query=normalized_query,
                    max_sources=max_sources,
                    trusted_domains=trusted_domains,
                ),
                timeout_seconds=self.timeout_seconds,
                hermes_home=self.hermes_home,
            )
            parsed = _extract_json_object(raw_output)
        except Exception:
            return self._failure(query=normalized_query, error="hermes_query_failed")

        raw_sources = parsed.get("sources")
        if not isinstance(raw_sources, list):
            return self._failure(query=normalized_query, error="invalid_hermes_response")

        sources: list[dict[str, str]] = []
        for item in raw_sources:
            if not isinstance(item, dict):
                continue
            source = {
                "title": str(item.get("title", "")).strip(),
                "url": str(item.get("url", "")).strip(),
                "summary": str(item.get("summary", "")).strip(),
                "content_excerpt": str(item.get("content_excerpt", item.get("excerpt", ""))).strip(),
            }
            if not source["url"] or not _source_allowed(source["url"], trusted_domains):
                continue
            sources.append(source)
            if len(sources) >= max_sources:
                break

        if not sources:
            return self._failure(query=normalized_query, error="no_sources_found")

        return {
            "success": True,
            "query": normalized_query,
            "retrieved_at": _utc_now_iso(),
            "provider": self.PROVIDER_LABEL,
            "sources": sources,
        }

    @classmethod
    def _failure(cls, *, query: str, error: str) -> dict[str, Any]:
        return {
            "success": False,
            "query": query,
            "retrieved_at": None,
            "provider": cls.PROVIDER_LABEL,
            "sources": [],
            "error": error,
        }


def create_hermes_research_sidecar_app(*, bridge: HermesResearchBridge | None = None) -> Flask:
    app = Flask(__name__)
    research_bridge = bridge or HermesResearchBridge()

    @app.get('/health')
    def health():
        return {"status": "ok", "service": "hermes-research-sidecar"}

    @app.post('/research/query')
    def research_query():
        payload = request.get_json(silent=True) or {}
        query = payload.get("query", "")
        mode = payload.get("mode", "web_search_and_extract")
        browser_fallback = bool(payload.get("browser_fallback", False))
        if mode != "web_search_and_extract":
            return jsonify(HermesResearchBridge._failure(query=query, error="unsupported_mode"))
        if browser_fallback:
            return jsonify(HermesResearchBridge._failure(query=query, error="browser_fallback_not_supported"))
        result = research_bridge.query(
            query=query,
            mode=mode,
            max_sources=payload.get("max_sources", 5),
            trusted_domains=payload.get("trusted_domains") or [],
            browser_fallback=browser_fallback,
        )
        return jsonify(result)

    return app
