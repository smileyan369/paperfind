import datetime

from pydantic import BaseModel, Field

from app.schemas.common import PaginatedResponse


class JournalCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
    issn: str | None = Field(default=None, min_length=8, max_length=9)
    sci_zone: str = Field(..., pattern=r"^Q[1-4]$")
    category: str | None = Field(default=None, max_length=255)
    year: int = Field(default=2024)


class JournalResponse(BaseModel):
    id: int
    name: str
    issn: str | None
    sci_zone: str
    category: str | None
    year: int
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}


class JournalListResponse(PaginatedResponse):
    journals: list[JournalResponse]


class JournalImportResponse(BaseModel):
    added: int
    updated: int
    errors: list[str] = []
