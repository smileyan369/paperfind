import csv
import io
import logging
from datetime import date
from typing import Sequence

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, case, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import Select

from app.database import get_db
from app.models.keyword import Keyword
from app.models.paper import Paper, paper_keywords
from app.models.summary import Summary
from app.services.summary_queue import get_summary_queue
from app.schemas.paper import (
    PaperDetailResponse,
    PaperFilterParams,
    PaperListResponse,
    PaperResponse,
    PaperStarRequest,
    PaperStatsResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/papers", tags=["papers"])


def _not_future_condition():
    today = date.today()
    return or_(
        Paper.publication_date.is_(None),
        Paper.publication_date <= today,
    )


def _apply_paper_filters(
    query: Select,
    *,
    sci_zone: Sequence[str] | None = None,
    source: Sequence[str] | None = None,
    keyword_id: Sequence[int] | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    citations_min: int | None = None,
    q: str | None = None,
    has_summary: bool | None = None,
    starred: bool | None = None,
) -> Select:
    """Apply paper filter conditions to a query. Reused across list / stats / export."""
    query = query.where(_not_future_condition())
    if sci_zone:
        query = query.where(Paper.sci_zone.in_(sci_zone))
    if source:
        query = query.where(Paper.source.in_(source))
    if keyword_id:
        query = query.where(
            Paper.id.in_(
                select(paper_keywords.c.paper_id).where(paper_keywords.c.keyword_id.in_(keyword_id))
            )
        )
    if date_from:
        query = query.where(
            or_(
                Paper.publication_date >= date_from,
                and_(Paper.publication_date.is_(None), Paper.year >= date_from.year),
            )
        )
    if date_to:
        query = query.where(
            or_(
                Paper.publication_date <= date_to,
                and_(Paper.publication_date.is_(None), Paper.year <= date_to.year),
            )
        )
    if citations_min is not None:
        query = query.where(Paper.citation_count >= citations_min)
    if q:
        like = f"%{q}%"
        query = query.where(
            or_(Paper.title.ilike(like), Paper.abstract.ilike(like))
        )
    if has_summary is True:
        query = query.where(Paper.id.in_(select(Summary.paper_id).where(Summary.status == "completed", Summary.summary_cn.isnot(None))))
    elif has_summary is False:
        query = query.where(Paper.id.notin_(select(Summary.paper_id).where(Summary.status == "completed", Summary.summary_cn.isnot(None))))
    if starred is not None:
        query = query.where(Paper.is_starred == starred)
    return query


async def _fetch_huggingface_daily_papers(limit: int = 6) -> list[dict]:
    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            resp = await client.get(
                "https://huggingface.co/papers",
                headers={"User-Agent": "PaperFind/0.1 (+local research agent)"},
            )
            resp.raise_for_status()
        html = resp.text
    except Exception as e:
        logger.info("Daily digest remote fetch failed: %s", e)
        return []

    import html as html_lib
    import re

    items: list[dict] = []
    seen: set[str] = set()
    pattern = re.compile(r'href="(/papers/[^"]+)".{0,900}?<h3[^>]*>(.*?)</h3>', re.S)
    for href, raw_title in pattern.findall(html):
        title = re.sub(r"<[^>]+>", " ", raw_title)
        title = html_lib.unescape(" ".join(title.split()))
        if not title or title.lower() in seen:
            continue
        seen.add(title.lower())
        items.append({
            "title": title,
            "url": f"https://huggingface.co{href}",
            "source": "Hugging Face Daily Papers",
            "summary": "社区每日论文榜单，适合发现不同领域的新论文。",
        })
        if len(items) >= limit:
            break
    return items


@router.get("/daily-digest")
async def daily_digest(limit: int = Query(6, ge=1, le=12), db: AsyncSession = Depends(get_db)):
    remote = await _fetch_huggingface_daily_papers(limit=limit)
    if remote:
        return {"items": remote, "source": "Hugging Face Daily Papers"}

    result = await db.execute(
        select(Paper)
        .where(_not_future_condition())
        .order_by(Paper.publication_date.desc().nullslast(), Paper.crawled_at.desc())
        .limit(limit)
    )
    items = [
        {
            "id": p.id,
            "title": p.title,
            "url": p.url,
            "source": p.source,
            "date": p.publication_date.isoformat() if p.publication_date else (str(p.year) if p.year else None),
            "summary": p.abstract[:120] if p.abstract else "本地最近检索到的论文。",
        }
        for p in result.scalars().all()
    ]
    return {"items": items, "source": "本地最近论文"}


@router.get("", response_model=PaperListResponse)
async def list_papers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("sci_zone"),
    sort_order: str = Query("asc"),
    sci_zone: list[str] | None = Query(None, alias="sci_zone[]"),
    source: list[str] | None = Query(None, alias="source[]"),
    keyword_id: list[int] | None = Query(None, alias="keyword_id[]"),
    date_from: date | None = None,
    date_to: date | None = None,
    citations_min: int | None = None,
    q: str | None = None,
    has_summary: bool | None = None,
    starred: bool | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Paper)
    count_query = select(func.count(Paper.id))

    filter_kwargs = dict(
        sci_zone=sci_zone, source=source, keyword_id=keyword_id,
        date_from=date_from, date_to=date_to, citations_min=citations_min,
        q=q, has_summary=has_summary, starred=starred,
    )
    query = _apply_paper_filters(query, **filter_kwargs)
    count_query = _apply_paper_filters(count_query, **filter_kwargs)

    # Apply sort
    if sort_by == "sci_zone":
        zone_order = case(
            (Paper.sci_zone == 'Q1', 1),
            (Paper.sci_zone == 'Q2', 2),
            (Paper.sci_zone == 'Q3', 3),
            (Paper.sci_zone == 'Q4', 4),
            else_=5,
        )
        if sort_order == "desc":
            zone_order = case(
                (Paper.sci_zone == 'Q4', 1),
                (Paper.sci_zone == 'Q3', 2),
                (Paper.sci_zone == 'Q2', 3),
                (Paper.sci_zone == 'Q1', 4),
                else_=5,
            )
        query = query.order_by(zone_order, Paper.publication_date.desc().nullslast())
    else:
        sort_col_map = {
            "publication_date": Paper.publication_date,
            "citation_count": Paper.citation_count,
            "title": Paper.title,
            "updated_at": Paper.updated_at,
            "crawled_at": Paper.crawled_at,
        }
        sort_col = sort_col_map.get(sort_by, Paper.publication_date)
        if sort_order == "asc":
            query = query.order_by(sort_col.asc().nullslast() if sort_by == "publication_date" else sort_col.asc())
        else:
            query = query.order_by(sort_col.desc().nullslast() if sort_by == "publication_date" else sort_col.desc())

    # Count
    total = (await db.execute(count_query)).scalar() or 0

    # Paginate — eager-load keywords for keyword_texts
    query = query.options(selectinload(Paper.keywords)).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    papers = result.unique().scalars().all()

    # Enrich with has_summary — only count papers with completed summaries
    summary_paper_ids = set()
    processing_paper_ids = set()
    if papers:
        paper_ids = [p.id for p in papers]
        summary_result = await db.execute(
            select(Summary.paper_id).where(
                Summary.paper_id.in_(paper_ids),
                Summary.status == "completed",
                Summary.summary_cn.isnot(None),
            )
        )
        summary_paper_ids = {r[0] for r in summary_result.all()}
        queue_running = bool(get_summary_queue().stats.get("running"))
        if queue_running:
            proc_result = await db.execute(
                select(Summary.paper_id).where(
                    Summary.paper_id.in_(paper_ids),
                    Summary.status == "processing",
                )
            )
            processing_paper_ids = {r[0] for r in proc_result.all()}

    paper_responses = []
    for p in papers:
        completed = p.id in summary_paper_ids
        processing = p.id in processing_paper_ids
        pr = PaperResponse(
            id=p.id,
            title=p.title,
            authors=p.authors,
            abstract=p.abstract[:300] if p.abstract else None,
            publication_date=p.publication_date.isoformat() if p.publication_date else None,
            source=p.source,
            doi=p.doi,
            arxiv_id=p.arxiv_id,
            url=p.url,
            pdf_url=p.pdf_url,
            journal_name=p.journal_name,
            sci_zone=p.sci_zone,
            citation_count=p.citation_count,
            year=p.year,
            is_starred=p.is_starred,
            has_summary=completed,
            summary_status="completed" if completed else ("processing" if processing else "none"),
            keyword_texts=[kw.text for kw in p.keywords],
            keyword_ids=[kw.id for kw in p.keywords],
            crawled_at=p.crawled_at,
            updated_at=p.updated_at,
        )
        paper_responses.append(pr)

    return PaperListResponse(
        papers=paper_responses,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/stats", response_model=PaperStatsResponse)
async def get_stats(
    sci_zone: list[str] | None = Query(None, alias="sci_zone[]"),
    source: list[str] | None = Query(None, alias="source[]"),
    keyword_id: list[int] | None = Query(None, alias="keyword_id[]"),
    date_from: date | None = None,
    date_to: date | None = None,
    citations_min: int | None = None,
    q: str | None = None,
    has_summary: bool | None = None,
    starred: bool | None = None,
    db: AsyncSession = Depends(get_db),
):
    filter_kwargs = dict(
        sci_zone=sci_zone, source=source, keyword_id=keyword_id,
        date_from=date_from, date_to=date_to, citations_min=citations_min,
        q=q, has_summary=has_summary, starred=starred,
    )

    # Total count (filtered)
    total_query = _apply_paper_filters(select(func.count(Paper.id)), **filter_kwargs)
    total = (await db.execute(total_query)).scalar() or 0

    # With summary count (filtered)
    summary_query = _apply_paper_filters(
        select(func.count(Paper.id)), **filter_kwargs
    ).where(Paper.id.in_(select(Summary.paper_id).where(Summary.status == "completed", Summary.summary_cn.isnot(None))))
    with_summary = (await db.execute(summary_query)).scalar() or 0

    # Zone counts (filtered)
    zone_query = _apply_paper_filters(
        select(Paper.sci_zone, func.count(Paper.id))
        .where(Paper.sci_zone.isnot(None))
        .group_by(Paper.sci_zone),
        **filter_kwargs,
    )
    zone_result = await db.execute(zone_query)
    by_zone = {r[0]: r[1] for r in zone_result.all()}

    # Source counts (filtered)
    source_query = _apply_paper_filters(
        select(Paper.source, func.count(Paper.id)).group_by(Paper.source),
        **filter_kwargs,
    )
    source_result = await db.execute(source_query)
    by_source = {r[0]: r[1] for r in source_result.all()}

    return PaperStatsResponse(
        total=total,
        with_summary=with_summary,
        by_zone=by_zone,
        by_source=by_source,
    )


@router.get("/export")
async def export_papers_csv(
    sci_zone: list[str] | None = Query(None, alias="sci_zone[]"),
    source: list[str] | None = Query(None, alias="source[]"),
    keyword_id: list[int] | None = Query(None, alias="keyword_id[]"),
    date_from: date | None = None,
    date_to: date | None = None,
    citations_min: int | None = None,
    q: str | None = None,
    has_summary: bool | None = None,
    starred: bool | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = _apply_paper_filters(
        select(Paper),
        sci_zone=sci_zone, source=source, keyword_id=keyword_id,
        date_from=date_from, date_to=date_to, citations_min=citations_min,
        q=q, has_summary=has_summary, starred=starred,
    )

    query = query.order_by(Paper.publication_date.desc().nullslast()).limit(5000)
    result = await db.execute(query)
    papers = result.scalars().all()

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        "title", "authors", "abstract", "publication_date", "source",
        "doi", "arxiv_id", "url", "journal_name", "sci_zone",
        "citation_count", "year", "is_starred",
    ])
    writer.writeheader()
    for p in papers:
        writer.writerow({
            "title": p.title,
            "authors": p.authors,
            "abstract": p.abstract or "",
            "publication_date": p.publication_date.isoformat() if p.publication_date else "",
            "source": p.source,
            "doi": p.doi or "",
            "arxiv_id": p.arxiv_id or "",
            "url": p.url or "",
            "journal_name": p.journal_name or "",
            "sci_zone": p.sci_zone or "",
            "citation_count": p.citation_count,
            "year": p.year or "",
            "is_starred": p.is_starred,
        })

    filename = f"papers_export_{date.today().isoformat()}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/{paper_id}", response_model=PaperDetailResponse)
async def get_paper(paper_id: int, db: AsyncSession = Depends(get_db)):
    paper = await db.get(Paper, paper_id, options=[selectinload(Paper.keywords)])
    if not paper:
        raise HTTPException(status_code=404, detail="论文不存在")

    summary_result = await db.execute(
        select(Summary).where(Summary.paper_id == paper_id)
    )
    summary = summary_result.scalar_one_or_none()

    completed = summary is not None and summary.status == "completed" and bool(summary.summary_cn)
    processing = summary is not None and summary.status == "processing" and bool(get_summary_queue().stats.get("running"))
    return PaperDetailResponse(
        id=paper.id,
        title=paper.title,
        authors=paper.authors,
        abstract=paper.abstract,
        publication_date=paper.publication_date.isoformat() if paper.publication_date else None,
        source=paper.source,
        doi=paper.doi,
        arxiv_id=paper.arxiv_id,
        url=paper.url,
        pdf_url=paper.pdf_url,
        journal_name=paper.journal_name,
        sci_zone=paper.sci_zone,
        citation_count=paper.citation_count,
        year=paper.year,
        is_starred=paper.is_starred,
        has_summary=completed,
        summary_status="completed" if completed else ("processing" if processing else "none"),
        keyword_texts=[kw.text for kw in paper.keywords],
        keyword_ids=[kw.id for kw in paper.keywords],
        crawled_at=paper.crawled_at,
        updated_at=paper.updated_at,
        summary_cn=summary.summary_cn if completed else None,
        key_points_cn=summary.key_points_cn if completed else None,
        model_used=summary.model_used if summary else None,
        summary_generated_at=summary.generated_at if summary else None,
        source_type=summary.source_type if summary else None,
        source_chars=summary.source_chars if summary else 0,
    )


@router.patch("/{paper_id}/star", response_model=PaperResponse)
async def toggle_star(paper_id: int, data: PaperStarRequest, db: AsyncSession = Depends(get_db)):
    paper = await db.get(Paper, paper_id, options=[selectinload(Paper.keywords)])
    if not paper:
        raise HTTPException(status_code=404, detail="论文不存在")
    paper.is_starred = data.starred
    await db.commit()
    await db.refresh(paper)

    summary_result = await db.execute(select(Summary).where(Summary.paper_id == paper_id))
    summary = summary_result.scalar_one_or_none()

    completed = summary is not None and summary.status == "completed" and bool(summary.summary_cn)
    processing = summary is not None and summary.status == "processing" and bool(get_summary_queue().stats.get("running"))
    return PaperResponse(
        id=paper.id,
        title=paper.title,
        authors=paper.authors,
        abstract=paper.abstract[:300] if paper.abstract else None,
        publication_date=paper.publication_date.isoformat() if paper.publication_date else None,
        source=paper.source,
        doi=paper.doi,
        arxiv_id=paper.arxiv_id,
        url=paper.url,
        pdf_url=paper.pdf_url,
        journal_name=paper.journal_name,
        sci_zone=paper.sci_zone,
        citation_count=paper.citation_count,
        year=paper.year,
        is_starred=paper.is_starred,
        has_summary=completed,
        summary_status="completed" if completed else ("processing" if processing else "none"),
        keyword_texts=[kw.text for kw in paper.keywords],
        keyword_ids=[kw.id for kw in paper.keywords],
        crawled_at=paper.crawled_at,
        updated_at=paper.updated_at,
    )


@router.delete("/{paper_id}")
async def delete_paper(paper_id: int, db: AsyncSession = Depends(get_db)):
    paper = await db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="论文不存在")
    await db.delete(paper)
    await db.commit()
    return {"ok": True}
