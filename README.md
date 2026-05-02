# AI VK Auto-Content Bot

Автономный бот для VK-сообщества: постит аниме-арты/эстетику, иногда публикует краткие аниме-новости, избегает дублей и работает по расписанию.

## Возможности
- 2–5 арт-постов в день со случайным временем (в дневном окне).
- Редкие новости (до 1–2 раз в день) из RSS (ANN, MAL, Crunchyroll).
- Генерация подписей и кратких news-summary через OpenAI.
- Авто-хэштеги (4–8 шт.).
- Антидубли по checksum изображений и тексту.
- SQLite-история постов/новостей/картинок.
- Fallback по источникам изображений (Safebooru/Konachan).
- Автоочистка кеша `storage/`.

## Структура
См. дерево проекта в задаче; реализовано полностью в этом репозитории.

## Установка
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# заполните .env
python main.py
```

## ENV
Обязательные:
- `VK_TOKEN`
- `VK_GROUP_ID`
- `OPENAI_API_KEY`

Дополнительные:
- `OPENAI_MODEL` (по умолчанию `gpt-4.1-mini`)
- `TIMEZONE`
- `POSTING_START_HOUR`, `POSTING_END_HOUR`
- `POSTS_MIN_PER_DAY`, `POSTS_MAX_PER_DAY`
- `NEWS_MAX_PER_DAY`
- `MIN_IMAGE_WIDTH`, `MIN_IMAGE_HEIGHT`
- `CLEANUP_KEEP_FILES`

## Запуск на Railway
1. Загрузите репозиторий в GitHub.
2. Создайте проект в Railway и подключите репозиторий.
3. Добавьте ENV-переменные из `.env.example`.
4. Убедитесь, что используется `Procfile` (`worker: python main.py`).
5. Deploy.

## Важно
- Бот **не генерирует изображения ИИ**.
- Для стабильности VK API нужен токен сообщества с правами wall/photos.
- Рекомендуется запускать в режиме Worker (без HTTP сервера).
