"""Canonical report-tool registry for ReportAgent.

This module centralizes:
- canonical tool metadata exposed to the model
- legacy compatibility tool names / redirects
- execution dispatch for all report-agent tool calls
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable

from .external_research_client import ExternalResearchClient
from .research_context_builder import ResearchContextBuilder
from ..utils.locale import t
from ..utils.logger import get_logger

logger = get_logger("mirofish.report_tool_registry")


TOOL_DESC_INSIGHT_FORGE = """\
【深度洞察检索 - 强大的检索工具】
这是我们强大的检索函数，专为深度分析设计。它会：
1. 自动将你的问题分解为多个子问题
2. 从多个维度检索模拟图谱中的信息
3. 整合语义搜索、实体分析、关系链追踪的结果
4. 返回最全面、最深度的检索内容

【使用场景】
- 需要深入分析某个话题
- 需要了解事件的多个方面
- 需要获取支撑报告章节的丰富素材

【返回内容】
- 相关事实原文（可直接引用）
- 核心实体洞察
- 关系链分析"""

TOOL_DESC_PANORAMA_SEARCH = """\
【广度搜索 - 获取全貌视图】
这个工具用于获取模拟结果的完整全貌，特别适合了解事件演变过程。它会：
1. 获取所有相关节点和关系
2. 区分当前有效的事实和历史/过期的事实
3. 帮助你了解舆情是如何演变的

【使用场景】
- 需要了解事件的完整发展脉络
- 需要对比不同阶段的舆情变化
- 需要获取全面的实体和关系信息

【返回内容】
- 当前有效事实（模拟最新结果）
- 历史/过期事实（演变记录）
- 所有涉及的实体"""

TOOL_DESC_QUICK_SEARCH = """\
【简单搜索 - 快速检索】
轻量级的快速检索工具，适合简单、直接的信息查询。

【使用场景】
- 需要快速查找某个具体信息
- 需要验证某个事实
- 简单的信息检索

【返回内容】
- 与查询最相关的事实列表"""

TOOL_DESC_INTERVIEW_AGENTS = """\
【深度采访 - 真实Agent采访（双平台）】
调用OASIS模拟环境的采访API，对正在运行的模拟Agent进行真实采访！
这不是LLM模拟，而是调用真实的采访接口获取模拟Agent的原始回答。
默认在Twitter和Reddit两个平台同时采访，获取更全面的观点。

功能流程：
1. 自动读取人设文件，了解所有模拟Agent
2. 智能选择与采访主题最相关的Agent（如学生、媒体、官方等）
3. 自动生成采访问题
4. 调用 /api/simulation/interview/batch 接口在双平台进行真实采访
5. 整合所有采访结果，提供多视角分析

【使用场景】
- 需要从不同角色视角了解事件看法（学生怎么看？媒体怎么看？官方怎么说？）
- 需要收集多方意见和立场
- 需要获取模拟Agent的真实回答（来自OASIS模拟环境）
- 想让报告更生动，包含"采访实录"

【返回内容】
- 被采访Agent的身份信息
- 各Agent在Twitter和Reddit两个平台的采访回答
- 关键引言（可直接引用）
- 采访摘要和观点对比

【重要】需要OASIS模拟环境正在运行才能使用此功能！"""

TOOL_DESC_EXTERNAL_RESEARCH = """\
【外部研究 - 现实世界网络参考】
当模拟图谱内的信息不足以回答问题时，使用这个工具获取外部现实世界参考资料。

【使用场景】
- 需要补充现实世界的最新公开信息
- 需要对比模拟结果与外部世界报道
- 需要引入网络来源作为辅助参考

【重要边界】
- 返回的是外部现实世界参考，不是模拟事实
- 不会替代图谱检索，也不会自动回退到Zep搜索
- 仅在明确需要外部研究时使用"""


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, str]
    handler: Callable[[dict[str, Any], str], str]
    canonical_name: str | None = None
    expose_to_model: bool = True


class ReportToolRegistry:
    def __init__(self, specs: list[ToolSpec]):
        self._specs = {spec.name: spec for spec in specs}

    def valid_names(self) -> set[str]:
        return {
            spec.name
            for spec in self._specs.values()
            if spec.expose_to_model
        }

    def resolve_name(self, name: str) -> str:
        spec = self._specs.get(name)
        if spec is None:
            return name
        return spec.canonical_name or spec.name

    def prompt_tools(self) -> dict[str, dict[str, Any]]:
        return {
            spec.name: {
                "name": spec.name,
                "description": spec.description,
                "parameters": spec.parameters,
            }
            for spec in self._specs.values()
            if spec.expose_to_model
        }

    def execute(self, name: str, parameters: dict[str, Any], report_context: str = "") -> str:
        spec = self._specs.get(name)
        if spec is None:
            valid = ", ".join(sorted(self.valid_names()))
            return f"未知工具: {name}。请使用以下工具之一: {valid}"
        return spec.handler(parameters, report_context)


def build_report_tool_registry(agent: Any) -> ReportToolRegistry:
    registry: ReportToolRegistry | None = None

    def insight_forge_handler(parameters: dict[str, Any], report_context: str) -> str:
        query = parameters.get("query", "")
        ctx = parameters.get("report_context", "") or report_context
        result = agent.zep_tools.insight_forge(
            graph_id=agent.graph_id,
            query=query,
            simulation_requirement=agent.simulation_requirement,
            report_context=ctx,
        )
        return result.to_text()

    def panorama_search_handler(parameters: dict[str, Any], _report_context: str) -> str:
        query = parameters.get("query", "")
        include_expired = parameters.get("include_expired", True)
        if isinstance(include_expired, str):
            include_expired = include_expired.lower() in ["true", "1", "yes"]
        result = agent.zep_tools.panorama_search(
            graph_id=agent.graph_id,
            query=query,
            include_expired=include_expired,
        )
        return result.to_text()

    def quick_search_handler(parameters: dict[str, Any], _report_context: str) -> str:
        query = parameters.get("query", "")
        limit = parameters.get("limit", 10)
        if isinstance(limit, str):
            limit = int(limit)
        result = agent.zep_tools.quick_search(
            graph_id=agent.graph_id,
            query=query,
            limit=limit,
        )
        return result.to_text()

    def interview_agents_handler(parameters: dict[str, Any], _report_context: str) -> str:
        interview_topic = parameters.get("interview_topic", parameters.get("query", ""))
        max_agents = parameters.get("max_agents", 5)
        if isinstance(max_agents, str):
            max_agents = int(max_agents)
        max_agents = min(max_agents, 10)
        result = agent.zep_tools.interview_agents(
            simulation_id=agent.simulation_id,
            interview_requirement=interview_topic,
            simulation_requirement=agent.simulation_requirement,
            max_agents=max_agents,
        )
        return result.to_text()

    def external_research_handler(parameters: dict[str, Any], _report_context: str) -> str:
        query = parameters.get("query", "")
        if not query:
            return "外部研究不可用: missing_query"

        max_sources = parameters.get("max_sources", 5)
        if isinstance(max_sources, str):
            max_sources = int(max_sources)
        max_sources = max(1, min(max_sources, 10))

        result = ExternalResearchClient().query(
            query=query,
            max_sources=max_sources,
            trusted_domains=None,
            browser_fallback=False,
        )
        if not result.success:
            return f"外部研究不可用: {result.error or 'research_unavailable'}"

        context = ResearchContextBuilder.build_for_ontology(result)
        if not context:
            return "外部研究未返回可用来源"
        return ResearchContextBuilder.render_for_report(context)

    def search_graph_handler(parameters: dict[str, Any], report_context: str) -> str:
        logger.info(t("report.redirectToQuickSearch"))
        assert registry is not None
        return registry.execute("quick_search", parameters, report_context)

    def graph_statistics_handler(_parameters: dict[str, Any], _report_context: str) -> str:
        result = agent.zep_tools.get_graph_statistics(agent.graph_id)
        return json.dumps(result, ensure_ascii=False, indent=2)

    def entity_summary_handler(parameters: dict[str, Any], _report_context: str) -> str:
        entity_name = parameters.get("entity_name", "")
        result = agent.zep_tools.get_entity_summary(
            graph_id=agent.graph_id,
            entity_name=entity_name,
        )
        return json.dumps(result, ensure_ascii=False, indent=2)

    def simulation_context_handler(parameters: dict[str, Any], report_context: str) -> str:
        logger.info(t("report.redirectToInsightForge"))
        query = parameters.get("query", agent.simulation_requirement)
        assert registry is not None
        return registry.execute("insight_forge", {"query": query}, report_context)

    def entities_by_type_handler(parameters: dict[str, Any], _report_context: str) -> str:
        entity_type = parameters.get("entity_type", "")
        nodes = agent.zep_tools.get_entities_by_type(
            graph_id=agent.graph_id,
            entity_type=entity_type,
        )
        result = [n.to_dict() for n in nodes]
        return json.dumps(result, ensure_ascii=False, indent=2)

    registry = ReportToolRegistry(
        [
            ToolSpec(
                name="insight_forge",
                description=TOOL_DESC_INSIGHT_FORGE,
                parameters={
                    "query": "你想深入分析的问题或话题",
                    "report_context": "当前报告章节的上下文（可选，有助于生成更精准的子问题）",
                },
                handler=insight_forge_handler,
            ),
            ToolSpec(
                name="panorama_search",
                description=TOOL_DESC_PANORAMA_SEARCH,
                parameters={
                    "query": "搜索查询，用于相关性排序",
                    "include_expired": "是否包含过期/历史内容（默认True）",
                },
                handler=panorama_search_handler,
            ),
            ToolSpec(
                name="quick_search",
                description=TOOL_DESC_QUICK_SEARCH,
                parameters={
                    "query": "搜索查询字符串",
                    "limit": "返回结果数量（可选，默认10）",
                },
                handler=quick_search_handler,
            ),
            ToolSpec(
                name="interview_agents",
                description=TOOL_DESC_INTERVIEW_AGENTS,
                parameters={
                    "interview_topic": "采访主题或需求描述（如：'了解学生对宿舍甲醛事件的看法'）",
                    "max_agents": "最多采访的Agent数量（可选，默认5，最大10）",
                },
                handler=interview_agents_handler,
            ),
            ToolSpec(
                name="external_research",
                description=TOOL_DESC_EXTERNAL_RESEARCH,
                parameters={
                    "query": "外部研究查询词",
                    "max_sources": "返回来源数量（可选，默认5，最大10）",
                },
                handler=external_research_handler,
            ),
            ToolSpec(
                name="search_graph",
                description="",
                parameters={},
                handler=search_graph_handler,
                canonical_name="quick_search",
                expose_to_model=False,
            ),
            ToolSpec(
                name="get_graph_statistics",
                description="",
                parameters={},
                handler=graph_statistics_handler,
                expose_to_model=False,
            ),
            ToolSpec(
                name="get_entity_summary",
                description="",
                parameters={},
                handler=entity_summary_handler,
                expose_to_model=False,
            ),
            ToolSpec(
                name="get_simulation_context",
                description="",
                parameters={},
                handler=simulation_context_handler,
                canonical_name="insight_forge",
                expose_to_model=False,
            ),
            ToolSpec(
                name="get_entities_by_type",
                description="",
                parameters={},
                handler=entities_by_type_handler,
                expose_to_model=False,
            ),
        ]
    )
    return registry
