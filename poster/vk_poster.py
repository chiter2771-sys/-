import logging
import mimetypes
from pathlib import Path
from typing import Any

import requests
from PIL import Image


logger = logging.getLogger(__name__)


class VKPoster:
    def __init__(self, token: str, group_id: int):
        self.token = token
        self.group_id = group_id
        self.api = "https://api.vk.com/method"
        self.v = "5.199"
        self.session = requests.Session()
        self.allowed_mime_types = {"image/jpeg", "image/png", "image/webp"}

    def _prepare_image_for_upload(self, file_path: str, max_size: int, quality: int) -> tuple[Path, dict[str, Any]] | None:
        src = Path(file_path)
        if not src.exists():
            logger.error("Skip upload: image file not found: %s", file_path)
            return None
        size_bytes = src.stat().st_size
        if size_bytes <= 0:
            logger.error("Skip upload: image file is empty: %s", file_path)
            return None
        mime_type, _ = mimetypes.guess_type(src.name)
        if mime_type not in self.allowed_mime_types:
            logger.error("Skip upload: unsupported MIME type %s for %s", mime_type, file_path)
            return None
        try:
            with Image.open(src) as img:
                original_size = img.size
                image_format = img.format
                img = img.convert("RGB")
                img.thumbnail((max_size, max_size))
                out_path = src.with_name(f"{src.stem}_vk_{max_size}_{quality}.jpg")
                img.save(out_path, "JPEG", quality=quality, optimize=True)
                final_size = img.size
        except Exception:
            logger.exception("Skip upload: failed to normalize image: %s", file_path)
            return None

        meta = {
            "source_path": str(src),
            "prepared_path": str(out_path),
            "source_size_bytes": size_bytes,
            "prepared_size_bytes": out_path.stat().st_size if out_path.exists() else 0,
            "mime_type": mime_type,
            "source_extension": src.suffix.lower(),
            "source_dimensions": original_size,
            "prepared_dimensions": final_size,
            "source_format": image_format,
        }
        return out_path, meta

    def _upload_to_server(self, upload_url: str, path: Path, meta: dict[str, Any]) -> tuple[dict[str, Any] | None, int | None]:
        try:
            with open(path, "rb") as f:
                upload_response = self.session.post(upload_url, files={"photo": f}, timeout=60)
            status_code = upload_response.status_code
            upload_response.raise_for_status()
            logger.info("VK raw upload response: %s", upload_response.text[:1000])
            return upload_response.json(), status_code
        except ValueError:
            logger.error("VK upload returned invalid JSON. status=%s url=%s meta=%s body=%s", status_code if 'status_code' in locals() else None, upload_url, meta, upload_response.text[:500] if 'upload_response' in locals() else "")
            return None, status_code if 'status_code' in locals() else None
        except requests.RequestException:
            logger.exception("VK upload transport error. url=%s meta=%s", upload_url, meta)
            return None, None

    def _call(self, method: str, **params: Any) -> dict[str, Any]:
        payload = {"access_token": self.token, "v": self.v, **params}
        for attempt in range(3):
            try:
                response = self.session.post(f"{self.api}/{method}", data=payload, timeout=30)
                response.raise_for_status()
                break
            except requests.RequestException as exc:
                if attempt == 2:
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

    def upload_photo(self, file_path: str) -> str | None:
        server = self._call("photos.getWallUploadServer", group_id=self.group_id)
        upload_url = server.get("upload_url")
        if not upload_url:
            logger.error("VK did not return upload_url")
            return None

        primary = self._prepare_image_for_upload(file_path, max_size=2560, quality=95)
        if not primary:
            return None
        primary_path, primary_meta = primary
        upload, status_code = self._upload_to_server(upload_url, primary_path, primary_meta)
        if not upload:
            return None

        if upload.get("error"):
            logger.error("VK upload API-level error: %s", upload)
            return None
        if not all(k in upload for k in ("photo", "server", "hash")) or not upload.get("photo"):
            logger.error("VK upload malformed response. payload=%s file_size=%s mime=%s ext=%s dims=%s upload_url=%s status=%s", upload, primary_meta["prepared_size_bytes"], primary_meta["mime_type"], primary_meta["source_extension"], primary_meta["prepared_dimensions"], upload_url, status_code)
            fallback = self._prepare_image_for_upload(file_path, max_size=1280, quality=85)
            if not fallback:
                return None
            fallback_path, fallback_meta = fallback
            upload, status_code = self._upload_to_server(upload_url, fallback_path, fallback_meta)
            if not upload:
                return None
            if not all(k in upload for k in ("photo", "server", "hash")) or not upload.get("photo"):
                logger.error("VK fallback upload malformed response. payload=%s file_size=%s mime=%s ext=%s dims=%s upload_url=%s status=%s", upload, fallback_meta["prepared_size_bytes"], fallback_meta["mime_type"], fallback_meta["source_extension"], fallback_meta["prepared_dimensions"], upload_url, status_code)
                return None

        try:
            saved = self._call(
                "photos.saveWallPhoto",
                group_id=self.group_id,
                photo=upload["photo"],
                server=upload["server"],
                hash=upload["hash"],
            )
        except RuntimeError:
            logger.exception("VK saveWallPhoto failed")
            return None
        if not saved:
            logger.error("VK saveWallPhoto returned empty response")
            return None
        photo = saved[0]
        if "owner_id" not in photo or "id" not in photo:
            logger.error("VK saveWallPhoto malformed response: %s", photo)
            return None
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

    def get_recent_posts(self, count: int = 5) -> list[dict[str, Any]]:
        res = self._call("wall.get", owner_id=-abs(self.group_id), count=count)
        return res.get("items", []) if isinstance(res, dict) else []

    def get_post_comments(self, post_id: int, count: int = 20) -> list[dict[str, Any]]:
        res = self._call(
            "wall.getComments",
            owner_id=-abs(self.group_id),
            post_id=post_id,
            need_likes=0,
            sort="desc",
            count=count,
            preview_length=0,
            extended=0,
        )
        return res.get("items", []) if isinstance(res, dict) else []

    def reply_to_comment(self, post_id: int, comment_id: int, message: str) -> int:
        try:
            res = self._call(
                "wall.createComment",
                owner_id=-abs(self.group_id),
                post_id=post_id,
                reply_to_comment=comment_id,
                from_group=1,
                message=message,
            )
        except RuntimeError:
            logger.exception("VK comment reply failed post_id=%s comment_id=%s", post_id, comment_id)
            return 0
        return int(res.get("comment_id", 0))
