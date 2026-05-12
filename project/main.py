import asyncio
import logging
from pathlib import Path

from dotenv import load_dotenv

from config import load_settings
from database.db import Database
from news.summarizer import NewsSummarizer
from poster.hashtags import generate_hashtags
from poster.image_fetcher import ImageFetcher
from poster.scheduler import BotScheduler
from poster.text_generator import TextGenerator
from poster.vk_poster import VKPoster


def setup_logging():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def cleanup_storage(storage: Path, keep: int):
    files = sorted([p for p in storage.glob("*.jpg") if p.is_file()], key=lambda p: p.stat().st_mtime, reverse=True)
    for stale in files[keep:]:
        stale.unlink(missing_ok=True)


async def main():
    load_dotenv()
    setup_logging()
    settings = load_settings()
    db = Database(settings.db_path)
    cleanup_storage(settings.storage_path, settings.cleanup_keep_files)

    # Startup connectivity check for image sources (does not stop scheduler)
    try:
        probe = await ImageFetcher(settings.storage_path, settings.min_image_width, settings.min_image_height, settings.pixiv_refresh_token).fetch_random()
        if probe:
            image_url, local_path, _, _, _, _, _ = probe
            logging.info("Startup image fetch URL: %s", image_url)
            logging.info("Startup image download path: %s", local_path)
            logging.info("Image fetched successfully")
        else:
            logging.error("Startup image probe failed: no image fetched")
    except Exception:
        logging.exception("Startup image probe failed with exception")

    scheduler = BotScheduler(
        settings=settings,
        db=db,
        image_fetcher=ImageFetcher(settings.storage_path, settings.min_image_width, settings.min_image_height, settings.pixiv_refresh_token),
        text_gen=TextGenerator(settings.openrouter_api_key, settings.openrouter_model, settings.openrouter_fallback_model),
        news_summarizer=NewsSummarizer(settings.openrouter_api_key, settings.openrouter_model, settings.openrouter_fallback_model),
        vk_poster=VKPoster(settings.vk_token, settings.vk_group_id),
        hashtag_fn=generate_hashtags,
    )
    if settings.test_post_now:
        try:
            await scheduler.publish_test_post_now()
        except Exception:
            logging.exception("Test post failed")
    scheduler.start()
    await scheduler.run_forever()


if __name__ == "__main__":
    asyncio.run(main())
