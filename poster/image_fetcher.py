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

    async def fetch_random(self, blocked_urls: set[str] | None = None) -> tuple[str, Path, str, str, str, str, tuple[int, int]] | None:
        async with aiohttp.ClientSession(headers=HEADERS, timeout=aiohttp.ClientTimeout(total=20)) as session:
            candidates = await self._collect_candidates(session)
            random.shuffle(candidates)
            attempts = 0
            for url, w, h, tags, source, score in candidates:
                attempts += 1
                if attempts > 20:
                    break
                if not url or (blocked_urls and url in blocked_urls):
                    logger.info("image rejected source=%s reason=empty_or_blocked url=%s", source, url)
                    continue
                if score < 20:
                    logger.info("image rejected source=%s reason=low_score score=%s url=%s tags=%s", source, score, url, tags[:120])
                    continue
                if not self._is_quality_ok(url, w, h):
                    logger.info("image rejected source=%s reason=quality size=%sx%s url=%s", source, w, h, url)
                    continue
                if not self._is_anime_art(tags, url):
                    logger.info("image rejected source=%s reason=style_filter url=%s tags=%s", source, url, tags[:120])
                    continue
                out = await self._download(session, url)
                if not out:
                    logger.info("image rejected source=%s reason=download_failed url=%s", source, url)
                    continue
                topic = self._topic_from_tags(tags)
                checksum = hashlib.sha256(out.read_bytes()).hexdigest()
                logger.info("image accepted source=%s size=%sx%s url=%s", source, w, h, url)
                return url, out, topic, checksum, tags, source, (w, h)
        return None

    async def _collect_candidates(self, s):
        c=[]
        c.extend(await self._fetch_safebooru(s))
        c.extend(await self._fetch_danbooru(s))
        c.extend(await self._fetch_yandere(s))
        c.extend(await self._fetch_konachan(s))
        c.extend(await self._fetch_wallhaven(s))
        return c

    def _is_quality_ok(self, url:str,w:int,h:int)->bool:
        if h > w and (w < 700 or h < 900):
            return False
        if w >= h and (w < 1200 or h < 700):
            return False
        ratio = max(w, h) / max(min(w, h), 1)
        if ratio > 2.2:
            return False
        low=url.lower()
        if any(x in low for x in ("unsplash","pexels","getty","shutterstock")):
            return False
        return True

    def _is_anime_art(self, tags: str, url: str) -> bool:
        t = (tags or "").lower()
        u = (url or "").lower()
        bad = (
            "figure", "figurine", "toy", "merch", "cosplay", "live_action", "realistic",
            "3d", "cgi", "render", "logo", "watermark", "text", "screenshot", "comic",
            "manga_page", "panel", "model_kit",
        )
        if any(x in t for x in bad):
            return False
        if any(x in u for x in ("figure", "figurine", "toy", "merch", "logo")):
            return False
        good = ("1girl", "1boy", "anime", "original", "illustration", "solo")
        return any(x in t for x in good)

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
        u="https://safebooru.org/index.php?page=dapi&s=post&q=index&json=1&limit=80&tags=anime+1girl+rating:safe+score:>20"
        try:
            async with s.get(u) as r:
                if r.status!=200:return []
                d=json.loads(await r.text())
            return [(x.get("file_url",""),int(x.get("width",0)),int(x.get("height",0)),(x.get("tags") or ""),"safebooru", int(x.get("score", 0) or 0)) for x in d if x.get("file_url")]
        except Exception:return []

    async def _fetch_danbooru(self, s):
        u="https://danbooru.donmai.us/posts.json?limit=80&tags=rating:g+anime+score:>20+-comic"
        try:
            async with s.get(u) as r:
                if r.status!=200:return []
                d=json.loads(await r.text())
            out=[]
            for x in d:
                tags=(x.get("tag_string_general") or "")
                out.append((x.get("file_url",""),int(x.get("image_width",0)),int(x.get("image_height",0)),tags,"danbooru", int(x.get("score", 0) or 0)))
            return out
        except Exception:return []

    async def _fetch_konachan(self, s):
        u="https://konachan.com/post.json?limit=80&tags=safe+anime+score:>20"
        try:
            async with s.get(u) as r:
                if r.status!=200:return []
                d=json.loads(await r.text())
            return [(x.get("file_url",""),int(x.get("width",0)),int(x.get("height",0)),(x.get("tags") or ""),"konachan", int(x.get("score", 0) or 0)) for x in d if x.get("file_url")]
        except Exception:return []

    async def _fetch_yandere(self, s):
        u="https://yande.re/post.json?limit=80&tags=safe+anime+score:>20"
        try:
            async with s.get(u) as r:
                if r.status != 200:
                    return []
                d = json.loads(await r.text())
            return [(x.get("file_url", ""), int(x.get("width", 0)), int(x.get("height", 0)), (x.get("tags") or ""), "yandere", int(x.get("score", 0) or 0)) for x in d if x.get("file_url")]
        except Exception:
            return []

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
                out.append((x.get("path",""),int(x.get("dimension_x",0)),int(x.get("dimension_y",0)),tags,"wallhaven", int(x.get("favorites", 0) or 0)))
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
