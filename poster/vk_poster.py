import logging

import requests


logger = logging.getLogger(__name__)


class VKPoster:
    def __init__(self, token: str, group_id: int):
        self.token = token
        self.group_id = group_id
        self.api = "https://api.vk.com/method"
        self.v = "5.199"

    def _call(self, method: str, **params):
        payload = {"access_token": self.token, "v": self.v, **params}
        r = requests.post(f"{self.api}/{method}", data=payload, timeout=30)
        data = r.json()
        if "error" in data:
            raise RuntimeError(data["error"])
        return data["response"]

    def upload_photo(self, file_path: str) -> str:
        server = self._call("photos.getWallUploadServer", group_id=self.group_id)
        with open(file_path, "rb") as f:
            upload = requests.post(server["upload_url"], files={"photo": f}, timeout=60).json()
        logger.info("VK upload status: %s", "ok" if "photo" in upload else upload)
        saved = self._call(
            "photos.saveWallPhoto",
            group_id=self.group_id,
            photo=upload["photo"],
            server=upload["server"],
            hash=upload["hash"],
        )[0]
        return f"photo{saved['owner_id']}_{saved['id']}"

    def post(self, message: str, attachment: str | None = None) -> int:
        res = self._call(
            "wall.post",
            owner_id=-abs(self.group_id),
            from_group=1,
            message=message,
            attachments=attachment,
        )
        logger.info("wall.post response: %s", res)
        return int(res["post_id"])
