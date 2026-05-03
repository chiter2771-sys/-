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
        res = self._call("wall.post", owner_id=-abs(self.group_id), from_group=1, message=message, attachments=attachment)
        return int(res.get("post_id", 0))

    def get_recent_posts(self, count: int = 5) -> list[dict[str, Any]]:
        return self._call("wall.get", owner_id=-abs(self.group_id), count=count).get("items", [])

    def get_post_comments(self, post_id: int, count: int = 20) -> list[dict[str, Any]]:
        return self._call("wall.getComments", owner_id=-abs(self.group_id), post_id=post_id, count=count).get("items", [])

    def reply_to_comment(self, post_id: int, comment_id: int, message: str) -> int:
        try:
            res = self._call("wall.createComment", owner_id=-abs(self.group_id), post_id=post_id, reply_to_comment=comment_id, from_group=1, message=message)
            return int(res.get("comment_id", 0))
        except RuntimeError:
            try:
                res = self._call("wall.createComment", owner_id=-abs(self.group_id), post_id=post_id, reply_to_comment=comment_id, message=message)
                return int(res.get("comment_id", 0))
            except RuntimeError:
                return 0
