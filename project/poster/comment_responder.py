import random
from datetime import datetime, timedelta, timezone


class CommentResponder:
    def __init__(self):
        self.last_reply_at: datetime | None = None
        self.cooldown = timedelta(minutes=15)

    def should_reply(self, text: str) -> bool:
        low = (text or "").lower().strip()
        if not low or len(low) < 2:
            return False
        if any(x in low for x in ("http://", "https://", "подпишись", "реклама", "скам")):
            return False
        return True

    def build_reply(self, text: str) -> str | None:
        low = text.lower()
        if "где постер" in low or "где арт" in low:
            return "Источник снова умер, бот пост без арта кинул. Уже поправили."
        if any(x in low for x in ("класс", "красиво", "топ", "шик", "люблю")):
            return random.choice(["Спасибо, очень приятно это читать.", "Рады, что откликнулось 💬".replace("💬", "")])
        if "?" in text:
            return "Хороший вопрос. Проверяем источник и поправим пост, если нужно."
        if any(x in low for x in ("грустно", "плохо", "тяжело")):
            return "Понимаю тебя. Надеюсь, этот пост хотя бы немного поддержит сегодня."
        if len(low) > 180:
            return "Спасибо за развёрнутый комментарий. Ценим, что делишься мыслями."
        return None

    def can_reply_now(self) -> bool:
        if self.last_reply_at is None:
            return True
        return datetime.now(timezone.utc) - self.last_reply_at >= self.cooldown

    def mark_replied(self):
        self.last_reply_at = datetime.now(timezone.utc)
