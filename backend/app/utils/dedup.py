import re


def normalize_title(title: str) -> str:
    t = title.lower()
    t = re.sub(r"[^\w\s]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def generate_paper_key(paper: dict) -> str:
    doi = paper.get("doi")
    if doi:
        return f"doi:{doi.strip().lower()}"

    arxiv_id = paper.get("arxiv_id")
    if arxiv_id:
        aid = arxiv_id.strip()
        if aid.startswith("arxiv:"):
            aid = aid[6:]
        return f"arxiv:{aid}"

    title = normalize_title(paper.get("title", ""))
    authors = paper.get("authors", "[]")
    first_author = ""
    try:
        import json

        author_list = json.loads(authors) if isinstance(authors, str) else authors
        if author_list:
            first_author = author_list[0].split()[-1].lower()
    except (json.JSONDecodeError, IndexError):
        if isinstance(authors, str):
            first_author = authors.split(",")[0].strip().split()[-1].lower()

    return f"title:{title}|author:{first_author}"


def deduplicate_new_papers(
    new_papers: list[dict], existing_keys: set[str]
) -> list[dict]:
    seen_keys: set[str] = set()
    result: list[dict] = []

    for paper in new_papers:
        key = generate_paper_key(paper)
        if key in existing_keys or key in seen_keys:
            continue
        seen_keys.add(key)
        result.append(paper)

    return result
