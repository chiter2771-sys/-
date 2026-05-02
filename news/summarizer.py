from asyncio import TimeoutError
from typing import Iterable

from openai import AsyncOpenAI
from openai import APIError, RateLimitError


class NewsSummarizer:
    def __init__(self, api_key: str, model: str, fallback_model: str):
        self.client = AsyncOpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
        self.model = model
        self.fallback_model = fallback_model

    async def _summarize_with_model(self, model: str, title: str, summary: str, link: str, prompt: str) -> str:
        res = await self.client.responses.create(
            model=model,
            input=[{"role": "system", "content": prompt}, {"role": "user", "content": f"{title}\n\n{summary}\n\n{link}"}],
            max_output_tokens=180,
            timeout=25,
        )
        text = (res.output_text or "").strip()
        if not text:
            raise ValueError("empty response")
        return text

    @staticmethod
    def _local_fallback(title: str, link: str) -> str:
        return f"Кратко: {title}. Подробности и первоисточник: {link}"

    async def _try_models(self, models: Iterable[str], title: str, summary: str, link: str, prompt: str) -> str:
        for model in models:
            try:
                return await self._summarize_with_model(model, title, summary, link, prompt)
            except RateLimitError:
                continue
            except TimeoutError:
                continue
            except APIError:
                continue
            except ValueError:
                continue
        return self._local_fallback(title, link)

    async def summarize(self, title: str, summary: str, link: str) -> str:
        prompt = (
            "Сделай короткий официальный пересказ новости про аниме/мангу на русском (2-4 предложения). "
            "Добавь в конце источник ссылкой."
        )
        return await self._try_models((self.model, self.fallback_model), title, summary, link, prompt)
