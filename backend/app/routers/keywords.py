import json
import re

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.keyword import Keyword
from app.models.paper import Paper, paper_keywords
from app.models.summary import Summary
from app.rate_limit import limiter
from app.routers.config import get_effective_config
from app.schemas.keyword import (
    KeywordCreate,
    KeywordImportRequest,
    KeywordResponse,
    KeywordSuggestRequest,
    KeywordSuggestResponse,
    KeywordUpdate,
)

router = APIRouter(prefix="/api/keywords", tags=["keywords"])


def _fallback_suggestions(query: str, limit: int) -> list[str]:
    text = query.strip()
    terms: list[str] = []
    hint_map = {
        "人体行为": ["human behavior prediction", "human activity recognition"],
        "人体运动": ["human motion prediction", "long-term human motion prediction"],
        "行为预测": ["human behavior prediction", "trajectory prediction"],
        "动作预测": ["action prediction", "motion forecasting"],
        "运动预测": ["human motion prediction", "motion forecasting"],
        "网络安全": ["cybersecurity", "network security", "intrusion detection"],
        "大模型": ["large language models", "foundation models"],
        "多模态": ["multimodal learning", "multimodal large language models"],
        "医学影像": ["medical imaging", "radiology report generation"],
        "报告生成": ["report generation", "medical report generation"],
        "可解释": ["explainable AI", "interpretability"],
        "临床": ["clinical decision support", "clinical AI"],
        "强化学习": ["reinforcement learning"],
        "扩散": ["diffusion models"],
        "图神经网络": ["graph neural networks"],
        "综述": ["survey", "review"],
        "前沿": ["state of the art", "recent advances"],
        "最新": ["recent advances", "state of the art"],
    }

    def add(item: str) -> None:
        cleaned = re.sub(r"\s+", " ", item).strip(" ,.;:，。；：")
        known = {term.lower() for term in terms}
        if 2 <= len(cleaned) <= 80 and cleaned.lower() not in known:
            terms.append(cleaned)

    for key, mapped_terms in hint_map.items():
        if key in text:
            for item in mapped_terms:
                add(item)

    for item in re.findall(r"[A-Za-z][A-Za-z0-9+\-/ ]{2,}", text):
        add(item)
    for item in re.findall(r"[\u4e00-\u9fff]{2,}", text):
        add(item)

    add(text[:80])
    return terms[:limit]


@router.get("", response_model=list[KeywordResponse])
async def list_keywords(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Keyword).order_by(Keyword.created_at.desc()))
    return result.scalars().all()


@router.post("", response_model=KeywordResponse, status_code=201)
@limiter.limit("30/minute")
async def create_keyword(
    request: Request,
    data: KeywordCreate,
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(select(Keyword).where(Keyword.text == data.text))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="关键词已存在")
    kw = Keyword(text=data.text, source=data.source, is_active=data.is_active)
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
    orphan_ids = [row[0] for row in result.all()]

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
        existing = await db.execute(select(Keyword).where(Keyword.text == line))
        if existing.scalar_one_or_none():
            skipped += 1
            continue
        db.add(Keyword(text=line, source=data.source))
        added += 1
    await db.commit()
    return {"added": added, "skipped": skipped}


@router.post("/suggest", response_model=KeywordSuggestResponse)
@limiter.limit("10/minute")
async def suggest_keywords(request: Request, data: KeywordSuggestRequest):
    cfg = await get_effective_config()
    api_key = str(cfg.get("llm_api_key") or "")
    if api_key:
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(
                api_key=api_key,
                base_url=str(cfg.get("llm_base_url") or ""),
            )
            prompt = (
                "把用户的自然语言科研需求转成适合论文数据库检索的关键词。"
                "要求：只输出 JSON 字符串数组；中英文都给；每个词 2-8 个单词；"
                "不要解释，不要 Markdown。\n"
                f"用户需求：{data.query}"
            )
            response = await client.chat.completions.create(
                model=str(cfg.get("llm_model") or ""),
                max_tokens=400,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.choices[0].message.content or "[]"
            parsed = json.loads(raw[raw.find("["): raw.rfind("]") + 1])
            suggestions: list[str] = []
            for item in parsed:
                text = str(item).strip()
                known = {suggestion.lower() for suggestion in suggestions}
                if text and text.lower() not in known:
                    suggestions.append(text[:80])
            if suggestions:
                return KeywordSuggestResponse(
                    suggestions=suggestions[: data.limit],
                    source="ai",
                )
        except Exception:
            pass

    return KeywordSuggestResponse(
        suggestions=_fallback_suggestions(data.query, data.limit),
        source="local",
    )
