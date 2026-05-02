from openai import AsyncOpenAI


class NewsSummarizer:
    def __init__(self, api_key: str, model: str):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def summarize(self, title: str, summary: str, link: str) -> str:
        prompt = (
            "Сделай короткий официальный пересказ новости про аниме/мангу на русском (2-4 предложения). "
            "Добавь в конце источник ссылкой."
        )
        res = await self.client.responses.create(
            model=self.model,
            input=[{"role": "system", "content": prompt}, {"role": "user", "content": f"{title}\n\n{summary}\n\n{link}"}],
            max_output_tokens=180,
        )
        return res.output_text.strip()
