import json

import httpx
from academic_engine.ai_providers import OpenAIProvider
from academic_engine.writing_models import ProviderRequest, WritingContext


def test_openai_adapter_parses_structured_response(monkeypatch) -> None:
    response = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "revised_text": "The evidence is clear.",
                            "changes_made": ["clarity"],
                            "explanation": "Removed filler.",
                            "meaning_change_warning": None,
                            "citation_preservation_status": "preserved",
                            "validation_warnings": [],
                        }
                    )
                }
            }
        ]
    }

    def fake_post(self, url, headers, json):
        return httpx.Response(200, json=response, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.Client, "post", fake_post)
    result = OpenAIProvider("test-key").improve(
        WritingContext(selected_text="The evidence is clear."), ProviderRequest()
    )
    assert result.revised_text == "The evidence is clear."
    assert result.citation_preservation_status == "preserved"
