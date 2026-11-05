from academic_engine.config import get_settings
from academic_engine.models import ProviderMetadata
from academic_engine.providers import provider_metadata
from fastapi import APIRouter

router = APIRouter()


@router.get("/providers", response_model=list[ProviderMetadata], tags=["providers"])
def providers() -> list[ProviderMetadata]:
    return list(provider_metadata(get_settings()))
