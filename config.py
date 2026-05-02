import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class Settings:
    vk_token: str
    vk_group_id: int
    openrouter_api_key: str
    openrouter_model: str
    openrouter_fallback_model: str
    db_path: str
    storage_path: Path
    timezone: str
    posting_start_hour: int
    posting_end_hour: int
    posts_min_per_day: int
    posts_max_per_day: int
    news_max_per_day: int
    min_image_width: int
    min_image_height: int
    cleanup_keep_files: int
    test_post_now: bool


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


def load_settings() -> Settings:
    storage = Path(os.getenv("STORAGE_PATH", "storage"))
    storage.mkdir(parents=True, exist_ok=True)
    return Settings(
        vk_token=_require("VK_TOKEN"),
        vk_group_id=int(_require("VK_GROUP_ID")),
        openrouter_api_key=_require("OPENROUTER_API_KEY"),
        openrouter_model=os.getenv("OPENROUTER_MODEL", "openai/gpt-4.1-mini"),
        openrouter_fallback_model=os.getenv("OPENROUTER_FALLBACK_MODEL", "meta-llama/llama-3.3-70b-instruct:free"),
        db_path=os.getenv("DB_PATH", "database/bot.db"),
        storage_path=storage,
        timezone=os.getenv("TIMEZONE", "Europe/Moscow"),
        posting_start_hour=int(os.getenv("POSTING_START_HOUR", "9")),
        posting_end_hour=int(os.getenv("POSTING_END_HOUR", "23")),
        posts_min_per_day=int(os.getenv("POSTS_MIN_PER_DAY", "2")),
        posts_max_per_day=int(os.getenv("POSTS_MAX_PER_DAY", "5")),
        news_max_per_day=int(os.getenv("NEWS_MAX_PER_DAY", "2")),
        min_image_width=int(os.getenv("MIN_IMAGE_WIDTH", "1000")),
        min_image_height=int(os.getenv("MIN_IMAGE_HEIGHT", "1000")),
        cleanup_keep_files=int(os.getenv("CLEANUP_KEEP_FILES", "150")),
        test_post_now=os.getenv("TEST_POST_NOW", "false").lower() == "true",
    )
