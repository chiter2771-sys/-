import asyncio
import hashlib
import logging
import random
from pathlib import Path

import aiohttp
from pixivpy3 import AppPixivAPI

from poster.image_validator import validate_image_file

logger = logging.getLogger(__name__)

PIXIV_QUERIES = [
    "anime girl night city",
    "anime aesthetic",
    "cyberpunk anime girl",
    "anime kimono",
    "sakura anime art",
    "cozy anime room",
    "rainy anime night",
    "japanese aesthetic anime",
    "fantasy anime girl",
    "anime sunset scenery",
]

BLOCKED_TERMS = {
    "school_uniform", "school uniform", "classroom", "loli", "child", "shota",
    "comic", "manga", "lowres", "blurry", "pixelated",
}


class ImageFetcher:
    def __init__(self, storage_dir: Path, min_w: int, min_h: int, pixiv_refresh_token: str):
        self.storage_dir = storage_dir
        self.min_w = max(min_w, 1200)
        self.min_h = max(min_h, 1200)
        self.pixiv_refresh_token = pixiv_refresh_token
        self.api = AppPixivAPI()
        self._query_index = 0

    async def fetch_random(self, blocked_urls: set[str] | None = None):
        if not await self._auth_pixiv():
            return None

        for attempt in range(1, 6):
            query = PIXIV_QUERIES[self._query_index % len(PIXIV_QUERIES)]
            self._query_index += 1
            logger.info("Pixiv search query used: %s", query)
            illusts = await asyncio.to_thread(self._search_pixiv, query)
            random.shuffle(illusts)
            for illust in illusts:
                picked = await self._try_illust(illust, blocked_urls)
                if picked:
                    return picked
            logger.warning("Pixiv search attempt failed attempt=%s/5 query=%s", attempt, query)
            await asyncio.sleep(min(12, attempt * 1.5))
        return None

    async def _auth_pixiv(self) -> bool:
        try:
            await asyncio.to_thread(self.api.auth, refresh_token=self.pixiv_refresh_token)
            logger.info("Pixiv auth success")
            return True
        except Exception:
            logger.exception("Pixiv auth failure")
            return False

    def _search_pixiv(self, query: str):
        result = self.api.search_illust(query, search_target="partial_match_for_tags", sort="date_desc", filter="for_ios")
        return list(getattr(result, "illusts", []) or [])

    async def _try_illust(self, illust, blocked_urls: set[str] | None):
        tags = " ".join(t.name.lower() for t in getattr(illust, "tags", []))
        caption = (getattr(illust, "caption", "") or "").lower()
        merged_text = f"{tags} {caption}"
        if any(term in merged_text for term in BLOCKED_TERMS):
            return None

        urls = getattr(illust, "meta_single_page", {}) or {}
        original = urls.get("original_image_url")
        if not original:
            pages = getattr(illust, "meta_pages", []) or []
            if pages:
                original = ((pages[0].get("image_urls") or {}).get("original"))
        if not original or (blocked_urls and original in blocked_urls):
            return None

        local = await self._download_original(original)
        if not local:
            return None

        valid, reason, size = validate_image_file(local, self.min_w, self.min_h)
        if not valid:
            logger.warning("Pixiv image rejected illust_id=%s reason=%s", getattr(illust, "id", "unknown"), reason)
            local.unlink(missing_ok=True)
            return None

        topic = "anime aesthetic"
        checksum = hashlib.sha256(local.read_bytes()).hexdigest()
        logger.info("Pixiv illustration ID: %s", getattr(illust, "id", "unknown"))
        logger.info("Pixiv image resolution: %sx%s", size[0], size[1])
        logger.info("Pixiv image download success: %s", local)
        return original, local, topic, checksum, tags, "pixiv", size

    async def _download_original(self, url: str):
        dest = self.storage_dir / f"pixiv_{hashlib.md5(url.encode()).hexdigest()}.jpg"
        headers = {"Referer": "https://app-api.pixiv.net/"}
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=45), headers=headers) as s:
                async with s.get(url) as r:
                    if r.status != 200:
                        return None
                    data = await r.read()
                    if not data:
                        return None
                    dest.write_bytes(data)
                    return dest
        except Exception:
            logger.exception("Pixiv image download failure")
            return None
