from typing import Any

import feedparser

RSS_FEEDS = [
    "https://www.animenewsnetwork.com/all/rss.xml",
    "https://myanimelist.net/rss/news.xml",
    "https://www.crunchyroll.com/newsrss",
]


def fetch_entries(limit: int = 20) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for url in RSS_FEEDS:
        feed = feedparser.parse(url)
        for e in feed.entries[:limit]:
            entries.append({
                "guid": getattr(e, "id", None) or getattr(e, "link", ""),
                "title": getattr(e, "title", ""),
                "link": getattr(e, "link", ""),
                "summary": getattr(e, "summary", ""),
                "published": getattr(e, "published", None),
            })
    return entries
