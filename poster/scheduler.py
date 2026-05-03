import asyncio
import logging
import random
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from poster.comment_responder import CommentResponder
from poster.retry_utils import retry_async

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
        self.replied_comments: set[int] = set()
        self.comments_enabled = True

    def start(self):
        self.scheduler.add_job(self._publish_art_post, CronTrigger(hour=10, minute=0))
        self.scheduler.add_job(self._publish_art_post, CronTrigger(hour=17, minute=0))
        self.scheduler.add_job(self._publish_art_post, CronTrigger(hour=0, minute=0))
        if self.comments_enabled:
            self.scheduler.add_job(self._process_new_comments, "interval", minutes=1, next_run_time=datetime.now(self.scheduler.timezone))
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
                    logger.warning("upload retry attempt=%s/10", attempt)
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

    async def _process_new_comments(self):
        posts = self.vk_poster.get_recent_posts(count=5)
        for post in posts:
            post_id = int(post.get("id", 0) or 0)
            for item in self.vk_poster.get_post_comments(post_id=post_id, count=20):
                comment_id = int(item.get("id", 0) or 0)
                user_id = int(item.get("from_id", 0) or 0)
                text = (item.get("text") or "").strip()
                if comment_id <= 0 or user_id == 0 or user_id == -abs(self.settings.vk_group_id):
                    continue
                if self.db.has_replied_comment(comment_id) and self.db.comment_reply_attempts(comment_id) >= 2:
                    continue
                if not self.comment_responder.should_reply(text):
                    continue
                reply = self.comment_responder.build_reply(text)
                if not reply:
                    continue
                new_comment_id = self.vk_poster.reply_to_comment(post_id, comment_id, reply)
                if new_comment_id <= 0:
                    self.db.mark_comment_reply_failed(comment_id, user_id)
                    continue
                self.db.add_comment_reply(comment_id, user_id)
                self.comment_responder.mark_replied()
                return

    async def run_forever(self):
        while True:
            await asyncio.sleep(300)
