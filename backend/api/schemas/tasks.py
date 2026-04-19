from enum import StrEnum

from pydantic import BaseModel

from backend.api.schemas.clauses import ClassifiedClause


class TaskStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisResult(BaseModel):
    filename: str
    clauses: list[ClassifiedClause]
    overall_risk_score: float
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    processing_time_seconds: float


class TaskResponse(BaseModel):
    task_id: str
    status: TaskStatus
    progress: int = 0  # 0–100
    result: AnalysisResult | None = None
    error: str | None = None
