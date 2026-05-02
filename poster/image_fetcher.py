import hashlib
import json
import logging
import random
from pathlib import Path

import aiohttp

logger = logging.getLogger(__name__)
HEADERS = {"User-Agent": "VKAnimeBot/1.0", "Accept": "application/json,text/plain,*/*"}

class ImageFetcher:
    def __init__(self, storage_dir: Path, min_w: int, min_h: int):
        self.storage_dir = storage_dir

    async def fetch_random(self, blocked_urls: set[str] | None = None) -> tuple[str, Path, str, str, str] | None:
        async with aiohttp.ClientSession(headers=HEADERS, timeout=aiohttp.ClientTimeout(total=20)) as session:
            candidates = await self._collect_candidates(session)
            random.shuffle(candidates)
            for url, w, h, tags in candidates:
                if not url or (blocked_urls and url in blocked_urls):
                    continue
                if not self._is_quality_ok(url, w, h):
                    continue
                out = await self._download(session, url)
                if not out:
                    continue
                topic = self._topic_from_tags(tags)
                checksum = hashlib.sha256(out.read_bytes()).hexdigest()
                return url, out, topic, checksum, tags
        return None

    async def _collect_candidates(self, s):
        c=[]
        c.extend(await self._fetch_safebooru(s))
        c.extend(await self._fetch_danbooru(s))
        c.extend(await self._fetch_konachan(s))
        c.extend(await self._fetch_wallhaven(s))
        return c

    def _is_quality_ok(self, url:str,w:int,h:int)->bool:
        if h > w and (w < 700 or h < 900):
            return False
        if w >= h and (w < 1200 or h < 700):
            return False
        low=url.lower()
        if any(x in low for x in ("unsplash","pexels","getty","shutterstock")):
            return False
        return True

    def _topic_from_tags(self, tags: str) -> str:
        t = tags.lower()
        if any(x in t for x in ("samurai", "katana", "kimono")): return "samurai"
        if any(x in t for x in ("school", "uniform", "classroom")): return "school"
        if any(x in t for x in ("cyberpunk", "neon", "mecha", "sci-fi")): return "cyberpunk"
        if any(x in t for x in ("magic", "fantasy", "elf", "witch", "dragon")): return "fantasy"
        if any(x in t for x in ("action", "battle", "sword", "fight")): return "action"
        if any(x in t for x in ("rain", "night", "city")): return "melancholy"
        if any(x in t for x in ("room", "tea", "cozy", "sunset")): return "cozy"
        return "anime art"

    async def _fetch_safebooru(self, s):
        u="https://safebooru.org/index.php?page=dapi&s=post&q=index&json=1&limit=60&tags=anime+-rating:explicit"
        try:
            async with s.get(u) as r:
                if r.status!=200:return []
                d=json.loads(await r.text())
            return [(x.get("file_url",""),int(x.get("width",0)),int(x.get("height",0)),(x.get("tags") or "")) for x in d if x.get("file_url")]
        except Exception:return []

    async def _fetch_danbooru(self, s):
        u="https://danbooru.donmai.us/posts.json?limit=60&tags=rating:g+anime+-comic"
        try:
            async with s.get(u) as r:
                if r.status!=200:return []
                d=json.loads(await r.text())
            out=[]
            for x in d:
                tags=(x.get("tag_string_general") or "")
                out.append((x.get("file_url",""),int(x.get("image_width",0)),int(x.get("image_height",0)),tags))
            return out
        except Exception:return []

    async def _fetch_konachan(self, s):
        u="https://konachan.com/post.json?limit=60&tags=safe+anime"
        try:
            async with s.get(u) as r:
                if r.status!=200:return []
                d=json.loads(await r.text())
            return [(x.get("file_url",""),int(x.get("width",0)),int(x.get("height",0)),(x.get("tags") or "")) for x in d if x.get("file_url")]
        except Exception:return []

    async def _fetch_wallhaven(self, s):
        u="https://wallhaven.cc/api/v1/search?q=anime&categories=010&purity=100&sorting=toplist"
        try:
            async with s.get(u) as r:
                if r.status!=200:return []
                d=json.loads(await r.text())
            out=[]
            for x in (d.get("data") or []):
                tags=" ".join((t.get("name","") for t in (x.get("tags") or []))).lower()
                if "anime" not in tags:continue
                out.append((x.get("path",""),int(x.get("dimension_x",0)),int(x.get("dimension_y",0)),tags))
            return out
        except Exception:return []

    async def _download(self,s,url):
        p=self.storage_dir/(hashlib.md5(url.encode()).hexdigest()+".jpg")
        try:
            async with s.get(url) as r:
                if r.status!=200:return None
                if not (r.headers.get("Content-Type","").lower().startswith("image/")): return None
                p.write_bytes(await r.read())
            return p
        except Exception:return None
