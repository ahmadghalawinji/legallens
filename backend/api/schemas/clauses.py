from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class ClauseType(StrEnum):
    LIABILITY = "liability"
    INDEMNIFICATION = "indemnification"
    IP_ASSIGNMENT = "ip_assignment"
    CONFIDENTIALITY = "confidentiality"
    TERMINATION = "termination"
    PAYMENT_TERMS = "payment_terms"
    NON_COMPETE = "non_compete"
    GOVERNING_LAW = "governing_law"
    DISPUTE_RESOLUTION = "dispute_resolution"
    AUTO_RENEWAL = "auto_renewal"
    DATA_PROTECTION = "data_protection"
    FORCE_MAJEURE = "force_majeure"
    OTHER = "other"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ExtractedClause(BaseModel):
    id: str
    clause_type: ClauseType
    text: str = Field(description="Exact clause text from the contract")
    confidence: float = Field(ge=0, le=1)
    page_number: int | None = None

    @field_validator("clause_type", mode="before")
    @classmethod
    def coerce_clause_type(cls, v: object) -> str:
        try:
            ClauseType(str(v))
            return str(v)
        except ValueError:
            return ClauseType.OTHER


class ClassifiedClause(ExtractedClause):
    risk_level: RiskLevel
    risk_score: float = Field(ge=0, le=1)
    risk_explanation: str
    reasoning: str = Field(description="Chain-of-thought reasoning")


class ExtractionResult(BaseModel):
    clauses: list[ExtractedClause]


class ClassificationResult(BaseModel):
    clauses: list[ClassifiedClause]
