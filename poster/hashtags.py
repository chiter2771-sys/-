import random

THEME_TAGS = {
    "samurai": ["#аниме", "#самурай", "#катана", "#япония", "#ночь"],
    "school": ["#аниме", "#школа", "#повседневность", "#уют", "#вечер"],
    "cyberpunk": ["#аниме", "#неон", "#город", "#киберпанк", "#атмосфера"],
    "fantasy": ["#аниме", "#фэнтези", "#магия", "#миф", "#сказка"],
    "action": ["#аниме", "#битва", "#движение", "#драйв", "#сцена"],
    "melancholy": ["#аниме", "#дождь", "#ночь", "#город", "#настроение"],
    "cozy": ["#аниме", "#уют", "#тепло", "#дом", "#тишина"],
    "anime art": ["#аниме", "#арт", "#иллюстрация", "#эстетика", "#кадр"],
}

def generate_hashtags(topic: str) -> str:
    pool = THEME_TAGS.get(topic, THEME_TAGS["anime art"])
    k = random.randint(4, min(7, len(pool)))
    tags = random.sample(pool, k=k)
    if "#аниме" not in tags:
        tags[0] = "#аниме"
    return " ".join(tags)
