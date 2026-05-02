import random


TOPIC_TAGS = {
    "anime scenery": ["#анимепейзаж", "#scenery"],
    "sakura": ["#sakura", "#веснаваниме"],
    "rainy night": ["#rainynight", "#ночнойдождь"],
    "cyberpunk anime": ["#cyberpunkanime", "#неоновыйгород"],
}


def generate_hashtags(topic: str) -> str:
    tags = TOPIC_TAGS.get(topic, [])
    if not tags:
        return ""
    # 0-2 релевантных хештега, без generic шума
    count = random.choice((0, 1, 2))
    if count == 0:
        return ""
    return " ".join(tags[:count])
