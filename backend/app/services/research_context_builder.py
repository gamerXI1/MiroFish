"""Build and render optional external research context without changing core source authority."""

from __future__ import annotations

from typing import Any, Optional

from .external_research_client import ExternalResearchResult


class ResearchContextBuilder:
    """Convert optional external research results into renderable, persisted context."""

    @staticmethod
    def build_for_ontology(
        research_result: ExternalResearchResult,
    ) -> Optional[dict[str, Any]]:
        if not research_result.success or not research_result.items:
            return None

        return {
            "source_type": "external_research",
            "query": research_result.query,
            "retrieved_at": research_result.retrieved_at,
            "provider": research_result.provider,
            "items": [
                {
                    "title": item.title,
                    "url": item.url,
                    "summary": item.summary,
                    "excerpt": item.excerpt,
                }
                for item in research_result.items
            ],
        }

    @staticmethod
    def render_for_ontology(context: Optional[dict[str, Any]]) -> str:
        if not context:
            return ""

        lines = [
            "## 外部现实世界参考资料",
            "以下内容来自外部网络检索，仅供本体生成时补充参考，不应视为模拟事实。",
        ]
        lines.extend(ResearchContextBuilder._render_metadata(context))
        lines.extend(ResearchContextBuilder._render_items(context))
        return "\n".join(lines).strip()

    @staticmethod
    def render_for_report(context: Optional[dict[str, Any]]) -> str:
        if not context:
            return ""

        lines = [
            "## 外部现实世界参考资料（非模拟事实）",
            "以下内容属于现实世界外部参考，不应与模拟预测事实混合解释。",
        ]
        lines.extend(ResearchContextBuilder._render_metadata(context))
        lines.extend(ResearchContextBuilder._render_items(context))
        return "\n".join(lines).strip()

    @staticmethod
    def _render_metadata(context: dict[str, Any]) -> list[str]:
        lines: list[str] = []
        if context.get("query"):
            lines.append(f"- 查询: {context['query']}")
        if context.get("retrieved_at"):
            lines.append(f"- 检索时间: {context['retrieved_at']}")
        if context.get("provider"):
            lines.append(f"- 提供方: {context['provider']}")
        return lines

    @staticmethod
    def _render_items(context: dict[str, Any]) -> list[str]:
        lines: list[str] = []
        for index, item in enumerate(context.get("items", []), start=1):
            lines.extend(
                [
                    f"### 来源 {index}: {item.get('title', '')}",
                    f"- URL: {item.get('url', '')}",
                    f"- 摘要: {item.get('summary', '')}",
                    f"- 摘录: {item.get('excerpt', '')}",
                ]
            )
        return lines
