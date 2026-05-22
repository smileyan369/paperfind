from enum import Enum

from pydantic import BaseModel, Field


class SortOrder(str, Enum):
    asc = "asc"
    desc = "desc"


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class PaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
