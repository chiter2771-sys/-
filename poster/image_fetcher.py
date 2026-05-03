import hashlib
import json
import logging
import random
from pathlib import Path

import aiohttp

from poster.content_filters import has_blocked_tags, quality_score
from poster.image_validator import validate_image_file

logger = logging.getLogger(__name__)
HEADERS = {"User-Agent": "VKAnimeBot/1.0", "Accept": "application/json,text/plain,*/*"}


class ImageFetcher:
    def __init__(self, storage_dir: Path, min_w: int, min_h: int):
        self.storage_dir = storage_dir
        self.min_w = min_w
        self.min_h = min_h

    async def fetch_random(self, blocked_urls: set[str] | None = None):
        async with aiohttp.ClientSession(headers=HEADERS, timeout=aiohttp.ClientTimeout(total=25)) as session:
            candidates = await self._collect_candidates(session)
            random.shuffle(candidates)
            for url, w, h, tags, source, provider_score in candidates[:200]:
                if not url or (blocked_urls and url in blocked_urls):
                    continue
                if has_blocked_tags(tags):
                    continue
                score = quality_score(tags, w, h, provider_score)
                if score < 40:
                    continue
                out = await self._download(session, url)
                if not out:
                    continue
                valid, reason, size = validate_image_file(out, self.min_w, self.min_h)
                if not valid:
                    logger.warning("invalid image source=%s reason=%s url=%s", source, reason, url)
                    out.unlink(missing_ok=True)
                    continue
                topic = self._topic_from_tags(tags)
                checksum = hashlib.sha256(out.read_bytes()).hexdigest()
                logger.info("image validated source=%s score=%s size=%s url=%s", source, score, size, url)
                return url, out, topic, checksum, tags, source, size
        return None

    async def _collect_candidates(self, s):
        c = []
        c.extend(await self._fetch_safebooru(s))
        c.extend(await self._fetch_danbooru(s))
        c.extend(await self._fetch_gelbooru(s))
        c.extend(await self._fetch_konachan(s))
        c.extend(await self._fetch_zerochan(s))
        return c

    def _topic_from_tags(self, tags: str) -> str:
        t = tags.lower()
        if any(x in t for x in ("neon", "night", "city", "cyberpunk")): return "night city"
        if any(x in t for x in ("sakura", "kimono")): return "sakura"
        if any(x in t for x in ("beach", "ocean")): return "beach aesthetic"
        if any(x in t for x in ("fantasy", "elf", "magic")): return "fantasy"
        return "anime aesthetic"

    async def _fetch_safebooru(self, s):
        u = "https://safebooru.org/index.php?page=dapi&s=post&q=index&json=1&limit=100&tags=anime+1girl+rating:safe+masterpiece+best_quality"
        return await self._fetch_generic_json(s, u, "safebooru", "file_url", "width", "height", "tags", "score")

    async def _fetch_danbooru(self, s):
        u = "https://danbooru.donmai.us/posts.json?limit=100&tags=rating:g+anime_girl+masterpiece+-school_uniform"
        return await self._fetch_generic_json(s, u, "danbooru", "file_url", "image_width", "image_height", "tag_string_general", "score")

    async def _fetch_gelbooru(self, s):
        u = "https://gelbooru.com/index.php?page=dapi&s=post&q=index&json=1&limit=100&tags=rating:safe+anime+1girl+masterpiece"
        return await self._fetch_generic_json(s, u, "gelbooru", "file_url", "width", "height", "tags", "score")

    async def _fetch_konachan(self, s):
        u = "https://konachan.com/post.json?limit=100&tags=safe+anime+masterpiece+-school_uniform"
        return await self._fetch_generic_json(s, u, "konachan", "file_url", "width", "height", "tags", "score")

    async def _fetch_zerochan(self, s):
        return []

    async def _fetch_generic_json(self, s, url, source, file_key, w_key, h_key, tags_key, score_key):
        try:
            async with s.get(url) as r:
                if r.status != 200:
                    return []
                d = json.loads(await r.text())
            rows = d if isinstance(d, list) else d.get("post", []) if isinstance(d, dict) else []
            return [
                (x.get(file_key, ""), int(x.get(w_key, 0) or 0), int(x.get(h_key, 0) or 0), (x.get(tags_key) or ""), source, int(x.get(score_key, 0) or 0))
                for x in rows if x.get(file_key)
            ]
        except Exception:
            logger.exception("image provider fetch failed source=%s", source)
            return []

    async def _download(self, s, url):
        p = self.storage_dir / (hashlib.md5(url.encode()).hexdigest() + ".jpg")
        try:
            async with s.get(url) as r:
                if r.status != 200:
                    return None
                if not (r.headers.get("Content-Type", "").lower().startswith("image/")):
                    return None
                p.write_bytes(await r.read())
            return p
        except Exception:
            return None
