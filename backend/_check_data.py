import asyncio, sys
sys.path.insert(0, '.')
from app.database import async_session
from app.models.paper import Paper
from sqlalchemy import select

async def check():
    async with async_session() as db:
        # Check for bad years (> 2030 or < 1900)
        bad_year = (await db.execute(
            select(Paper.id, Paper.title, Paper.year, Paper.publication_date, Paper.source)
            .where(Paper.year > 2030)
        )).all()
        print(f"Papers with year > 2030: {len(bad_year)}")
        for p in bad_year[:10]:
            print(f"  id={p[0]} year={p[2]} date={p[3]} src={p[4]} title={p[1][:50]}")

        # Check for papers without year but with publication_date
        no_year = (await db.execute(
            select(Paper.id, Paper.title, Paper.year, Paper.publication_date, Paper.source)
            .where(Paper.year.is_(None), Paper.publication_date.isnot(None))
        )).all()
        print(f"\nPapers with pub_date but no year: {len(no_year)}")

        # Total papers
        total = (await db.execute(select(Paper.id))).scalars().all()
        print(f"\nTotal papers: {len(total)}")

asyncio.run(check())
