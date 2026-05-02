import hashlib
import random
from pathlib import Path

import aiohttp

TOPICS = ["anime scenery", "sakura", "anime girl", "rainy night", "aesthetic anime", "cyberpunk anime"]

# Public JSON/image endpoints only (no Selenium / no AI generation)
SOURCES = [
    "https://safebooru.org/index.php?page=dapi&s=post&q=index&json=1&limit=30&tags={query}",
    "https://konachan.com/post.json?limit=30&tags={query}",
]


class ImageFetcher:
    def __init__(self, storage_dir: Path, min_w: int, min_h: int):
        self.storage_dir = storage_dir
        self.min_w = min_w
        self.min_h = min_h

    async def fetch_random(self) -> tuple[str, Path, str, str] | None:
        topic = random.choice(TOPICS)
        query = topic.replace(" ", "+") + "+-rating:e"
        random.shuffle(SOURCES)
        async with aiohttp.ClientSession() as session:
            for src in SOURCES:
                try:
                    async with session.get(src.format(query=query), timeout=20) as r:
                        if r.status != 200:
                            continue
                        data = await r.json(content_type=None)
                    candidates = self._extract(data)
                    random.shuffle(candidates)
                    for img_url, w, h in candidates:
                        if w < self.min_w or h < self.min_h:
                            continue
                        out = await self._download(session, img_url)
                        if out:
                            checksum = hashlib.sha256(out.read_bytes()).hexdigest()
                            return img_url, out, topic, checksum
                except Exception:
                    continue
        return None

    def _extract(self, data):
        result = []
        for item in data if isinstance(data, list) else []:
            img = item.get("file_url") or item.get("jpeg_url")
            w = int(item.get("width", 0))
            h = int(item.get("height", 0))
            if img and "gif" not in img:
                if img.startswith("//"):
                    img = "https:" + img
                result.append((img, w, h))
        return result

    async def _download(self, session: aiohttp.ClientSession, url: str) -> Path | None:
        name = hashlib.md5(url.encode()).hexdigest() + ".jpg"
        path = self.storage_dir / name
        async with session.get(url, timeout=25) as r:
            if r.status != 200:
                return None
            path.write_bytes(await r.read())
        return path
