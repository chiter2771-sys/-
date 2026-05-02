import asyncio
import logging
import random
from datetime import datetime

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
        self.scheduler.add_job(self._daily_plan, CronTrigger(hour=0, minute=5))
        self.scheduler.start()

    async def _daily_plan(self):
        jobs = random.randint(self.settings.posts_min_per_day, self.settings.posts_max_per_day)
        for _ in range(jobs):
            h = random.randint(self.settings.posting_start_hour, self.settings.posting_end_hour - 1)
            m = random.randint(0, 59)
            self.scheduler.add_job(self._publish_art_post, "cron", hour=h, minute=m)
        if self.db.todays_news_posts() < self.settings.news_max_per_day:
            self.scheduler.add_job(self._publish_news_post, "cron", hour=random.randint(12, 20), minute=random.randint(0, 59))
        logger.info("Planned %s art jobs for %s", jobs, datetime.now().date())

    async def _publish_art_post(self):
        item = await self.image_fetcher.fetch_random()
        if not item:
            logger.warning("No image fetched")
            return
        src, local, topic, checksum = item
        if self.db.has_image_checksum(checksum):
            return
        caption = await self.text_gen.caption(topic)
        if self.db.has_text(caption):
            caption = f"{caption}\n{random.randint(10, 999)}"
        text = f"{caption}\n\n{self.hashtag_fn(topic)}"
        attachment = self.vk_poster.upload_photo(str(local))
        post_id = self.vk_poster.post(text, attachment)
        self.db.add_image(src, str(local), topic, checksum)
        self.db.add_post("art", checksum, caption, post_id)
        logger.info("Published art post %s", post_id)

    async def _publish_news_post(self):
        entries = fetch_entries()
        entry = pick_news(entries)
        if not entry or self.db.has_news(entry["guid"]):
            return
        text = await self.news_summarizer.summarize(entry["title"], entry["summary"], entry["link"])
        if self.db.has_text(text):
            return
        post_id = self.vk_poster.post(text)
        self.db.add_news(entry["guid"], entry["title"], entry["link"], entry.get("published"))
        self.db.add_post("news", None, text, post_id)
        logger.info("Published news post %s", post_id)

    async def run_forever(self):
        await self._daily_plan()
        while True:
            await asyncio.sleep(300)
