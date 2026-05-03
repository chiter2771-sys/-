REQUIRED_HINTS = {
    "masterpiece", "best_quality", "anime_girl", "aesthetic", "cinematic_lighting",
    "detailed", "beautiful_eyes", "vibrant_colors", "ultra_detailed", "anime_art",
}

BLACKLIST_TAGS = {
    "school", "uniform", "classroom", "student", "loli", "gore", "nsfw", "lowres",
    "bad_anatomy", "blurry", "monochrome", "sketch", "comic", "manga_page", "watermark",
    "jpeg_artifacts", "bad_hands", "extra_limbs", "text", "logo",
}

AESTHETIC_BONUS = {
    "night", "neon", "rain", "sakura", "beach", "fantasy", "kimono", "cyberpunk", "cozy", "dreamy",
}


def has_blocked_tags(tags: str) -> bool:
    tagset = {t.strip().lower() for t in (tags or "").replace(",", " ").split() if t.strip()}
    return any(t in tagset for t in BLACKLIST_TAGS)


def quality_score(tags: str, width: int, height: int, provider_score: int = 0) -> int:
    tagset = {t.strip().lower() for t in (tags or "").replace(",", " ").split() if t.strip()}
    score = provider_score
    if width >= 1200:
        score += 20
    if height > width:
        score += 20
    ratio = width / max(height, 1)
    if 0.5 <= ratio <= 0.85:
        score += 15
    score += sum(5 for x in AESTHETIC_BONUS if x in tagset)
    score += sum(3 for x in REQUIRED_HINTS if x in tagset)
    score -= sum(30 for x in BLACKLIST_TAGS if x in tagset)
    return score
