import asyncio
import logging
import random

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from news.news_filter import pick_news
from news.rss_parser import fetch_entries

logger = logging.getLogger(__name__)


class BotScheduler:
    def __init__(self, settings, db, image_fetcher, text_gen, news_summarizer, vk_poster, hashtag_fn):
        self.settings = settings
        self.db = db
        self.image_fetcher = image_fetcher
        self.text_gen = text_gen
        self.news_summarizer = news_summarizer
        self.vk_poster = vk_poster
        self.hashtag_fn = hashtag_fn
        self.scheduler = AsyncIOScheduler(timezone=settings.timezone)

    def start(self):
        self.scheduler.add_job(self._publish_art_post, CronTrigger(hour=10, minute=0))
        self.scheduler.add_job(self._publish_art_post, CronTrigger(hour=17, minute=0))
        self.scheduler.add_job(self._publish_art_post, CronTrigger(hour=0, minute=0))
        self.scheduler.add_job(self._publish_news_post, "interval", minutes=90)
        self.scheduler.start()

    async def _publish_art(self):
        art = await asyncio.to_thread(self.image_fetcher.fetch_art)
        if not art or not art.get("image"):
            logger.warning("Skip art post: image == None")
            return None

        src = art["image"]
        tags_raw = art.get("tags", "")
        downloaded = await asyncio.to_thread(self.image_fetcher.download_image, src)
        if not downloaded:
            logger.warning("Skip art post: download/validation failed")
            return None
        local, checksum, _ = downloaded
        topic = "anime aesthetic"
        logger.info("image url: %s", src)
        if self.db.has_image_checksum(checksum):
            logger.info("Duplicate image checksum, skip")
            return None
        caption = random.choice(self.settings.captions)
        text = f"{caption}\n\n{self.settings.fixed_hashtags}"
        try:
            attachment = self.vk_poster.upload_photo(str(local))
            if not attachment:
                logger.warning("Skip art post: VK upload returned empty attachment")
                return None
            post_id = self.vk_poster.post(text, attachment)
        except Exception:
            logger.exception("VK publish failed, skip this art post")
            return None
        self.db.add_image(src, str(local), topic, checksum)
        self.db.add_post("art", checksum, text, post_id)
        logger.info("Published art post %s", post_id)
        return post_id

    async def _publish_art_post(self):
        await self._publish_art()

    async def publish_test_post_now(self):
        post_id = await self._publish_art()
        if post_id is not None:
            logger.info("Test post published successfully")

    async def _publish_news_post(self):
        if self.db.todays_news_posts() >= self.settings.news_max_per_day:
            return
        entries = fetch_entries()
        entry = pick_news(entries)
        if not entry or self.db.has_news(entry["guid"]):
            return
        text = await self.news_summarizer.summarize(entry["title"], entry["summary"], entry["link"])
        if self.db.has_text(text):
            return
        post_id = self.vk_poster.post(text)
        self._last_post_id = post_id
        self.db.add_news(entry["guid"], entry["title"], entry["link"], entry.get("published"))
        self.db.add_post("news", None, text, post_id)
        logger.info("Published news post %s", post_id)

    async def run_forever(self):
        while True:
            await asyncio.sleep(300)
