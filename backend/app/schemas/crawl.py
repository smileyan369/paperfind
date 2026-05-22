import datetime

from pydantic import BaseModel, Field

from app.schemas.common import PaginatedResponse


class CrawlTriggerRequest(BaseModel):
    source: str = Field(default="all")
    keyword_ids: list[int] | None = None


class UnreachableSource(BaseModel):
    source: str
    reason: str


class CrawlTriggerResponse(BaseModel):
    crawl_log_id: int
    message: str
    unreachable_sources: list[UnreachableSource] = []


class CrawlLogResponse(BaseModel):
    id: int
    started_at: datetime.datetime
    finished_at: datetime.datetime | None
    status: str
    source: str
    papers_found: int
    papers_new: int
    papers_updated: int
    error_message: str | None
    trigger_type: str

    model_config = {"from_attributes": True}


class CrawlLogListResponse(PaginatedResponse):
    logs: list[CrawlLogResponse]


class ScheduleStatusResponse(BaseModel):
    next_run: datetime.datetime | None
    last_run: datetime.datetime | None
    job_id: str | None


class ScheduleUpdateRequest(BaseModel):
    hour: int = Field(default=8, ge=0, le=23)
    minute: int = Field(default=0, ge=0, le=59)
