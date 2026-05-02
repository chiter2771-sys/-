import random

from openai import AsyncOpenAI

STYLES = ["уютный", "атмосферный", "anime aesthetic", "немного философский"]


class TextGenerator:
    def __init__(self, api_key: str, model: str):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def caption(self, topic: str) -> str:
        style = random.choice(STYLES)
        prompt = (
            "Напиши короткую подпись (1-2 предложения) для VK-поста с аниме-артом на русском. "
            "Тон естественный, без кринжа и без спама эмодзи."
        )
        res = await self.client.responses.create(
            model=self.model,
            input=f"Тема: {topic}. Стиль: {style}.",
            instructions=prompt,
            max_output_tokens=80,
        )
        return res.output_text.strip()
