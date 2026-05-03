import asyncio
import random
from asyncio import TimeoutError
from typing import Iterable

from openai import APIError, AsyncOpenAI, RateLimitError

STYLES = ["спокойный", "ночной", "мечтательный", "уютный"]


class TextGenerator:
    def __init__(self, api_key: str, model: str, fallback_model: str):
        self.client = AsyncOpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
        self.model = model
        self.fallback_model = fallback_model

    async def _generate_with_model(self, model: str, prompt: str, topic: str, style: str, tag_context: str) -> str:
        res = await self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Тема: {topic}. Стиль: {style}. Теги: {tag_context}."},
            ],
            max_tokens=140,
            timeout=10,
        )
        return ((res.choices[0].message.content if res.choices else "") or "").strip()

    @staticmethod
    def _local_fallback(topic: str, style: str) -> str:
        return random.choice([
            "Тёплый свет города и тишина в глазах.\nИногда один кадр говорит за всё 🌙",
            "Лёгкий ветер, мягкий свет и немного мечты.\nЭстетика, в которую хочется вернуться ✨",
        ])

    async def _try_models(self, models: Iterable[str], prompt: str, topic: str, style: str, tag_context: str) -> str:
        for model in models:
            for attempt in range(2):
                try:
                    text = await self._generate_with_model(model, prompt, topic, style, tag_context)
                    if text and not any("a" <= ch.lower() <= "z" for ch in text):
                        return text
                except (RateLimitError, TimeoutError, APIError, ValueError):
                    await asyncio.sleep(0.8 * (attempt + 1))
        return self._local_fallback(topic, style)

    async def caption(self, topic: str, tags: str = "") -> str:
        style = random.choice(STYLES)
        prompt = (
            "Напиши подпись 2-5 строк на русском для anime aesthetic арта. "
            "Без кринжа, без новостного стиля, умеренно emoji, атмосферно."
        )
        return await self._try_models((self.model, self.fallback_model), prompt, topic, style, tags)
