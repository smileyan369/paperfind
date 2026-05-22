import datetime

from pydantic import BaseModel, Field

from app.schemas.common import PaginatedResponse


class PaperFilterParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: str = Field(default="publication_date")
    sort_order: str = Field(default="desc")
    sci_zone: list[str] | None = Field(default=None, alias="sci_zone[]")
    source: list[str] | None = Field(default=None, alias="source[]")
    keyword_id: list[int] | None = Field(default=None, alias="keyword_id[]")
    date_from: str | None = None
    date_to: str | None = None
    citations_min: int | None = None
    q: str | None = None
    has_summary: bool | None = None
    starred: bool | None = None

    model_config = {"extra": "allow"}


class PaperResponse(BaseModel):
    id: int
    title: str
    authors: str
    abstract: str | None
    publication_date: str | None
    source: str
    doi: str | None
    arxiv_id: str | None
    url: str | None
    pdf_url: str | None
    journal_name: str | None
    sci_zone: str | None
    citation_count: int
    year: int | None
    is_starred: bool
    has_summary: bool = False
    summary_status: str = "none"  # "completed" | "processing" | "none"
    keyword_texts: list[str] = []
    keyword_ids: list[int] = []
    crawled_at: datetime.datetime | None = None
    updated_at: datetime.datetime | None = None

    model_config = {"from_attributes": True}


class PaperListResponse(PaginatedResponse):
    papers: list[PaperResponse]


class PaperDetailResponse(PaperResponse):
    model_config = {"from_attributes": True, "protected_namespaces": ()}

    summary_cn: str | None = None
    key_points_cn: str | None = None
    model_used: str | None = None
    summary_generated_at: datetime.datetime | None = None
    source_type: str | None = None
    source_chars: int = 0


class PaperStarRequest(BaseModel):
    starred: bool


class PaperStatsResponse(BaseModel):
    total: int
    with_summary: int
    by_zone: dict[str, int]
    by_source: dict[str, int]
