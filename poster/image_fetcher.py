import hashlib
import json
import logging
import random
import traceback
from pathlib import Path

import aiohttp

logger = logging.getLogger(__name__)

TOPICS = ["anime scenery", "rainy night", "cozy anime night", "melancholy city", "cyberpunk anime"]

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 VKContentBot/1.2 (+https://vk.com)"}

REDDIT_SOURCES = [
    "https://www.reddit.com/r/Animewallpaper/top.json?t=day&limit=20",
    "https://www.reddit.com/r/ImaginarySliceOfLife/top.json?t=day&limit=20",
    "https://www.reddit.com/r/AnimeART/top.json?t=day&limit=20",
    "https://www.reddit.com/r/Cyberpunk/top.json?t=week&limit=20",
]

FALLBACK_SOURCE = "https://nekos.best/api/v2/neko"


class ImageFetcher:
    def __init__(self, storage_dir: Path, min_w: int, min_h: int):
        self.storage_dir = storage_dir
        # Keep configured limits but do not over-reject medium images
        self.min_w = max(480, min_w)
        self.min_h = max(480, min_h)

    async def fetch_random(self, blocked_urls: set[str] | None = None) -> tuple[str, Path, str, str] | None:
        topic = random.choice(TOPICS)
        logger.info("Image fetch start. topic=%s", topic)
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            candidates = []
            for src in REDDIT_SOURCES:
                posts = await self._fetch_reddit_posts(session, src)
                candidates.extend(posts)

            random.shuffle(candidates)
            for img_url, width, height in candidates:
                if blocked_urls and img_url in blocked_urls:
                    continue
                if width < self.min_w or height < self.min_h:
                    logger.info("Rejected reddit image by size %sx%s (< %sx%s): %s", width, height, self.min_w, self.min_h, img_url)
                    continue
                out = await self._download(session, img_url)
                if not out:
                    continue
                checksum = hashlib.sha256(out.read_bytes()).hexdigest()
                logger.info("Image fetched successfully")
                logger.info("Final image url: %s", img_url)
                return img_url, out, topic, checksum

            logger.warning("Reddit sources exhausted, switching to fallback")
            fallback = await self._fetch_nekos_best(session)
            if fallback:
                img_url, width, height = fallback
                if width >= self.min_w and height >= self.min_h:
                    out = await self._download(session, img_url)
                    if out:
                        checksum = hashlib.sha256(out.read_bytes()).hexdigest()
                        logger.info("Image fetched successfully")
                        logger.info("Final image url: %s", img_url)
                        return img_url, out, topic, checksum
                logger.warning("Fallback image rejected by dimensions %sx%s (< %sx%s): %s", width, height, self.min_w, self.min_h, img_url)

        logger.error("No image fetched. All sources exhausted.")
        return None

    async def _fetch_reddit_posts(self, session: aiohttp.ClientSession, src: str) -> list[tuple[str, int, int]]:
        logger.info("Trying Reddit source: %s", src)
        try:
            async with session.get(src, timeout=25) as r:
                status = r.status
                logger.info("Reddit HTTP status: %s for %s", status, src)
                if status == 403:
                    logger.warning("Reddit 403 for %s, will use fallback sources", src)
                    return []
                if status != 200:
                    logger.warning("Reddit non-200 for %s: %s", src, status)
                    return []
                text = await r.text()
                if not text.strip():
                    logger.warning("Empty Reddit response: %s", src)
                    return []
                data = json.loads(text)
                logger.info("Image JSON parsed successfully")
        except Exception as e:
            logger.error("Reddit source failed: %s (%s)", src, e)
            logger.error("Traceback:\n%s", traceback.format_exc())
            return []

        result = []
        children = (((data or {}).get("data") or {}).get("children") or [])
        for child in children:
            post = (child or {}).get("data") or {}
            if post.get("over_18"):
                continue
            if post.get("is_video"):
                continue
            url = post.get("url_overridden_by_dest") or post.get("url") or ""
            lower = url.lower()
            if any(lower.endswith(ext) for ext in [".jpg", ".jpeg", ".png"]):
                width, height = self._preview_size(post)
                if width and height:
                    result.append((url, width, height))
                continue

            if "preview" in post:
                img = (((post.get("preview") or {}).get("images") or [{}])[0].get("source") or {})
                purl = (img.get("url") or "").replace("&amp;", "&")
                if purl and not purl.lower().endswith(".gif"):
                    width = int(img.get("width", 0) or 0)
                    height = int(img.get("height", 0) or 0)
                    if width and height:
                        result.append((purl, width, height))

        logger.info("Reddit parsed candidates: %s from %s", len(result), src)
        return result

    async def _fetch_nekos_best(self, session: aiohttp.ClientSession) -> tuple[str, int, int] | None:
        try:
            async with session.get(FALLBACK_SOURCE, timeout=25) as r:
                logger.info("Fallback HTTP status: %s for %s", r.status, FALLBACK_SOURCE)
                if r.status != 200:
                    return None
                text = await r.text()
                if not text.strip():
                    return None
                data = json.loads(text)
                logger.info("Image JSON parsed successfully")
                results = data.get("results") or []
                if not results:
                    return None
                url = results[0].get("url")
                if not url:
                    return None
                width = int(results[0].get("width", 0) or 0)
                height = int(results[0].get("height", 0) or 0)
                if (not width or not height):
                    width, height = await self._probe_dimensions(session, url)
                return url, width, height
        except Exception as e:
            logger.error("Fallback source failed: %s", e)
            logger.error("Traceback:\n%s", traceback.format_exc())
            return None

    def _preview_size(self, post: dict) -> tuple[int, int]:
        preview = post.get("preview") or {}
        images = preview.get("images") or []
        if not images:
            return 0, 0
        source = images[0].get("source") or {}
        return int(source.get("width", 0) or 0), int(source.get("height", 0) or 0)

    async def _probe_dimensions(self, session: aiohttp.ClientSession, url: str) -> tuple[int, int]:
        try:
            from PIL import Image
            from io import BytesIO

            async with session.get(url, timeout=25) as r:
                if r.status != 200:
                    return 0, 0
                raw = await r.read()
            img = Image.open(BytesIO(raw))
            return img.size
        except Exception:
            return 0, 0

    async def _download(self, session: aiohttp.ClientSession, url: str) -> Path | None:
        name = hashlib.md5(url.encode()).hexdigest() + ".jpg"
        path = self.storage_dir / name
        try:
            async with session.get(url, timeout=25) as r:
                logger.info("Download HTTP status: %s for %s", r.status, url)
                content_type = (r.headers.get("Content-Type") or "").lower()
                if r.status != 200:
                    logger.warning("Download rejected: non-200 status for %s", url)
                    return None
                if not content_type.startswith("image/"):
                    logger.warning("Download rejected: invalid content-type %s for %s", content_type, url)
                    return None
                path.write_bytes(await r.read())
            logger.info("Download saved: %s", path)
            return path
        except Exception as e:
            logger.error("Download failed for %s: %s", url, e)
            logger.error("Traceback:\n%s", traceback.format_exc())
            return None
