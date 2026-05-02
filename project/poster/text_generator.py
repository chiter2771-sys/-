import random
import asyncio
from asyncio import TimeoutError
from typing import Iterable

from openai import AsyncOpenAI
from openai import APIError, RateLimitError

STYLES = ["anime aesthetic", "internet melancholy", "late night vibes", "спокойный минимализм"]


class TextGenerator:
    def __init__(self, api_key: str, model: str, fallback_model: str):
        self.client = AsyncOpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
        self.model = model
        self.fallback_model = fallback_model

    async def _generate_with_model(self, model: str, prompt: str, topic: str, style: str) -> str:
        res = await self.client.chat.completions.create(
            model=model,
            messages=[{"role":"system","content":prompt},{"role":"user","content":f"Тема: {topic}. Стиль: {style}."}],
            max_tokens=120,
            timeout=20,
        )
        text = ((res.choices[0].message.content if res.choices else "") or "").strip()
        if not text:
            raise ValueError("empty response")
        return text

    @staticmethod
    def _local_fallback(topic: str, style: str) -> str:
        templates = [
            "{topic} — кадр, в котором хочется задержаться чуть дольше. {style} настроение и спокойный вайб.",
            "Немного {style} атмосферы: {topic}. Легко, красиво и без лишних слов.",
            "{topic}. Тихий кадр, который лучше не объяснять — просто оставить здесь.",
        ]
        return random.choice(templates).format(topic=topic, style=style)

    async def _try_models(self, models: Iterable[str], prompt: str, topic: str, style: str) -> str:
        for model in models:
            for attempt in range(3):
                try:
                    return await self._generate_with_model(model, prompt, topic, style)
                except (RateLimitError, TimeoutError, APIError, ValueError):
                    await asyncio.sleep(1.2 * (attempt + 1))
                    continue
        return self._local_fallback(topic, style)

    async def caption(self, topic: str) -> str:
        style = random.choice(STYLES)
        prompt = (
            "Сгенерируй короткую живую подпись для VK-поста с аниме-артом на русском. "
            "Иногда верни пустую строку (без описания). Избегай шаблонов и повторов структуры. "
            "Стиль: спокойный anime aesthetic / internet melancholy / late night vibes. Без кринжа."
        )
        return await self._try_models((self.model, self.fallback_model), prompt, topic, style)
