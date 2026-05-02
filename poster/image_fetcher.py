import hashlib
import json
import logging
import random
from pathlib import Path

import aiohttp

logger = logging.getLogger(__name__)

TOPICS = ["киберпанк аниме", "аниме ночной город", "дождливая аниме-улица", "аниме-пейзаж", "эстетичное аниме"]

HEADERS = {
    "User-Agent": "VKAnimeBot/1.0 (+https://vk.com)",
    "Accept": "application/json,text/plain,*/*",
}

MIN_W, MIN_H = 1280, 720

class ImageFetcher:
    def __init__(self, storage_dir: Path, min_w: int, min_h: int):
        self.storage_dir = storage_dir
        self.min_w = max(MIN_W, min_w)
        self.min_h = max(MIN_H, min_h)

    async def fetch_random(self, blocked_urls: set[str] | None = None) -> tuple[str, Path, str, str] | None:
        topic = random.choice(TOPICS)
        async with aiohttp.ClientSession(headers=HEADERS, timeout=aiohttp.ClientTimeout(total=20)) as session:
            for _ in range(2):
                candidates = await self._collect_candidates(session)
                random.shuffle(candidates)
                for img_url, width, height in candidates:
                    if not img_url or (blocked_urls and img_url in blocked_urls):
                        continue
                    if not self._is_valid_candidate(img_url, width, height):
                        continue
                    out = await self._download(session, img_url)
                    if not out:
                        continue
                    checksum = hashlib.sha256(out.read_bytes()).hexdigest()
                    return img_url, out, topic, checksum
        logger.warning("No suitable anime image found")
        return None

    async def _collect_candidates(self, session):
        c = []
        c.extend(await self._fetch_safebooru(session))
        c.extend(await self._fetch_danbooru(session))
        c.extend(await self._fetch_konachan(session))
        c.extend(await self._fetch_wallhaven(session))
        return c

    def _is_valid_candidate(self, url: str, w: int, h: int) -> bool:
        if w < self.min_w or h < self.min_h:
            logger.info("Reject small image %sx%s %s", w, h, url)
            return False
        if h > w:
            logger.info("Reject portrait image %sx%s %s", w, h, url)
            return False
        low = url.lower()
        if any(x in low for x in ("unsplash", "pexels", "getty", "shutterstock")):
            logger.info("Reject photo source url: %s", url)
            return False
        return True

    async def _fetch_safebooru(self, session):
        url = "https://safebooru.org/index.php?page=dapi&s=post&q=index&json=1&limit=40&tags=anime+city+night+-rating:explicit"
        try:
            async with session.get(url) as r:
                if r.status != 200:
                    return []
                data = json.loads(await r.text())
            return [(x.get("file_url",""), int(x.get("width",0)), int(x.get("height",0))) for x in data if x.get("file_url")]
        except Exception:
            return []

    async def _fetch_danbooru(self, session):
        url = "https://danbooru.donmai.us/posts.json?limit=40&tags=rating:g+anime+city+night+-comic"
        try:
            async with session.get(url) as r:
                if r.status != 200:
                    return []
                data = json.loads(await r.text())
            out = []
            for x in data:
                tags = (x.get("tag_string_general") or "").lower()
                if "anime" not in tags and "city" not in tags and "night" not in tags:
                    continue
                out.append((x.get("file_url",""), int(x.get("image_width",0)), int(x.get("image_height",0))))
            return out
        except Exception:
            return []

    async def _fetch_konachan(self, session):
        url = "https://konachan.com/post.json?limit=40&tags=safe+anime+city+night"
        try:
            async with session.get(url) as r:
                if r.status != 200:
                    return []
                data = json.loads(await r.text())
            return [(x.get("file_url",""), int(x.get("width",0)), int(x.get("height",0))) for x in data if x.get("file_url")]
        except Exception:
            return []

    async def _fetch_wallhaven(self, session):
        url = "https://wallhaven.cc/api/v1/search?q=anime+city+night+cyberpunk&categories=010&purity=100&ratios=16x9&atleast=1280x720"
        try:
            async with session.get(url) as r:
                if r.status != 200:
                    return []
                data = json.loads(await r.text())
            out=[]
            for x in (data.get("data") or []):
                tags = " ".join((t.get("name","") for t in (x.get("tags") or []))).lower()
                if "anime" not in tags:
                    continue
                out.append((x.get("path",""), int(x.get("dimension_x",0)), int(x.get("dimension_y",0))))
            return out
        except Exception:
            return []

    async def _download(self, session, url):
        path = self.storage_dir / (hashlib.md5(url.encode()).hexdigest() + ".jpg")
        try:
            async with session.get(url) as r:
                if r.status != 200:
                    return None
                if not (r.headers.get("Content-Type","").lower().startswith("image/")):
                    return None
                path.write_bytes(await r.read())
            return path
        except Exception:
            return None
