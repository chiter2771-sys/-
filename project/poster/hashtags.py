import random


TOPIC_TAGS = {
    "anime scenery": ["#anime", "#аниме", "#scenery", "#art", "#aesthetic", "#атмосфера"],
    "sakura": ["#sakura", "#аниме", "#spring", "#арт", "#aesthetic", "#цветение"],
    "rainy night": ["#rainynight", "#ночь", "#anime", "#mood", "#aesthetic", "#дождь"],
    "cyberpunk anime": ["#cyberpunk", "#киберпанк", "#anime", "#neon", "#art", "#future"],
    "cozy anime night": ["#cozy", "#уют", "#anime", "#night", "#aesthetic", "#art"],
    "melancholy city": ["#melancholy", "#город", "#anime", "#vibes", "#aesthetic", "#art"],
}


def generate_hashtags(topic: str) -> str:
    tags = TOPIC_TAGS.get(topic) or ["#anime", "#аниме", "#art", "#aesthetic", "#vk"]
    # Minimum 4 tags, mixed RU/EN.
    count = random.randint(4, min(6, len(tags)))
    return " ".join(tags[:count])
