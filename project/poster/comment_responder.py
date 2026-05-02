import random
from datetime import datetime, timedelta, timezone

COMMENT_REPLY_PROMPT = """
Ты — живой админ аниме-сообщества VK.

Отвечай естественно, кратко и по-человечески.
Без официоза.
Без англицизмов.
Без кринжа.
Без повторов.

Стиль:
— спокойный
— дружелюбный
— осмысленный
— как настоящий человек

Не пиши одинаковые ответы.

Комментарий пользователя:
"{comment}"

Ответ:
"""

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
        low = text.lower().strip()
        if "где постер" in low or "где арт" in low:
            return random.choice([
                "Источник снова упал, уже исправили.",
                "Да, заметили. Сейчас уже починили.",
            ])
        if any(x in low for x in ("класс", "красиво", "топ", "шик", "люблю")):
            return random.choice(["Спасибо, очень приятно.", "Рады, что понравилось.", "Очень ценно, спасибо."])
        if "?" in low:
            return random.choice(["Есть такое.", "Хороший вопрос.", "Справедливое замечание.", "Под этот арт идеально."])
        if any(x in low for x in ("грустно", "плохо", "тяжело")):
            return random.choice(["Понимаем. Держись.", "Пусть этот кадр чуть поддержит.", "Обнимаем мысленно."])
        if len(low) > 180:
            return random.choice(["Спасибо, что так подробно написал.", "Хорошо сказал, согласны."])
        return random.choice(["Тоже зацепило.", "Согласны.", "Есть в этом настроение."])

    def can_reply_now(self) -> bool:
        if self.last_reply_at is None:
            return True
        return datetime.now(timezone.utc) - self.last_reply_at >= self.cooldown

    def mark_replied(self):
        self.last_reply_at = datetime.now(timezone.utc)
