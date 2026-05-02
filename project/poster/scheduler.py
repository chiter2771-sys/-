import asyncio
import logging
import random

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from poster.comment_responder import CommentResponder

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
        self.comment_responder = CommentResponder()

    def start(self):
        self.scheduler.add_job(self._publish_art_post, CronTrigger(hour=10, minute=0))
        self.scheduler.add_job(self._publish_art_post, CronTrigger(hour=17, minute=0))
        self.scheduler.add_job(self._publish_art_post, CronTrigger(hour=0, minute=0))
        self.scheduler.add_job(self._publish_news_post, "interval", minutes=90)
        self.scheduler.add_job(self._process_new_comments, "interval", minutes=5)
        self.scheduler.start()

    async def _publish_art(self):
        item = await self.image_fetcher.fetch_random(blocked_urls=self.db.image_urls())
        if not item:
            logger.warning("Skip art post: no valid image fetched")
            return None
        src, local, topic, checksum = item
        logger.info("image url: %s", src)
        if self.db.has_image_checksum(checksum):
            logger.info("Duplicate image checksum, skip")
            return None
        caption = await self.text_gen.caption(topic)
        logger.info("generated caption: %s", caption)
        if self.db.has_text(caption):
            caption = f"{caption}\n{random.randint(10, 999)}"
        tags = self.hashtag_fn(topic)
        text = caption.strip()
        if tags:
            text = f"{text}\n\n{tags}" if text else tags
        try:
            attachment = self.vk_poster.upload_photo(str(local))
            post_id = self.vk_poster.post(text, attachment)
        except Exception:
            logger.exception("VK publish failed, skip this art post")
            return None
        self.db.add_image(src, str(local), topic, checksum)
        self.db.add_post("art", checksum, caption, post_id)
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

    async def _process_new_comments(self):
        try:
            if not self.comment_responder.can_reply_now():
                return
            posts = self.vk_poster.get_recent_posts(count=5)
            for post in posts:
                post_id = int(post.get("id", 0) or 0)
                if post_id <= 0:
                    continue
                for item in self.vk_poster.get_post_comments(post_id=post_id, count=20):
                    comment_id = int(item.get("id", 0) or 0)
                    user_id = int(item.get("from_id", 0) or 0)
                    text = (item.get("text") or "").strip()
                    logger.info("Found comment id=%s post_id=%s", comment_id, post_id)
                    if comment_id <= 0 or user_id <= 0:
                        continue
                    if self.db.has_replied_comment(comment_id):
                        continue
                    if not self.comment_responder.should_reply(text):
                        logger.info("Comment filtered id=%s", comment_id)
                        continue
                    reply = self.comment_responder.build_reply(text)
                    if not reply:
                        logger.info("No reply generated id=%s", comment_id)
                        continue
                    logger.info("Reply generated id=%s: %s", comment_id, reply)
                    self.vk_poster.reply_to_comment(comment_id, reply)
                    self.db.add_comment_reply(comment_id, user_id)
                    self.comment_responder.mark_replied()
                    logger.info("Replied to comment_id=%s post_id=%s", comment_id, post_id)
                    return
        except Exception:
            logger.exception("Comment polling loop failed")

    async def run_forever(self):
        while True:
            await asyncio.sleep(300)
