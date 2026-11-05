from collections.abc import Sequence

from academic_engine.config import Settings
from academic_engine.models import ProviderMetadata, ProviderName


def provider_metadata(settings: Settings) -> Sequence[ProviderMetadata]:
    configured = {
        ProviderName.OPENAI: bool(settings.openai_api_key),
        ProviderName.ANTHROPIC: bool(settings.anthropic_api_key),
        ProviderName.GOOGLE: bool(settings.google_api_key),
        ProviderName.OLLAMA: bool(settings.ollama_base_url),
    }
    return [
        ProviderMetadata(provider=provider, configured=is_configured)
        for provider, is_configured in configured.items()
    ]
