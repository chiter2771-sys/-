import logging
import mimetypes
from pathlib import Path
from typing import Any

import requests

from poster.image_validator import validate_image_file

logger = logging.getLogger(__name__)


class VKPoster:
    def __init__(self, token: str, group_id: int):
        self.token = token
        self.group_id = group_id
        self.api = "https://api.vk.com/method"
        self.v = "5.199"
        self.session = requests.Session()
        self.allowed_mime_types = {"image/jpeg", "image/png", "image/webp"}

    def check_access(self) -> tuple[bool, str]:
        try:
            self._call("groups.getById", group_id=self.group_id)
            self._call("wall.get", owner_id=-abs(self.group_id), count=1)
            return True, "ok"
        except RuntimeError as exc:
            return False, str(exc)

    def _call(self, method: str, **params: Any) -> dict[str, Any]:
        payload = {"access_token": self.token, "v": self.v, **params}
        response = self.session.post(f"{self.api}/{method}", data=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            raise RuntimeError(f"VK API error on {method}: {data['error']}")
        if "response" not in data:
            raise RuntimeError(f"VK malformed response on {method}")
        return data["response"]

    def upload_photo(self, file_path: str) -> str | None:
        path = Path(file_path)
        valid, reason, _ = validate_image_file(path, min_width=600, min_height=600)
        if not valid:
            logger.warning("invalid image for upload reason=%s file=%s", reason, file_path)
            return None
        server = self._call("photos.getWallUploadServer", group_id=self.group_id)
        upload_url = server.get("upload_url")
        if not upload_url:
            return None
        mime_type, _ = mimetypes.guess_type(path.name)
        if mime_type not in self.allowed_mime_types:
            return None
        with open(path, "rb") as f:
            upload = self.session.post(upload_url, files={"photo": f}, timeout=60).json()
        if not upload.get("photo") or not upload.get("server") or not upload.get("hash"):
            logger.error("VK upload malformed response: %s", upload)
            return None
        saved = self._call("photos.saveWallPhoto", group_id=self.group_id, photo=upload["photo"], server=upload["server"], hash=upload["hash"])
        if not saved:
            return None
        photo = saved[0]
        return f"photo{photo['owner_id']}_{photo['id']}"

    def post(self, message: str, attachment: str | None = None) -> int:
        if not attachment:
            logger.error("empty attachment, post aborted")
            return 0
        res = self._call("wall.post", owner_id=-abs(self.group_id), from_group=1, message=message, attachments=attachment)
        return int(res.get("post_id", 0))
