from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class PolicyEvidence:
    chunk_id: str
    text: str
    document: str
    document_id: str
    source: str
    source_type: str
    source_url: str

    policy_id: str | None
    policy_version_id: str | None
    version_number: str | None

    chapter: str | None
    section: str | None
    page: int | None

    distance: float

    # Applicability / policy context
    institution: str | None = None
    jurisdiction: str | None = None
    loan_type: str | None = None
    department: str | None = None

    # Policy provenance / lifecycle
    effective_from: str | None = None
    effective_to: str | None = None
    file_hash: str | None = None

    def validate(self):
        for name in (
            "chunk_id",
            "text",
            "document",
            "document_id",
            "source",
            "source_type",
            "source_url",
        ):
            value = getattr(self, name)

            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"{name} must be a non-empty string"
                )

        for name in (
            "policy_id",
            "policy_version_id",
            "version_number",
            "institution",
            "jurisdiction",
            "loan_type",
            "department",
            "effective_from",
            "effective_to",
            "file_hash",
        ):
            value = getattr(self, name)

            if value is not None and not isinstance(value, str):
                raise ValueError(
                    f"{name} must be a string or None"
                )

            # Empty strings are allowed for optional provenance fields.
            # In particular, an active policy may have no effective_to date.

        if self.page is not None and (
            not isinstance(self.page, int)
            or isinstance(self.page, bool)
            or self.page < 1
        ):
            raise ValueError(
                "page must be a positive integer or None"
            )

        if (
            not isinstance(self.distance, (int, float))
            or isinstance(self.distance, bool)
            or self.distance < 0
        ):
            raise ValueError(
                "distance must be a non-negative number"
            )

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass
class EvidenceContract:
    query: str
    final_query: str
    evidence_status: str
    attempts: int
    evidence: list[PolicyEvidence]
    trace: dict[str, Any]

    VALID_STATUSES = {"sufficient", "insufficient"}

    def validate(self):
        if not isinstance(self.query, str) or not self.query.strip():
            raise ValueError("query must be non-empty")

        if self.evidence_status not in self.VALID_STATUSES:
            raise ValueError("invalid evidence_status")

        if self.attempts not in {1, 2}:
            raise ValueError("attempts must be 1 or 2")

        for item in self.evidence:
            item.validate()

        if self.evidence_status == "insufficient" and self.evidence:
            raise ValueError(
                "insufficient evidence must not expose items"
            )

    def to_dict(self):
        self.validate()

        return {
            "query": self.query,
            "final_query": self.final_query,
            "evidence_status": self.evidence_status,
            "attempts": self.attempts,
            "evidence": [x.to_dict() for x in self.evidence],
            "trace": self.trace,
        }