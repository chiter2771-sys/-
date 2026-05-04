import asyncio
import logging
import random

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from poster.retry_utils import retry_async

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
        self.scheduler.start()

    async def _publish_art(self):
        for attempt in range(1, 11):
            item = await self.image_fetcher.fetch_random(blocked_urls=self.db.image_urls())
            if not item:
                logger.warning("image fetch failed attempt=%s/10", attempt)
                await asyncio.sleep(min(20, 0.5 * (2 ** (attempt - 1))))
                continue
            src, local, topic, checksum, tags, source, size = item
            logger.info("image selected source=%s url=%s", source, src)
            if self.db.has_image_checksum(checksum):
                continue
            caption = await self.text_gen.caption(topic, tags)
            logger.info("caption generated")
            tags_out = self.hashtag_fn(topic)
            text = f"{caption.strip()}\n\n{tags_out}" if tags_out else caption.strip()
            try:
                attachment = self.vk_poster.upload_photo(str(local))
                if not attachment:
                    logger.error("vk upload failed attempt=%s/10", attempt)
                    continue
                post_id = self.vk_poster.post(text, attachment)
            except Exception:
                logger.exception("vk api failed")
                continue
            if post_id <= 0:
                continue
            self.db.add_image(src, str(local), topic, checksum)
            self.db.add_post("art", checksum, caption, post_id)
            logger.info("post published post_id=%s", post_id)
            return post_id
        return None

    async def _publish_art_post(self):
        await retry_async(self._publish_art, attempts=1, op_name="publish_art")


    async def publish_test_post_now(self):
        await self._publish_art()

    async def run_forever(self):
        while True:
            await asyncio.sleep(300)
