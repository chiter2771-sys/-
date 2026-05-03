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

    async def _generate_with_model(self, model: str, prompt: str, topic: str, style: str, tag_context: str) -> str:
        res = await self.client.chat.completions.create(
            model=model,
            messages=[{"role":"system","content":prompt},{"role":"user","content":f"Тема: {topic}. Стиль: {style}. Детали кадра по тегам: {tag_context}."}],
            max_tokens=80,
            timeout=8,
        )
        text = ((res.choices[0].message.content if res.choices else "") or "").strip()
        if not text:
            raise ValueError("empty response")
        return text

    @staticmethod
    def _local_fallback(topic: str, style: str) -> str:
        by_topic = {
            "cozy": ["Теплый свет и спокойный вечер.", "Здесь легко задержаться взглядом."],
            "melancholy": ["После дождя всегда тише.", "Ночной город снова молчит."],
            "action": ["В этом кадре много движения.", "Секунда перед рывком."],
            "fantasy": ["Как будто из старой сказки.", "Немного магии в обычном вечере."],
            "cyberpunk": ["Неон и тишина рядом.", "Город светится, но не спешит."],
        }
        templates = by_topic.get(topic, ["Иногда достаточно просто смотреть.", "Свет в окнах и немного тишины."])
        return random.choice(templates)

    def _tags_to_context(self, tags: str) -> str:
        raw = [t.strip().replace("_", " ") for t in (tags or "").split() if t.strip()]
        stop = {"1girl", "1boy", "solo", "rating:safe", "safe", "anime", "highres"}
        cleaned = [t for t in raw if t.lower() not in stop and len(t) > 2][:8]
        return ", ".join(cleaned) if cleaned else "детали не указаны"

    async def _try_models(self, models: Iterable[str], prompt: str, topic: str, style: str, tag_context: str) -> str:
        for model in models:
            for attempt in range(2):
                try:
                    text = await self._generate_with_model(model, prompt, topic, style, tag_context)
                    low = text.lower()
                    if "теплый свет свечи" in low:
                        raise ValueError("cliche phrase")
                    if any("a" <= ch.lower() <= "z" for ch in text):
                        raise ValueError("non-russian text")
                    return text
                except (RateLimitError, TimeoutError, APIError, ValueError):
                    await asyncio.sleep(0.7 * (attempt + 1))
                    continue
        return self._local_fallback(topic, style)

    async def caption(self, topic: str, tags: str = "") -> str:
        style = random.choice(STYLES)
        tag_context = self._tags_to_context(tags)
        prompt = (
            "Напиши короткую атмосферную подпись для аниме-арта только на русском языке. "
            "Подстрой тон под тему кадра и детали из тегов. "
            "Строго 1 предложение, 8-16 слов. "
            "Без англицизмов, без пафоса, без штампов, без фраз про свечи, магию и волшебство, если этого нет в тегах."
        )
        return await self._try_models((self.model, self.fallback_model), prompt, topic, style, tag_context)
