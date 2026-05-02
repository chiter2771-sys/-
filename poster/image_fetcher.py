import hashlib
import logging
import random
import traceback
from pathlib import Path

import aiohttp

logger = logging.getLogger(__name__)

TOPICS = ["anime scenery", "sakura", "anime girl", "rainy night", "aesthetic anime", "cyberpunk anime"]

HEADERS = {"User-Agent": "Mozilla/5.0"}

# Temporary test-safe sources only (as requested)
SOURCES = [
    "https://api.waifu.pics/sfw/waifu",
    "https://api.waifu.pics/sfw/shinobu",
    "https://api.waifu.pics/sfw/neko",
]


class ImageFetcher:
    def __init__(self, storage_dir: Path, min_w: int, min_h: int):
        self.storage_dir = storage_dir
        self.min_w = min_w
        self.min_h = min_h

    async def fetch_random(self) -> tuple[str, Path, str, str] | None:
        topic = random.choice(TOPICS)
        random.shuffle(SOURCES)
        logger.info("Image fetch start. topic=%s", topic)
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            for src in SOURCES:
                logger.info("Trying source: %s", src)
                try:
                    async with session.get(src, timeout=20) as r:
                        logger.info("Source HTTP status: %s for %s", r.status, src)
                        if r.status != 200:
                            logger.warning("Source rejected due to non-200 status: %s", r.status)
                            continue
                        data = await r.json(content_type=None)

                    img_url = data.get("url") if isinstance(data, dict) else None
                    if not img_url:
                        logger.warning("Source %s rejected: no image URL in payload: %s", src, data)
                        continue

                    logger.info("Candidate image url: %s", img_url)
                    out = await self._download(session, img_url)
                    if not out:
                        logger.warning("Image rejected: download failed for %s", img_url)
                        continue

                    if not await self._check_size(session, img_url):
                        logger.warning(
                            "Image rejected by size check (<%sx%s): %s",
                            self.min_w,
                            self.min_h,
                            img_url,
                        )
                        out.unlink(missing_ok=True)
                        continue

                    checksum = hashlib.sha256(out.read_bytes()).hexdigest()
                    logger.info("Image fetched successfully")
                    logger.info("Final image url: %s", img_url)
                    return img_url, out, topic, checksum
                except Exception as e:
                    logger.error("Source %s failed: %s", src, e)
                    logger.error("Traceback:\n%s", traceback.format_exc())
                    continue

        logger.error("No image fetched. All sources exhausted.")
        return None

    async def _check_size(self, session: aiohttp.ClientSession, url: str) -> bool:
        try:
            from PIL import Image
            from io import BytesIO

            async with session.get(url, timeout=25) as r:
                logger.info("Size-check HTTP status: %s for %s", r.status, url)
                if r.status != 200:
                    logger.warning("Size-check rejected: non-200 status for %s", url)
                    return False
                raw = await r.read()
            img = Image.open(BytesIO(raw))
            width, height = img.size
            logger.info("Image dimensions: %sx%s for %s", width, height, url)
            return width >= self.min_w and height >= self.min_h
        except Exception as e:
            logger.error("Size-check failed for %s: %s", url, e)
            logger.error("Traceback:\n%s", traceback.format_exc())
            return False

    async def _download(self, session: aiohttp.ClientSession, url: str) -> Path | None:
        name = hashlib.md5(url.encode()).hexdigest() + ".jpg"
        path = self.storage_dir / name
        try:
            async with session.get(url, timeout=25) as r:
                logger.info("Download HTTP status: %s for %s", r.status, url)
                if r.status != 200:
                    logger.warning("Download rejected: non-200 status for %s", url)
                    return None
                path.write_bytes(await r.read())
            logger.info("Download saved: %s", path)
            return path
        except Exception as e:
            logger.error("Download failed for %s: %s", url, e)
            logger.error("Traceback:\n%s", traceback.format_exc())
            return None
