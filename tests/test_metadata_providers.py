from academic_engine.metadata_providers import CrossrefProvider


class Response:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "message": {
                "items": [
                    {
                        "DOI": "10.1000/example",
                        "title": ["A verified title"],
                        "author": [{"family": "Doe"}],
                        "published": {"date-parts": [[2024]]},
                    }
                ]
            }
        }


def test_crossref_metadata_is_structured(monkeypatch) -> None:
    monkeypatch.setattr(
        "academic_engine.metadata_providers.httpx.get", lambda *args, **kwargs: Response()
    )
    verification = CrossrefProvider().verify("A verified title")
    assert verification.provider == "crossref"
    assert verification.persistent_identifier == "10.1000/example"
    assert verification.verification_status == "verified_metadata"
