import hashlib
import logging
import random
from pathlib import Path

import requests

from poster.image_validator import validate_image_file

logger = logging.getLogger(__name__)

DANBOORU_URL = "https://danbooru.donmai.us/posts.json"
TAGS = [
    "1girl anime aesthetic beautiful anime_art night_city neon kimono pink_hair atmospheric",
    "1girl anime aesthetic neon_city night atmospheric pink_hair",
    "anime_art 1girl kimono night city_lights aesthetic",
]
BLACKLIST = {
    "school_uniform",
    "loli",
    "shota",
    "nsfw",
    "nude",
    "comic",
    "monochrome",
    "sketch",
    "manga",
    "lowres",
}
NEGATIVE_QUERY = " ".join(f"-{x}" for x in sorted(BLACKLIST))


def _is_blocked(tags: str) -> str | None:
    tag_set = set(tags.split())
    for term in BLACKLIST:
        if term in tag_set:
            return term
    rating = {t for t in tag_set if t.startswith("rating:")}
    if "rating:s" not in rating:
        return "unsafe_rating"
    return None


class ArtFetcher:
    def __init__(self, storage_dir: Path, min_w: int, min_h: int):
        self.storage_dir = storage_dir
        self.min_w = max(min_w, 1200)
        self.min_h = max(min_h, 1200)

    def fetch_art(self) -> dict[str, str] | None:
        for query in TAGS:
            search_tags = f"{query} {NEGATIVE_QUERY} rating:s -animated"
            try:
                res = requests.get(DANBOORU_URL, params={"tags": search_tags, "limit": 40, "random": "true"}, timeout=30)
                res.raise_for_status()
                posts = res.json()
            except Exception:
                logger.exception("Danbooru request failed")
                continue

            logger.info("Danbooru posts found: %s for query='%s'", len(posts), query)
            if not posts:
                continue

            random.shuffle(posts)
            for post in posts:
                ext = (post.get("file_ext") or "").lower()
                if ext not in {"jpg", "jpeg", "png"}:
                    logger.info("Skip post id=%s reason=bad_ext ext=%s", post.get("id"), ext)
                    continue

                all_tags = (post.get("tag_string") or "").strip().lower()
                blocked_reason = _is_blocked(all_tags)
                if blocked_reason:
                    logger.info("Skip post id=%s reason=%s", post.get("id"), blocked_reason)
                    continue

                image_url = post.get("file_url")
                if not image_url:
                    logger.info("Skip post id=%s reason=no_file_url", post.get("id"))
                    continue

                logger.info("Selected Danbooru image url: %s", image_url)
                return {"image": image_url, "tags": all_tags}

        return None

    def download_image(self, image_url: str) -> tuple[Path, str, tuple[int, int]] | None:
        suffix = ".png" if image_url.lower().endswith(".png") else ".jpg"
        dest = self.storage_dir / f"danbooru_{hashlib.md5(image_url.encode()).hexdigest()}{suffix}"
        try:
            r = requests.get(image_url, timeout=45)
            r.raise_for_status()
            if not r.content:
                logger.warning("Skip image reason=empty_body url=%s", image_url)
                return None
            dest.write_bytes(r.content)
        except Exception:
            logger.exception("Danbooru image download failed url=%s", image_url)
            return None

        valid, reason, size = validate_image_file(dest, self.min_w, self.min_h)
        if not valid:
            logger.warning("Skip image reason=%s url=%s", reason, image_url)
            dest.unlink(missing_ok=True)
            return None

        checksum = hashlib.sha256(dest.read_bytes()).hexdigest()
        return dest, checksum, size
