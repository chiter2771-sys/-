import random

BASE_TAGS = ["#anime", "#аниме", "#art", "#арт", "#aesthetic", "#scenery", "#animegirl", "#sakura", "#cyberpunk"]


def generate_hashtags(topic: str) -> str:
    topic_tags = {
        "anime scenery": ["#scenery", "#landscape"],
        "sakura": ["#sakura", "#spring"],
        "anime girl": ["#animegirl", "#waifu"],
        "rainy night": ["#rain", "#nightvibes"],
        "aesthetic anime": ["#aesthetic", "#vibes"],
        "cyberpunk anime": ["#cyberpunk", "#neon"],
    }.get(topic, ["#anime"])
    tags = list(set(topic_tags + random.sample(BASE_TAGS, k=5)))
    return " ".join(tags[:8])
