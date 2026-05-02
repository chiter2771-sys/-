import random


TOPIC_TAGS = {
    "anime scenery": ["#anime", "#animescenery", "#nightanime", "#lofi"],
    "rainy night": ["#anime", "#rainycity", "#nightanime", "#lofi", "#rain"],
    "cozy anime night": ["#anime", "#cozyanime", "#nightanime", "#lofi"],
    "melancholy city": ["#anime", "#melancholy", "#rainycity", "#nightanime"],
    "cyberpunk anime": ["#anime", "#cyberpunk", "#neoncity", "#nightanime", "#lofi"],
    "sakura": ["#anime", "#sakura", "#springanime", "#animeart"],
}


def generate_hashtags(topic: str) -> str:
    pool = TOPIC_TAGS.get(topic, ["#anime", "#animeart", "#nightanime"])
    k = random.randint(3, min(5, len(pool)))
    return " ".join(pool[:k])
