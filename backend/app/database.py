from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def init_db():
    async with engine.begin() as conn:
        await conn.execute(text("PRAGMA journal_mode=WAL"))
        await conn.execute(text("PRAGMA synchronous=NORMAL"))
        await conn.execute(text("PRAGMA busy_timeout=5000"))
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_papers_doi ON papers(doi)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_papers_arxiv_id ON papers(arxiv_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_papers_publication_date ON papers(publication_date)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_paper_keywords_keyword ON paper_keywords(keyword_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_summaries_paper_status ON summaries(paper_id, status)"))
