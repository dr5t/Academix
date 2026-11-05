from academic_api.main import app
from docx import Document
from fastapi.testclient import TestClient


def test_health_endpoint() -> None:
    response = TestClient(app).get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_configuration_does_not_expose_credentials() -> None:
    response = TestClient(app).get("/api/v1/configuration")
    assert response.status_code == 200
    assert "api_key" not in response.text.lower()


def test_document_upload_analysis_and_delete(tmp_path) -> None:
    source = tmp_path / "api-paper.docx"
    document = Document()
    document.add_heading("API Paper", level=1)
    document.add_paragraph("A paragraph for structural analysis.")
    document.save(source)
    with TestClient(app) as client:
        with source.open("rb") as stream:
            response = client.post(
                "/api/v1/documents",
                files={
                    "file": (
                        source.name,
                        stream,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
                },
            )
        assert response.status_code == 201
        document_id = response.json()["id"]
        analysis = client.get(f"/api/v1/documents/{document_id}/analysis")
        assert analysis.status_code == 200
        assert analysis.json()["paragraph_count"] == 2
        assert client.delete(f"/api/v1/documents/{document_id}").status_code == 204


def test_integrity_review_and_finding_review(tmp_path) -> None:
    source = tmp_path / "integrity-paper.docx"
    document = Document()
    document.add_heading("Integrity Paper", level=1)
    document.add_paragraph("The study demonstrates a result without a citation.")
    document.save(source)
    with TestClient(app) as client:
        with source.open("rb") as stream:
            response = client.post(
                "/api/v1/documents",
                files={
                    "file": (
                        source.name,
                        stream,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
                },
            )
        document_id = response.json()["id"]
        report = client.post(
            f"/api/v1/documents/{document_id}/integrity",
            json={"verify_metadata": False},
        )
        assert report.status_code == 200
        assert report.json()["findings"]
        finding = report.json()["findings"][0]
        reviewed = client.post(
            f"/api/v1/documents/{document_id}/integrity/findings/{finding['id']}/review",
            json={"status": "reviewed"},
        )
        assert reviewed.status_code == 200
        assert reviewed.json()["status"] == "reviewed"
        assert client.delete(f"/api/v1/documents/{document_id}").status_code == 204
