import random

CAPTIONS = [
    "Иногда один кадр говорит больше слов 🌙",
    "Тёплый свет и тихая атмосфера...",
    "Просто красивый вайб ✨",
    "Есть что-то особенное в таких кадрах.",
    "Спокойствие в чистом виде 🌸",
    "Немного света, немного тишины и идеальный настрой.",
    "Кадр, в котором хочется остаться подольше.",
]


class TextGenerator:
    def __init__(self, api_key: str, model: str, fallback_model: str):
        _ = (api_key, model, fallback_model)

    async def caption(self, topic: str, tags: str = "") -> str:
        _ = (topic, tags)
        return random.choice(CAPTIONS)
