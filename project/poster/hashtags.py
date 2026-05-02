import random

TOPIC_TAGS = {
    "киберпанк аниме": ["#anime", "#cyberpunk", "#nightcity", "#neon", "#animeart", "#citylights", "#aesthetic"],
    "аниме ночной город": ["#anime", "#nightcity", "#animecity", "#citylights", "#lofi", "#aesthetic", "#animeart"],
    "дождливая аниме-улица": ["#anime", "#rain", "#rainycity", "#nightcity", "#animeart", "#atmosphere", "#lofi"],
    "аниме-пейзаж": ["#anime", "#animescenery", "#animeart", "#landscape", "#night", "#aesthetic", "#lofi"],
    "эстетичное аниме": ["#anime", "#animeart", "#aesthetic", "#nightcity", "#lofi", "#atmosphere", "#illustration"],
}

def generate_hashtags(topic: str) -> str:
    pool = TOPIC_TAGS.get(topic, ["#anime", "#animeart", "#nightcity", "#aesthetic", "#lofi"])
    k = random.randint(4, min(8, len(pool)))
    return " ".join(pool[:k])
