import random

KEYWORDS = ["anime", "manga", "trailer", "season", "movie", "studio"]


def pick_news(entries: list[dict]) -> dict | None:
    pool = [e for e in entries if any(k in e.get("title", "").lower() for k in KEYWORDS)]
    if not pool:
        return None
    return random.choice(pool)
