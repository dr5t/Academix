from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from academic_engine.citation_intelligence import analyze_citations
from academic_engine.document_parser import parse_document
from academic_engine.document_service import DocumentService
from academic_engine.exceptions import DocumentNotFoundError, ProviderUnavailableError
from academic_engine.integrity_models import (
    FindingStatus,
    IntegrityFinding,
    IntegrityReport,
    IntegrityRequest,
)
from academic_engine.metadata_providers import CrossrefProvider, OpenAlexProvider
from academic_engine.similarity import compare_documents, find_internal_repetition
from academic_engine.storage import SQLiteStore


class IntegrityService:
    def __init__(self, store: SQLiteStore, documents: DocumentService):
        self.store = store
        self.documents = documents

    def analyze(self, document_id: str, request: IntegrityRequest) -> IntegrityReport:
        detail = self.documents.get_document(document_id)
        document = parse_document(self.documents._path_for(detail))
        citation_analysis = analyze_citations(document, request.style)
        findings = self._citation_findings(document_id, citation_analysis)
        findings.extend(self._content_findings(document_id, document))
        internal = find_internal_repetition(document)
        findings.extend(
            self._similarity_findings(document_id, match.target_element_id, match.matching_text)
            for match in internal
        )
        sources = []
        for source_id in request.source_document_ids:
            source_detail = self.documents.get_document(source_id)
            sources.append((source_id, parse_document(self.documents._path_for(source_detail))))
        external = compare_documents(document, sources)
        findings.extend(
            self._similarity_findings(document_id, match.target_element_id, match.matching_text)
            for match in external
        )
        metadata = self._verify_references(citation_analysis, request.verify_metadata)
        limitations = [
            "This review identifies evidence for human review; it does not determine plagiarism.",
            "External similarity is limited to explicitly supplied local comparison documents.",
        ]
        report = IntegrityReport(
            document_id=document_id,
            analyzed_at=datetime.now(timezone.utc),
            citation_analysis=citation_analysis,
            findings=findings,
            internal_similarity=internal,
            external_matches=external,
            metadata_verifications=metadata,
            limitations=limitations,
        )
        self.store.update_integrity(document_id, report)
        for finding in findings:
            self.store.create_integrity_finding(finding)
        return report

    def report(self, document_id: str) -> IntegrityReport | None:
        self.documents.get_document(document_id)
        return self.store.get_integrity(document_id)

    def findings(self, document_id: str) -> list[IntegrityFinding]:
        self.documents.get_document(document_id)
        return self.store.list_integrity_findings(document_id)

    def review_finding(
        self,
        document_id: str,
        finding_id: str,
        status: FindingStatus,
        dismissal_reason: str | None = None,
    ) -> IntegrityFinding:
        self.documents.get_document(document_id)
        finding = self.store.get_integrity_finding(finding_id)
        if finding is None or finding.document_id != document_id:
            raise DocumentNotFoundError("Integrity finding was not found.")
        if status is FindingStatus.DISMISSED and not dismissal_reason:
            raise ValueError("A dismissal reason is required.")
        updated = self.store.update_integrity_finding(finding_id, status, dismissal_reason)
        if updated is None:
            raise DocumentNotFoundError("Integrity finding was not found.")
        return updated

    @staticmethod
    def _citation_findings(document_id, analysis):
        findings = []
        for reference in analysis.missing_references:
            findings.append(
                IntegrityFinding(
                    id=str(uuid4()),
                    document_id=document_id,
                    category="missing_reference",
                    severity="medium",
                    explanation=f"The in-text citation '{reference}' has no matching bibliography entry.",
                    confidence=0.92,
                    recommended_action="Add or correct the bibliography entry after verifying the original source.",
                    evidence=[reference],
                    created_at=datetime.now(timezone.utc),
                )
            )
        for raw in analysis.unreferenced_entries:
            findings.append(
                IntegrityFinding(
                    id=str(uuid4()),
                    document_id=document_id,
                    category="unreferenced_bibliography",
                    severity="low",
                    explanation="This bibliography entry was not matched to an in-text citation.",
                    confidence=0.86,
                    recommended_action="Confirm whether the entry is background reading or should be cited.",
                    evidence=[raw],
                    created_at=datetime.now(timezone.utc),
                )
            )
        for warning in analysis.consistency_warnings:
            findings.append(
                IntegrityFinding(
                    id=str(uuid4()),
                    document_id=document_id,
                    category="citation_consistency",
                    severity="low",
                    explanation=warning,
                    confidence=0.78,
                    recommended_action="Review the document against its required citation style.",
                    created_at=datetime.now(timezone.utc),
                )
            )
        return findings

    @staticmethod
    def _content_findings(document_id, document):
        findings = []
        for element in document.elements:
            text = element.original_content.strip()
            if not text or element.element_type.value not in {"paragraph", "heading"}:
                continue
            if text.startswith('"') or text.startswith("“"):
                if not any(marker in text for marker in ("(", "[", "doi.org")):
                    findings.append(
                        IntegrityFinding(
                            id=str(uuid4()),
                            document_id=document_id,
                            element_id=element.id,
                            category="unattributed_quote",
                            severity="high",
                            explanation="A direct quotation marker was detected without an apparent attribution.",
                            confidence=0.76,
                            recommended_action="Verify the quotation and add a page-level citation or attribution.",
                            evidence=[text[:240]],
                            created_at=datetime.now(timezone.utc),
                        )
                    )
            if any(
                marker in text.lower()
                for marker in (" demonstrates ", " was found ", " significantly ")
            ):
                if not any(marker in text for marker in ("(", "[", "doi.org")):
                    findings.append(
                        IntegrityFinding(
                            id=str(uuid4()),
                            document_id=document_id,
                            element_id=element.id,
                            category="potentially_unsupported_claim",
                            severity="medium",
                            explanation="This sentence uses a factual or research-result construction without a detected citation.",
                            confidence=0.58,
                            recommended_action="Author should verify the claim and add a supporting source if required.",
                            evidence=[text[:240]],
                            created_at=datetime.now(timezone.utc),
                        )
                    )
        return findings

    @staticmethod
    def _similarity_findings(document_id, element_id, matching_text):
        return IntegrityFinding(
            id=str(uuid4()),
            document_id=document_id,
            element_id=element_id,
            category="similarity",
            severity="medium",
            explanation="A passage overlaps substantially with another comparison passage.",
            confidence=0.84,
            recommended_action="Review attribution and confirm that the wording is appropriately quoted or paraphrased.",
            evidence=[matching_text[:240]],
            created_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def _verify_references(analysis, enabled):
        if not enabled:
            return []
        results = []
        for reference in analysis.references[:20]:
            query = reference.title or reference.raw_text
            if not query:
                continue
            for provider in (CrossrefProvider(), OpenAlexProvider()):
                try:
                    results.append(provider.verify(query))
                    break
                except ProviderUnavailableError:
                    continue
        return results
