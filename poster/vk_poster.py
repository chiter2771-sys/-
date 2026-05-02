import logging
from pathlib import Path
from typing import Any

import requests


logger = logging.getLogger(__name__)


class VKPoster:
    def __init__(self, token: str, group_id: int):
        self.token = token
        self.group_id = group_id
        self.api = "https://api.vk.com/method"
        self.v = "5.199"
        self.session = requests.Session()

    def _call(self, method: str, **params: Any) -> dict[str, Any]:
        payload = {"access_token": self.token, "v": self.v, **params}
        try:
            response = self.session.post(f"{self.api}/{method}", data=payload, timeout=30)
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.exception("VK transport error on %s", method)
            raise RuntimeError(f"VK transport error on {method}: {exc}") from exc

        try:
            data = response.json()
        except ValueError as exc:
            logger.error("VK returned non-JSON response on %s: %s", method, response.text[:500])
            raise RuntimeError(f"VK returned invalid JSON on {method}") from exc

        if "error" in data:
            err = data["error"]
            logger.error("VK API error on %s: %s", method, err)
            raise RuntimeError(f"VK API error on {method}: {err}")

        if "response" not in data:
            logger.error("VK response missing 'response' on %s: %s", method, data)
            raise RuntimeError(f"VK malformed response on {method}: missing response")
        return data["response"]

    def upload_photo(self, file_path: str) -> str:
        if not Path(file_path).exists():
            raise RuntimeError(f"Image file not found: {file_path}")

        server = self._call("photos.getWallUploadServer", group_id=self.group_id)
        upload_url = server.get("upload_url")
        if not upload_url:
            raise RuntimeError("VK did not return upload_url")

        try:
            with open(file_path, "rb") as f:
                upload_response = self.session.post(upload_url, files={"photo": f}, timeout=60)
                upload_response.raise_for_status()
                upload = upload_response.json()
        except requests.RequestException as exc:
            logger.exception("VK upload transport error")
            raise RuntimeError(f"VK upload transport error: {exc}") from exc
        except ValueError as exc:
            logger.error("VK upload returned non-JSON response")
            raise RuntimeError("VK upload returned invalid JSON") from exc

        if upload.get("error"):
            logger.error("VK upload API-level error: %s", upload)
            raise RuntimeError(f"VK upload failed: {upload}")
        if not all(k in upload for k in ("photo", "server", "hash")):
            logger.error("VK upload missing expected fields: %s", upload)
            raise RuntimeError(f"VK upload malformed response: {upload}")

        saved = self._call(
            "photos.saveWallPhoto",
            group_id=self.group_id,
            photo=upload["photo"],
            server=upload["server"],
            hash=upload["hash"],
        )
        if not saved:
            raise RuntimeError("VK saveWallPhoto returned empty response")
        photo = saved[0]
        if "owner_id" not in photo or "id" not in photo:
            raise RuntimeError(f"VK saveWallPhoto malformed response: {photo}")
        logger.info("VK photo uploaded: owner_id=%s id=%s", photo["owner_id"], photo["id"])
        return f"photo{photo['owner_id']}_{photo['id']}"

    def post(self, message: str, attachment: str | None = None) -> int:
        if not message or not message.strip():
            raise RuntimeError("VK post message is empty")

        res = self._call(
            "wall.post",
            owner_id=-abs(self.group_id),
            from_group=1,
            message=message,
            attachments=attachment,
        )
        if "post_id" not in res:
            raise RuntimeError(f"VK wall.post malformed response: {res}")
        logger.info("VK wall.post succeeded: %s", res)
        return int(res["post_id"])
