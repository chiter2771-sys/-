import random

THEME_TAGS = {
    "samurai": ["#anime", "#samurai", "#katana", "#night", "#artwork", "#japan"],
    "school": ["#anime", "#schoolgirl", "#sliceoflife", "#aesthetic", "#daily", "#artwork"],
    "cyberpunk": ["#anime", "#cyberpunk", "#neon", "#nightcity", "#scifi", "#artwork"],
    "fantasy": ["#anime", "#fantasy", "#magic", "#artwork", "#myth", "#dream"],
    "action": ["#anime", "#action", "#battle", "#sword", "#artwork", "#dynamic"],
    "melancholy": ["#anime", "#rain", "#night", "#citylights", "#aesthetic", "#artwork"],
    "cozy": ["#anime", "#cozy", "#warmlight", "#quiet", "#aesthetic", "#artwork"],
    "anime art": ["#anime", "#animeart", "#illustration", "#artwork", "#aesthetic", "#scene"],
}

def generate_hashtags(topic: str) -> str:
    pool = THEME_TAGS.get(topic, THEME_TAGS["anime art"])
    k = random.randint(4, min(8, len(pool)))
    tags = random.sample(pool, k=k)
    if "#anime" not in tags:
        tags[0] = "#anime"
    return " ".join(tags)
