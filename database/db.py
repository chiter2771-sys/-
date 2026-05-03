import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone


class Database:
    def __init__(self, path: str):
        self.path = path
        self._init()

    @contextmanager
    def conn(self):
        c = sqlite3.connect(self.path)
        c.row_factory = sqlite3.Row
        try:
            yield c
            c.commit()
        finally:
            c.close()

    def _init(self):
        with self.conn() as c:
            c.executescript(
                """
                CREATE TABLE IF NOT EXISTS images(
                    id INTEGER PRIMARY KEY,
                    source_url TEXT UNIQUE,
                    local_path TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    checksum TEXT UNIQUE NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS posts(
                    id INTEGER PRIMARY KEY,
                    post_type TEXT NOT NULL,
                    image_checksum TEXT,
                    text TEXT UNIQUE NOT NULL,
                    vk_post_id INTEGER,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS news(
                    id INTEGER PRIMARY KEY,
                    guid TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    link TEXT NOT NULL,
                    published_at TEXT
                );
                CREATE TABLE IF NOT EXISTS comment_replies(
                    id INTEGER PRIMARY KEY,
                    comment_id INTEGER UNIQUE NOT NULL,
                    user_id INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'ok',
                    attempts INTEGER NOT NULL DEFAULT 1,
                    replied_at TEXT NOT NULL
                );
                """
            )

    def has_image_checksum(self, checksum: str) -> bool:
        with self.conn() as c:
            row = c.execute("SELECT 1 FROM images WHERE checksum=?", (checksum,)).fetchone()
            return row is not None

    def image_urls(self, limit: int = 5000) -> set[str]:
        with self.conn() as c:
            rows = c.execute("SELECT source_url FROM images ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            return {r[0] for r in rows if r[0]}

    def has_text(self, text: str) -> bool:
        with self.conn() as c:
            row = c.execute("SELECT 1 FROM posts WHERE text=?", (text,)).fetchone()
            return row is not None

    def add_image(self, source_url: str, local_path: str, topic: str, checksum: str):
        with self.conn() as c:
            c.execute(
                "INSERT OR IGNORE INTO images(source_url,local_path,topic,checksum,created_at) VALUES(?,?,?,?,?)",
                (source_url, local_path, topic, checksum, datetime.now(timezone.utc).isoformat()),
            )

    def add_post(self, post_type: str, image_checksum: str | None, text: str, vk_post_id: int):
        with self.conn() as c:
            c.execute(
                "INSERT OR IGNORE INTO posts(post_type,image_checksum,text,vk_post_id,created_at) VALUES(?,?,?,?,?)",
                (post_type, image_checksum, text, vk_post_id, datetime.now(timezone.utc).isoformat()),
            )

    def add_news(self, guid: str, title: str, link: str, published: str | None):
        with self.conn() as c:
            c.execute(
                "INSERT OR IGNORE INTO news(guid,title,link,published_at) VALUES(?,?,?,?)",
                (guid, title, link, published),
            )

    def has_news(self, guid: str) -> bool:
        with self.conn() as c:
            return c.execute("SELECT 1 FROM news WHERE guid=?", (guid,)).fetchone() is not None

    def todays_news_posts(self) -> int:
        date = datetime.now(timezone.utc).date().isoformat()
        with self.conn() as c:
            row = c.execute("SELECT count(1) as cnt FROM posts WHERE post_type='news' AND substr(created_at,1,10)=?", (date,)).fetchone()
            return int(row["cnt"]) if row else 0

    def has_replied_comment(self, comment_id: int) -> bool:
        with self.conn() as c:
            return c.execute("SELECT 1 FROM comment_replies WHERE comment_id=?", (comment_id,)).fetchone() is not None

    def add_comment_reply(self, comment_id: int, user_id: int):
        with self.conn() as c:
            c.execute(
                "INSERT OR IGNORE INTO comment_replies(comment_id,user_id,status,attempts,replied_at) VALUES(?,?,?,?,?)",
                (comment_id, user_id, "ok", 1, datetime.now(timezone.utc).isoformat()),
            )


    def comment_reply_attempts(self, comment_id: int) -> int:
        with self.conn() as c:
            row = c.execute("SELECT attempts FROM comment_replies WHERE comment_id=?", (comment_id,)).fetchone()
            return int(row[0]) if row else 0

    def mark_comment_reply_failed(self, comment_id: int, user_id: int):
        with self.conn() as c:
            c.execute(
                "INSERT INTO comment_replies(comment_id,user_id,status,attempts,replied_at) VALUES(?,?,?,?,?) "
                "ON CONFLICT(comment_id) DO UPDATE SET attempts=attempts+1,status='failed',replied_at=excluded.replied_at",
                (comment_id, user_id, 'failed', 1, datetime.now(timezone.utc).isoformat()),
            )
