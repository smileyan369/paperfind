import datetime

from pydantic import BaseModel, Field


class KeywordCreate(BaseModel):
    text: str = Field(..., min_length=1, max_length=255)
    source: str = Field(default="all")
    is_active: bool = Field(default=True)


class KeywordUpdate(BaseModel):
    text: str | None = Field(default=None, min_length=1, max_length=255)
    source: str | None = None
    is_active: bool | None = None


class KeywordResponse(BaseModel):
    id: int
    text: str
    source: str
    is_active: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}


class KeywordImportRequest(BaseModel):
    keywords: str = Field(..., description="Newline-separated keywords")
    source: str = Field(default="all")
