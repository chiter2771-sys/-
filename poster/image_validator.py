import imghdr
import logging
from pathlib import Path

from PIL import Image

logger = logging.getLogger(__name__)


def validate_image_file(path: Path, min_width: int = 1200, min_height: int = 900) -> tuple[bool, str, tuple[int, int] | None]:
    if not path.exists():
        return False, "file_missing", None
    if path.stat().st_size <= 0:
        return False, "empty_file", None
    if imghdr.what(path) is None:
        return False, "not_image", None
    try:
        with Image.open(path) as img:
            img.verify()
        with Image.open(path) as img:
            w, h = img.size
    except Exception:  # noqa: BLE001
        logger.warning("invalid image pil_open_failed path=%s", path)
        return False, "pil_open_failed", None
    if w < min_width or h < min_height:
        return False, "low_resolution", (w, h)
    return True, "ok", (w, h)
