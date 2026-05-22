import csv
import logging
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.journal import Journal
from app.models.paper import Paper

logger = logging.getLogger(__name__)


ABBREV_MAP = {
    "adv": "advanced",
    "algor": "algorithm",
    "anal": "analysis",
    "appl": "applications",
    "applic": "applications",
    "archit": "architecture",
    "artif": "artificial",
    "automat": "automation",
    "auton": "autonomous",
    "behav": "behavior",
    "bio": "biological",
    "bioinform": "bioinformatics",
    "biol": "biology",
    "cogn": "cognitive",
    "commer": "commerce",
    "commun": "communications",
    "comput": "computing",
    "conf": "conference",
    "cybern": "cybernetics",
    "distrib": "distributed",
    "electron": "electronics",
    "eng": "engineering",
    "environ": "environment",
    "evol": "evolutionary",
    "factors": "factors",
    "found": "foundations",
    "hum": "human",
    "human": "human",
    "humaniz": "humanized",
    "image": "image",
    "inf": "information",
    "inform": "informatics",
    "integr": "integrated",
    "int": "international",
    "intell": "intelligent",
    "interact": "interactive",
    "j": "journal",
    "knowl": "knowledge",
    "lang": "language",
    "learn": "learning",
    "lett": "letters",
    "mach": "machine",
    "manag": "management",
    "manuf": "manufacturing",
    "med": "medical",
    "mob": "mobile",
    "multim": "multimedia",
    "multimed": "multimedia",
    "netw": "networks",
    "neural": "neural",
    "numer": "numerical",
    "optim": "optimization",
    "parallel": "parallel",
    "pattern": "pattern",
    "pers": "personal",
    "proc": "proceedings",
    "process": "processing",
    "program": "programming",
    "recogn": "recognition",
    "recognit": "recognition",
    "reliab": "reliability",
    "represent": "representation",
    "res": "research",
    "robot": "robotics",
    "saf": "safety",
    "sci": "science",
    "secur": "security",
    "signal": "signal",
    "simul": "simulation",
    "softw": "software",
    "struct": "structural",
    "syst": "systems",
    "technol": "technology",
    "theor": "theoretical",
    "trans": "transactions",
    "transp": "transportation",
    "ubiquit": "ubiquitous",
    "vis": "visual",
    "wirel": "wireless",
}

# Pre-normalize strip words
STRIP_WORDS = [
    "the", "journal of", "proceedings of the", "ieee", "acm", "international",
    "on", "and", "of", "for", "in", "an", "a",
]


def _expand_abbrev(word: str) -> str:
    """Expand a single abbreviated word if found in the map."""
    # Strip trailing dot (common in abbrevs like "Intell.")
    clean = word.rstrip(".")
    if clean.lower() in ABBREV_MAP:
        return ABBREV_MAP[clean.lower()]
    return word


def normalize_name(name: str) -> str:
    n = name.lower()
    n = n.replace("-", " ").replace("–", " ").replace("—", " ")
    n = re.sub(r"[^a-z0-9\s\.]", "", n)
    n = re.sub(r"\s+", " ", n).strip()

    # Expand abbreviations word by word
    words = n.split()
    words = [_expand_abbrev(w) for w in words]
    n = " ".join(words)

    # Remove dots left after expansion
    n = n.replace(".", "")

    # Remove stop words from any position
    words = n.split()
    # Single-word removals
    single_stops = {w for w in STRIP_WORDS if " " not in w}
    words = [w for w in words if w not in single_stops]
    n = " ".join(words)
    # Multi-word phrase removals (only start/end)
    for w in sorted([w for w in STRIP_WORDS if " " in w], key=len, reverse=True):
        if n.startswith(w + " "):
            n = n[len(w) + 1 :]
        if n.endswith(" " + w):
            n = n[: -len(w) - 1]
    return n.strip()


async def resolve_sci_zone(paper_id: int) -> str | None:
    async with async_session() as db:
        paper = await db.get(Paper, paper_id)
        if not paper or not paper.journal_name:
            return None
        zone = await _match_journal(db, paper.journal_name)
        if zone:
            paper.sci_zone = zone
            await db.commit()
        return zone


async def bulk_resolve(paper_ids: list[int]) -> int:
    resolved = 0
    for pid in paper_ids:
        zone = await resolve_sci_zone(pid)
        if zone:
            resolved += 1
    return resolved


async def match_journal_zone(db: AsyncSession, journal_name: str | None) -> str | None:
    if not journal_name:
        return None
    return await _match_journal(db, journal_name)


async def _match_journal(db: AsyncSession, journal_name: str) -> str | None:
    norm = normalize_name(journal_name)
    if not norm or len(norm) < 5:
        return None

    result = await db.execute(select(Journal))
    all_journals = result.scalars().all()

    norm_words = set(norm.split())

    best_match: tuple[int, str | None] = (0, None)  # (score, zone)

    for j in all_journals:
        jn = normalize_name(j.name)
        if not jn:
            continue

        # Level 1: exact match
        if jn == norm:
            return j.sci_zone

        # Level 2: full substring match (longer contains shorter)
        if len(norm) >= 15 and len(jn) >= 15:
            if norm in jn or jn in norm:
                return j.sci_zone

        # Level 3: word overlap score
        j_words = set(jn.split())
        common = norm_words & j_words
        if len(common) >= 3:
            overlap = len(common) / max(len(norm_words), len(j_words))
            score = len(common) + int(overlap * 10)
            if score > best_match[0]:
                best_match = (score, j.sci_zone)

    if best_match[0] >= 3:  # Threshold: at least 2 common words with some overlap
        return best_match[1]

    return None


async def seed_journals_from_csv(filepath: str = "data/jcr_seed.csv") -> int:
    count = 0
    async with async_session() as db:
        existing = (await db.execute(select(Journal))).scalars().all()
        if existing:
            logger.info("Journals table already has %d entries, skipping seed", len(existing))
            return 0

        try:
            with open(filepath, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    j = Journal(
                        name=row["name"].strip(),
                        issn=row.get("issn", "").strip() or None,
                        sci_zone=row["sci_zone"].strip(),
                        category=row.get("category", "").strip() or None,
                        year=int(row.get("year", 2024)),
                    )
                    db.add(j)
                    count += 1
            await db.commit()
            logger.info("Seeded %d journals from %s", count, filepath)
        except FileNotFoundError:
            logger.warning("Seed file not found: %s", filepath)

    return count
