from app.services.external_research_client import (
    ExternalResearchItem,
    ExternalResearchResult,
)
from app.services.research_context_builder import ResearchContextBuilder


def _sample_result() -> ExternalResearchResult:
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


def test_build_and_render_for_ontology_labels_external_provenance():
    context = ResearchContextBuilder.build_for_ontology(_sample_result())

    assert context is not None
    assert context["source_type"] == "external_research"
    rendered = ResearchContextBuilder.render_for_ontology(context)
    assert "外部现实世界参考资料" in rendered
    assert "Alpha headline" in rendered
    assert "https://example.com/alpha" in rendered
    assert "Alpha excerpt" in rendered
    assert "hermes-web-search" in rendered
    assert "2026-08-25T00:00:00Z" in rendered


def test_render_for_report_marks_external_context_as_non_simulated():
    context = ResearchContextBuilder.build_for_ontology(_sample_result())

    rendered = ResearchContextBuilder.render_for_report(context)

    assert "非模拟事实" in rendered
    assert "Alpha summary" in rendered
    assert "https://example.com/alpha" in rendered


def test_unavailable_research_yields_no_context_and_empty_rendering():
    result = ExternalResearchResult(
        success=False,
        query="latest alpha",
        retrieved_at=None,
        items=[],
        provider=None,
        error="research_unavailable",
    )

    context = ResearchContextBuilder.build_for_ontology(result)

    assert context is None
    assert ResearchContextBuilder.render_for_ontology(context) == ""
    assert ResearchContextBuilder.render_for_report(context) == ""
