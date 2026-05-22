import datetime

from pydantic import BaseModel, Field


class SummaryResponse(BaseModel):
    model_config = {"from_attributes": True, "protected_namespaces": ()}

    id: int
    paper_id: int
    summary_cn: str | None
    key_points_cn: str | None
    model_used: str | None
    tokens_used: int
    status: str = "completed"
    generated_at: datetime.datetime | None
    error_message: str | None
    source_type: str | None = None
    source_chars: int = 0


class BatchSummaryRequest(BaseModel):
    limit: int = Field(default=10, ge=1, le=50)


class BatchSummaryResponse(BaseModel):
    success: int
    failed: int
    errors: list[dict] = []


class SummaryStatsResponse(BaseModel):
    total_summaries: int
    pending_count: int
    failed_count: int
