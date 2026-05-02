import random
from asyncio import TimeoutError
from typing import Iterable

from openai import AsyncOpenAI
from openai import APIError, RateLimitError

STYLES = ["уютный", "атмосферный", "anime aesthetic", "немного философский"]


class TextGenerator:
    def __init__(self, api_key: str, model: str, fallback_model: str):
        self.client = AsyncOpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
        self.model = model
        self.fallback_model = fallback_model

    async def _generate_with_model(self, model: str, prompt: str, topic: str, style: str) -> str:
        res = await self.client.responses.create(
            model=model,
            input=f"Тема: {topic}. Стиль: {style}.",
            instructions=prompt,
            max_output_tokens=80,
            timeout=20,
        )
        text = (res.output_text or "").strip()
        if not text:
            raise ValueError("empty response")
        return text

    @staticmethod
    def _local_fallback(topic: str, style: str) -> str:
        templates = [
            "{topic} — кадр, в котором хочется задержаться чуть дольше. {style} настроение и спокойный вайб.",
            "Немного {style} атмосферы: {topic}. Легко, красиво и без лишних слов.",
            "{topic} сегодня звучит особенно тихо и глубоко. Просто сохраняем это {style} состояние.",
        ]
        return random.choice(templates).format(topic=topic, style=style)

    async def _try_models(self, models: Iterable[str], prompt: str, topic: str, style: str) -> str:
        for model in models:
            try:
                return await self._generate_with_model(model, prompt, topic, style)
            except RateLimitError:
                continue
            except TimeoutError:
                continue
            except APIError:
                continue
            except ValueError:
                continue
        return self._local_fallback(topic, style)

    async def caption(self, topic: str) -> str:
        style = random.choice(STYLES)
        prompt = (
            "Напиши короткую подпись (1-2 предложения) для VK-поста с аниме-артом на русском. "
            "Тон естественный, без кринжа и без спама эмодзи."
        )
        return await self._try_models((self.model, self.fallback_model), prompt, topic, style)
