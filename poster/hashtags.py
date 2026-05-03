import random

THEME_TAGS = {
    "samurai": ["#anime", "#samurai", "#katana", "#night", "#japan", "#moonlight"],
    "school": ["#anime", "#school", "#evening", "#sliceoflife", "#classroom", "#quiet"],
    "cyberpunk": ["#anime", "#cyberpunk", "#neon", "#nightcity", "#streetlights", "#rain"],
    "fantasy": ["#anime", "#fantasy", "#magic", "#myth", "#dream", "#moon"],
    "action": ["#anime", "#action", "#battle", "#dynamic", "#sword", "#scene"],
    "melancholy": ["#anime", "#rain", "#night", "#city", "#atmosphere", "#lights"],
    "cozy": ["#anime", "#cozy", "#warmlight", "#home", "#quiet", "#evening"],
    "anime art": ["#anime", "#artwork", "#illustration", "#aesthetic", "#scene", "#mood"],
}

def generate_hashtags(topic: str) -> str:
    pool = THEME_TAGS.get(topic, THEME_TAGS["anime art"])
    k = random.randint(4, min(7, len(pool)))
    tags = random.sample(pool, k=k)
    if "#аниме" not in tags:
        tags[0] = "#аниме"
    return " ".join(tags)
