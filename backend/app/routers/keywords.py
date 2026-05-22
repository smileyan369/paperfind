from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.keyword import Keyword
from app.models.paper import Paper, paper_keywords
from app.models.summary import Summary
from app.rate_limit import limiter
from app.schemas.keyword import (
    KeywordCreate,
    KeywordImportRequest,
    KeywordResponse,
    KeywordUpdate,
)

router = APIRouter(prefix="/api/keywords", tags=["keywords"])


@router.get("", response_model=list[KeywordResponse])
async def list_keywords(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Keyword).order_by(Keyword.created_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=KeywordResponse, status_code=201)
@limiter.limit("30/minute")
async def create_keyword(
    request: Request,
    data: KeywordCreate,
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(Keyword).where(Keyword.text == data.text)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="关键词已存在")
    kw = Keyword(
        text=data.text,
        source=data.source,
        is_active=data.is_active,
    )
    db.add(kw)
    await db.commit()
    await db.refresh(kw)
    return kw


@router.put("/{keyword_id}", response_model=KeywordResponse)
async def update_keyword(
    keyword_id: int,
    data: KeywordUpdate,
    db: AsyncSession = Depends(get_db),
):
    kw = await db.get(Keyword, keyword_id)
    if not kw:
        raise HTTPException(status_code=404, detail="关键词不存在")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(kw, key, value)
    await db.commit()
    await db.refresh(kw)
    return kw


@router.delete("/{keyword_id}")
async def delete_keyword(keyword_id: int, db: AsyncSession = Depends(get_db)):
    kw = await db.get(Keyword, keyword_id)
    if not kw:
        raise HTTPException(status_code=404, detail="关键词不存在")

    await db.delete(kw)
    await db.flush()

    result = await db.execute(
        select(Paper.id).where(
            Paper.id.notin_(select(paper_keywords.c.paper_id).distinct())
        )
    )
    orphan_ids = [r[0] for r in result.all()]

    if orphan_ids:
        await db.execute(delete(Summary).where(Summary.paper_id.in_(orphan_ids)))
        await db.execute(delete(Paper).where(Paper.id.in_(orphan_ids)))

    await db.commit()
    return {"ok": True, "deleted_papers": len(orphan_ids)}


@router.post("/import", response_model=dict)
@limiter.limit("5/minute")
async def import_keywords(
    request: Request,
    data: KeywordImportRequest,
    db: AsyncSession = Depends(get_db),
):
    lines = [line.strip() for line in data.keywords.split("\n") if line.strip()]
    added = 0
    skipped = 0
    for line in lines:
        existing = await db.execute(
            select(Keyword).where(Keyword.text == line)
        )
        if existing.scalar_one_or_none():
            skipped += 1
            continue
        db.add(Keyword(text=line, source=data.source))
        added += 1
    await db.commit()
    return {"added": added, "skipped": skipped}
