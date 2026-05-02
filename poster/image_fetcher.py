import hashlib
import json
import logging
import random
from pathlib import Path

import aiohttp

logger = logging.getLogger(__name__)

TOPICS = ["аниме ночной город", "дождливая аниме-улица", "уютная аниме-комната", "киберпанк аниме", "аниме-пейзаж"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 VKAnimeBot/1.0",
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "en-US,en;q=0.9",
}

REDDIT_SOURCES = [
    "https://www.reddit.com/r/Animewallpaper/top.json?t=day&limit=30",
    "https://www.reddit.com/r/ImaginarySliceOfLife/top.json?t=day&limit=30",
]

ANIME_HINTS = ("anime", "аниме", "manga", "waifu", "pixiv", "illustration", "digital art")

class ImageFetcher:
    def __init__(self, storage_dir: Path, min_w: int, min_h: int):
        self.storage_dir = storage_dir
        self.min_w = max(640, min_w)
        self.min_h = max(640, min_h)

    async def fetch_random(self, blocked_urls: set[str] | None = None) -> tuple[str, Path, str, str] | None:
        topic = random.choice(TOPICS)
        async with aiohttp.ClientSession(headers=HEADERS, timeout=aiohttp.ClientTimeout(total=20)) as session:
            for attempt in range(3):
                try:
                    candidates = await self._collect_candidates(session)
                    random.shuffle(candidates)
                    for img_url, width, height in candidates:
                        if blocked_urls and img_url in blocked_urls:
                            logger.info("Image skipped (already posted): %s", img_url)
                            continue
                        if width < self.min_w or height < self.min_h:
                            logger.info("Image rejected by size %sx%s: %s", width, height, img_url)
                            continue
                        if not self._looks_like_anime(img_url):
                            logger.info("Image rejected: no anime hints %s", img_url)
                            continue
                        out = await self._download(session, img_url)
                        if not out:
                            continue
                        checksum = hashlib.sha256(out.read_bytes()).hexdigest()
                        return img_url, out, topic, checksum
                except Exception as exc:
                    logger.warning("Image fetch attempt %s failed: %s", attempt + 1, exc)
            logger.error("No valid image found after retries")
        return None

    async def _collect_candidates(self, session):
        candidates = []
        for src in REDDIT_SOURCES:
            candidates.extend(await self._fetch_reddit_posts(session, src))
        candidates.extend(await self._fetch_danbooru(session))
        candidates.extend(await self._fetch_konachan(session))
        candidates.extend(await self._fetch_safebooru(session))
        candidates.extend(await self._fetch_wallhaven(session))
        return candidates

    async def _fetch_reddit_posts(self, session, src):
        try:
            async with session.get(src) as r:
                if r.status != 200:
                    logger.warning("Reddit rejected %s with %s", src, r.status)
                    return []
                data = await r.json(content_type=None)
        except Exception as exc:
            logger.warning("Reddit source failed %s: %s", src, exc)
            return []
        out = []
        for child in (((data or {}).get("data") or {}).get("children") or []):
            post = (child or {}).get("data") or {}
            if post.get("over_18") or post.get("is_video"):
                continue
            title = (post.get("title") or "").lower()
            if not any(h in title for h in ANIME_HINTS):
                continue
            img = (((post.get("preview") or {}).get("images") or [{}])[0].get("source") or {})
            url = (img.get("url") or "").replace("&amp;", "&")
            if not url:
                continue
            out.append((url, int(img.get("width", 0) or 0), int(img.get("height", 0) or 0)))
        return out

    async def _fetch_danbooru(self, session):
        url = "https://danbooru.donmai.us/posts.json?limit=20&tags=rating:g+anime+scenery"
        try:
            async with session.get(url) as r:
                if r.status != 200:
                    return []
                data = json.loads(await r.text())
            return [(x.get("file_url", ""), int(x.get("image_width", 0)), int(x.get("image_height", 0))) for x in data if x.get("file_url")]
        except Exception:
            return []

    async def _fetch_safebooru(self, session):
        url = "https://safebooru.org/index.php?page=dapi&s=post&q=index&json=1&limit=25&tags=anime+scenery"
        try:
            async with session.get(url) as r:
                if r.status != 200:
                    return []
                data = json.loads(await r.text())
            return [(x.get("file_url", ""), int(x.get("width", 0)), int(x.get("height", 0))) for x in data if x.get("file_url")]
        except Exception:
            return []

    async def _fetch_konachan(self, session):
        url = "https://konachan.com/post.json?limit=20&tags=safe+scenery"
        try:
            async with session.get(url) as r:
                if r.status != 200:
                    return []
                data = json.loads(await r.text())
            return [(x.get("file_url", ""), int(x.get("width", 0)), int(x.get("height", 0))) for x in data if x.get("file_url")]
        except Exception:
            return []

    async def _fetch_wallhaven(self, session):
        url = "https://wallhaven.cc/api/v1/search?q=anime+city+night&categories=010&purity=100&atleast=1280x720&sorting=favorites"
        try:
            async with session.get(url) as r:
                if r.status != 200:
                    return []
                data = json.loads(await r.text())
            out = []
            for x in (data.get("data") or []):
                tags = " ".join((t.get("name", "") for t in (x.get("tags") or []))).lower()
                if "anime" not in tags:
                    continue
                out.append((x.get("path", ""), int(x.get("dimension_x", 0)), int(x.get("dimension_y", 0))))
            return out
        except Exception:
            return []

    def _looks_like_anime(self, url: str) -> bool:
        low = (url or "").lower()
        blocked = ("unsplash", "pexels", "shutterstock", "gettyimages", "nature")
        if any(x in low for x in blocked):
            return False
        return True

    async def _download(self, session: aiohttp.ClientSession, url: str) -> Path | None:
        if not url:
            return None
        name = hashlib.md5(url.encode()).hexdigest() + ".jpg"
        path = self.storage_dir / name
        try:
            async with session.get(url) as r:
                if r.status != 200:
                    logger.warning("Download reject status %s: %s", r.status, url)
                    return None
                if not (r.headers.get("Content-Type", "").lower().startswith("image/")):
                    logger.warning("Download reject content type: %s", url)
                    return None
                path.write_bytes(await r.read())
            return path
        except Exception as exc:
            logger.warning("Download failed %s: %s", url, exc)
            return None
