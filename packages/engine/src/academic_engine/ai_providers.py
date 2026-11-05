from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import httpx

from academic_engine.exceptions import ProviderUnavailableError
from academic_engine.models import ProviderConnectionResult, ProviderName
from academic_engine.writing_models import ProviderRequest, WritingContext, WritingSuggestion


class AIProvider(ABC):
    name: str

    @abstractmethod
    def improve(self, context: WritingContext, request: ProviderRequest) -> WritingSuggestion:
        raise NotImplementedError

    def test_connection(self) -> ProviderConnectionResult:
        return ProviderConnectionResult(
            provider=ProviderName(self.name),
            status="not_supported",
            message="This provider does not expose a connection test.",
        )


def _system_prompt() -> str:
    return (
        "You are an academic writing editor. Improve clarity, grammar, flow, and academic "
        "appropriateness without changing research meaning. Preserve all numbers, dates, "
        "equations, technical terms, proper nouns, citations, quotations, negation, and "
        "uncertainty. Never invent facts or sources. Return JSON only with keys: revised_text, "
        "changes_made (array of strings), explanation, meaning_change_warning (string or null), "
        "citation_preservation_status, validation_warnings (array of strings)."
    )


def _user_prompt(context: WritingContext) -> str:
    payload = context.model_dump(mode="json")
    return json.dumps(payload, ensure_ascii=False)


def _parse_response(raw: Dict[str, Any], context: WritingContext) -> WritingSuggestion:
    try:
        content = raw["revised_text"]
        if not isinstance(content, str) or not content.strip():
            raise ValueError("revised_text must be a non-empty string")
        return WritingSuggestion(
            element_id="",
            original_text=context.selected_text,
            revised_text=content,
            mode=context.mode,
            changes_made=raw.get("changes_made", []),
            explanation=raw.get("explanation", ""),
            meaning_change_warning=raw.get("meaning_change_warning"),
            citation_preservation_status=raw.get("citation_preservation_status", "not_verified"),
            validation_warnings=raw.get("validation_warnings", []),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ProviderUnavailableError(
            f"Provider returned invalid structured output: {error}"
        ) from error


class HTTPProvider(AIProvider):
    def __init__(self, api_key: Optional[str], base_url: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def _request(
        self, headers: Dict[str, str], payload: Dict[str, Any], request: ProviderRequest
    ) -> Dict[str, Any]:
        if not self.api_key:
            raise ProviderUnavailableError(f"{self.name} is not configured.")
        try:
            with httpx.Client(timeout=request.timeout_seconds) as client:
                response = client.post(self.base_url, headers=headers, json=payload)
                response.raise_for_status()
                body = response.json()
        except httpx.TimeoutException as error:
            raise ProviderUnavailableError(f"{self.name} request timed out.") from error
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 429:
                raise ProviderUnavailableError(f"{self.name} rate limit reached.") from error
            raise ProviderUnavailableError(
                f"{self.name} request failed with status {error.response.status_code}."
            ) from error
        except (httpx.HTTPError, ValueError) as error:
            raise ProviderUnavailableError(f"{self.name} request failed.") from error
        return body

    def _get(
        self, headers: Dict[str, str], request_path: str = "", timeout: float = 15
    ) -> Dict[str, Any]:
        if not self.api_key:
            raise ProviderUnavailableError(f"{self.name} is not configured.")
        try:
            with httpx.Client(timeout=timeout) as client:
                url = (
                    request_path
                    if request_path.startswith("http")
                    else (f"{self.base_url.rstrip('/')}/{request_path.lstrip('/')}")
                )
                response = client.get(url, headers=headers)
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException as error:
            raise ProviderUnavailableError(f"{self.name} connection timed out.") from error
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 429:
                raise ProviderUnavailableError(f"{self.name} rate limit reached.") from error
            raise ProviderUnavailableError(
                f"{self.name} connection failed with status {error.response.status_code}."
            ) from error
        except (httpx.HTTPError, ValueError) as error:
            raise ProviderUnavailableError(f"{self.name} connection failed.") from error


class OpenAIProvider(HTTPProvider):
    name = "openai"

    def __init__(self, api_key: Optional[str]):
        super().__init__(api_key, "https://api.openai.com/v1/chat/completions")

    def improve(self, context: WritingContext, request: ProviderRequest) -> WritingSuggestion:
        body = self._request(
            {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            {
                "model": request.model or "gpt-4o-mini",
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": _system_prompt()},
                    {"role": "user", "content": _user_prompt(context)},
                ],
            },
            request,
        )
        try:
            raw = json.loads(body["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise ProviderUnavailableError("OpenAI returned an unusable response.") from error
        return _parse_response(raw, context)

    def test_connection(self) -> ProviderConnectionResult:
        body = self._get(
            {"Authorization": f"Bearer {self.api_key}"},
            "https://api.openai.com/v1/models",
        )
        models = [item["id"] for item in body.get("data", []) if item.get("id")]
        return ProviderConnectionResult(
            provider=ProviderName.OPENAI,
            status="connection_successful",
            models=models[:100],
            message="OpenAI credentials and model listing are available.",
        )


class AnthropicProvider(HTTPProvider):
    name = "anthropic"

    def __init__(self, api_key: Optional[str]):
        super().__init__(api_key, "https://api.anthropic.com/v1/messages")

    def improve(self, context: WritingContext, request: ProviderRequest) -> WritingSuggestion:
        body = self._request(
            {
                "x-api-key": self.api_key or "",
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            {
                "model": request.model or "claude-3-5-haiku-latest",
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
                "system": _system_prompt(),
                "messages": [{"role": "user", "content": _user_prompt(context)}],
            },
            request,
        )
        try:
            raw = json.loads(body["content"][0]["text"])
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise ProviderUnavailableError("Anthropic returned an unusable response.") from error
        return _parse_response(raw, context)

    def test_connection(self) -> ProviderConnectionResult:
        request = ProviderRequest(model="claude-3-5-haiku-latest", max_tokens=16)
        self._request(
            {
                "x-api-key": self.api_key or "",
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            {
                "model": request.model,
                "max_tokens": request.max_tokens,
                "messages": [{"role": "user", "content": "Reply with OK."}],
            },
            request,
        )
        return ProviderConnectionResult(
            provider=ProviderName.ANTHROPIC,
            status="connection_successful",
            models=["claude-3-5-haiku-latest"],
            message="Anthropic credentials and the default model are available.",
        )


class GeminiProvider(HTTPProvider):
    name = "google"

    def __init__(self, api_key: Optional[str]):
        super().__init__(api_key, "https://generativelanguage.googleapis.com/v1beta/models")

    def improve(self, context: WritingContext, request: ProviderRequest) -> WritingSuggestion:
        if not self.api_key:
            raise ProviderUnavailableError("google is not configured.")
        model = request.model or "gemini-1.5-flash"
        self.base_url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        )
        body = self._request(
            {"Content-Type": "application/json", "x-goog-api-key": self.api_key},
            {
                "contents": [{"parts": [{"text": f"{_system_prompt()}\n{_user_prompt(context)}"}]}],
                "generationConfig": {
                    "temperature": request.temperature,
                    "maxOutputTokens": request.max_tokens,
                },
            },
            request,
        )
        try:
            raw = json.loads(body["candidates"][0]["content"]["parts"][0]["text"])
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise ProviderUnavailableError("Google returned an unusable response.") from error
        return _parse_response(raw, context)

    def test_connection(self) -> ProviderConnectionResult:
        if not self.api_key:
            raise ProviderUnavailableError("google is not configured.")
        with httpx.Client(timeout=15) as client:
            try:
                response = client.get(
                    "https://generativelanguage.googleapis.com/v1beta/models",
                    params={"key": self.api_key},
                )
                response.raise_for_status()
                models = [
                    item["name"].rsplit("/", 1)[-1]
                    for item in response.json().get("models", [])
                    if "generateContent" in item.get("supportedGenerationMethods", [])
                ]
            except httpx.TimeoutException as error:
                raise ProviderUnavailableError("google connection timed out.") from error
            except httpx.HTTPStatusError as error:
                if error.response.status_code == 429:
                    raise ProviderUnavailableError("google rate limit reached.") from error
                raise ProviderUnavailableError("google model listing failed.") from error
            except (httpx.HTTPError, ValueError) as error:
                raise ProviderUnavailableError("google connection failed.") from error
        return ProviderConnectionResult(
            provider=ProviderName.GOOGLE,
            status="connection_successful",
            models=models[:100],
            message="Google credentials and model listing are available.",
        )


class OllamaProvider(HTTPProvider):
    name = "ollama"

    def __init__(self, base_url: str):
        super().__init__("local", f"{base_url.rstrip('/')}/api/chat")

    def improve(self, context: WritingContext, request: ProviderRequest) -> WritingSuggestion:
        body = self._request(
            {"Content-Type": "application/json"},
            {
                "model": request.model or "llama3.2",
                "stream": False,
                "format": "json",
                "options": {"temperature": request.temperature, "num_predict": request.max_tokens},
                "messages": [
                    {"role": "system", "content": _system_prompt()},
                    {"role": "user", "content": _user_prompt(context)},
                ],
            },
            request,
        )
        try:
            raw = json.loads(body["message"]["content"])
        except (KeyError, TypeError, ValueError) as error:
            raise ProviderUnavailableError("Ollama returned an unusable response.") from error
        return _parse_response(raw, context)

    def test_connection(self) -> ProviderConnectionResult:
        try:
            with httpx.Client(timeout=15) as client:
                response = client.get(self.base_url.replace("/api/chat", "/api/tags"), headers={})
                response.raise_for_status()
                models = [item["name"] for item in response.json().get("models", [])]
        except (httpx.HTTPError, ValueError) as error:
            raise ProviderUnavailableError("Ollama is unreachable.") from error
        return ProviderConnectionResult(
            provider=ProviderName.OLLAMA,
            status="connection_successful",
            models=models,
            message="Ollama is reachable and returned its installed models.",
        )
