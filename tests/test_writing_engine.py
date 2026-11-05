from pathlib import Path

from academic_engine.ai_providers import AIProvider
from academic_engine.document_parser import parse_document
from academic_engine.writing_engine import AcademicWritingEngine, build_context
from academic_engine.writing_models import ProviderRequest, WritingMode, WritingSuggestion


class FakeProvider(AIProvider):
    name = "fake"

    def improve(self, context, request):
        return WritingSuggestion(
            element_id="",
            original_text=context.selected_text,
            revised_text=context.selected_text.replace("is", "remains"),
            mode=context.mode,
            changes_made=["Improved verb precision"],
            explanation="A controlled wording improvement.",
            citation_preservation_status="preserved",
        )


def test_context_contains_adjacent_paragraph_and_mode(tmp_path: Path) -> None:
    path = tmp_path / "paper.txt"
    path.write_text("Heading\nThe method is valid.\nThe result follows.", encoding="utf-8")
    parsed = parse_document(path)
    context = build_context(parsed, parsed.elements[1].id, WritingMode.TECHNICAL_RESEARCH)
    assert context.previous_text == "Heading"
    assert context.following_text == "The result follows."
    assert context.mode is WritingMode.TECHNICAL_RESEARCH


def test_engine_validates_numeric_preservation(tmp_path: Path) -> None:
    path = tmp_path / "paper.txt"
    path.write_text("The sample included 42 observations.", encoding="utf-8")
    parsed = parse_document(path)
    engine = AcademicWritingEngine({"fake": FakeProvider()})
    suggestion = engine.improve(
        parsed,
        parsed.elements[0].id,
        WritingMode.ACADEMIC_RESEARCH,
        "fake",
        ProviderRequest(),
    )
    assert suggestion.revised_text == "The sample included 42 observations."
    assert suggestion.validation_warnings == []
