import csv
import io
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.journal import Journal
from app.rate_limit import limiter
from app.schemas.journal import (
    JournalCreate,
    JournalImportResponse,
    JournalListResponse,
    JournalResponse,
)
from app.services.sci_lookup import bulk_resolve

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/journals", tags=["journals"])


@router.get("", response_model=JournalListResponse)
async def list_journals(
    page: int = 1,
    page_size: int = 50,
    q: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Journal)
    count_query = select(func.count(Journal.id))

    if q:
        query = query.where(Journal.name.ilike(f"%{q}%"))
        count_query = count_query.where(Journal.name.ilike(f"%{q}%"))

    total = (await db.execute(count_query)).scalar() or 0

    result = await db.execute(
        query.order_by(Journal.sci_zone, Journal.name).offset((page - 1) * page_size).limit(page_size)
    )
    journals = result.scalars().all()

    return JournalListResponse(
        journals=[JournalResponse.model_validate(j) for j in journals],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=JournalResponse, status_code=201)
@limiter.limit("30/minute")
async def create_journal(request: Request, data: JournalCreate, db: AsyncSession = Depends(get_db)):
    if data.issn:
        existing = await db.execute(select(Journal).where(Journal.issn == data.issn))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="该 ISSN 已存在")

    j = Journal(
        name=data.name,
        issn=data.issn,
        sci_zone=data.sci_zone,
        category=data.category,
        year=data.year,
    )
    db.add(j)
    await db.commit()
    await db.refresh(j)
    return j


@router.post("/import", response_model=JournalImportResponse)
@limiter.limit("5/minute")
async def import_journals(request: Request, file: UploadFile, db: AsyncSession = Depends(get_db)):
    added = 0
    updated = 0
    errors: list[str] = []

    try:
        content = await file.read()
        reader = csv.DictReader(io.StringIO(content.decode("utf-8")))
        for i, row in enumerate(reader, start=1):
            try:
                name = row.get("name", "").strip()
                issn = row.get("issn", "").strip() or None
                sci_zone = row.get("sci_zone", "").strip()
                if not name or sci_zone not in ("Q1", "Q2", "Q3", "Q4"):
                    errors.append(f"Row {i}: invalid data")
                    continue

                if issn:
                    existing = await db.execute(select(Journal).where(Journal.issn == issn))
                    existing = existing.scalar_one_or_none()
                    if existing:
                        existing.sci_zone = sci_zone
                        existing.name = name
                        updated += 1
                        continue

                j = Journal(
                    name=name,
                    issn=issn,
                    sci_zone=sci_zone,
                    category=row.get("category", "").strip() or None,
                    year=int(row.get("year", 2024)),
                )
                db.add(j)
                added += 1
            except Exception as e:
                errors.append(f"Row {i}: {e}")

        await db.commit()

        # Resolve SCI zones for papers that now have matching journals
        from app.models.paper import Paper

        papers = await db.execute(select(Paper.id).where(Paper.sci_zone.is_(None)))
        paper_ids = [r[0] for r in papers.all()]
        if paper_ids:
            await bulk_resolve(paper_ids)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return JournalImportResponse(added=added, updated=updated, errors=errors)


@router.get("/export")
async def export_journals(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Journal).order_by(Journal.sci_zone, Journal.name))
    journals = result.scalars().all()

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["name", "issn", "sci_zone", "category", "year"])
    writer.writeheader()
    for j in journals:
        writer.writerow({
            "name": j.name,
            "issn": j.issn or "",
            "sci_zone": j.sci_zone,
            "category": j.category or "",
            "year": j.year,
        })

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=journals.csv"},
    )


@router.delete("/{journal_id}")
async def delete_journal(journal_id: int, db: AsyncSession = Depends(get_db)):
    j = await db.get(Journal, journal_id)
    if not j:
        raise HTTPException(status_code=404, detail="期刊不存在")
    await db.delete(j)
    await db.commit()
    return {"ok": True}
