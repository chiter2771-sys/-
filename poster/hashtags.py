import random

BASE = ["#anime", "#animegirl", "#animeart", "#аниме", "#art", "#aesthetic"]
EXTRA = {
    "night city": ["#night", "#cyberpunk", "#vibes"],
    "sakura": ["#sakuralover", "#vibes", "#japan"],
    "beach aesthetic": ["#vibes", "#dreamy", "#beach"],
    "fantasy": ["#fantasy", "#waifu", "#vibes"],
    "anime aesthetic": ["#vibes", "#waifu", "#dreamy"],
}


def generate_hashtags(topic: str) -> str:
    tags = BASE[:]
    tags.extend(random.sample(EXTRA.get(topic, EXTRA["anime aesthetic"]), k=2))
    return " ".join(tags)
