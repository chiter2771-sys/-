import random
import asyncio
from asyncio import TimeoutError
from typing import Iterable

from openai import AsyncOpenAI
from openai import APIError, RateLimitError

STYLES = ["спокойный", "ночной", "меланхоличный", "уютный"]


class TextGenerator:
    def __init__(self, api_key: str, model: str, fallback_model: str):
        self.client = AsyncOpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
        self.model = model
        self.fallback_model = fallback_model

    async def _generate_with_model(self, model: str, prompt: str, topic: str, style: str) -> str:
        res = await self.client.chat.completions.create(
            model=model,
            messages=[{"role":"system","content":prompt},{"role":"user","content":f"Тема: {topic}. Стиль: {style}."}],
            max_tokens=80,
            timeout=8,
        )
        text = ((res.choices[0].message.content if res.choices else "") or "").strip()
        if not text:
            raise ValueError("empty response")
        return text

    @staticmethod
    def _local_fallback(topic: str, style: str) -> str:
        templates = [
            "Ночной свет и тишина.",
            "Город уже спит.",
            "Такие кадры хочется сохранить.",
            "Тишина после дождя.",
            "Сегодня что-то особенно спокойно.",
        ]
        return random.choice(templates)

    async def _try_models(self, models: Iterable[str], prompt: str, topic: str, style: str) -> str:
        for model in models:
            for attempt in range(2):
                try:
                    return await self._generate_with_model(model, prompt, topic, style)
                except (RateLimitError, TimeoutError, APIError, ValueError):
                    await asyncio.sleep(0.7 * (attempt + 1))
                    continue
        return self._local_fallback(topic, style)

    async def caption(self, topic: str) -> str:
        style = random.choice(STYLES)
        prompt = (
            "Напиши короткую подпись для поста с аниме-артом только на русском языке. "
            "Без английских слов, без пафоса, без длинных фраз. Иногда верни пустую строку."
        )
        return await self._try_models((self.model, self.fallback_model), prompt, topic, style)
