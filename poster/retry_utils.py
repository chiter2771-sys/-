import asyncio
import logging
from typing import Awaitable, Callable, TypeVar

T = TypeVar("T")
logger = logging.getLogger(__name__)


async def retry_async(
    fn: Callable[[], Awaitable[T]],
    attempts: int = 10,
    base_delay: float = 0.5,
    max_delay: float = 20.0,
    op_name: str = "operation",
) -> T:
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return await fn()
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt >= attempts:
                break
            delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
            logger.warning("retry %s attempt=%s/%s delay=%.2fs error=%s", op_name, attempt, attempts, delay, exc)
            await asyncio.sleep(delay)
    raise RuntimeError(f"{op_name} failed after {attempts} attempts") from last_exc
