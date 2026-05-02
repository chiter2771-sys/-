from dataclasses import dataclass


@dataclass(slots=True)
class ImageRecord:
    source_url: str
    local_path: str
    topic: str
    checksum: str


@dataclass(slots=True)
class PostRecord:
    post_type: str
    image_checksum: str | None
    text: str
    vk_post_id: int


@dataclass(slots=True)
class NewsRecord:
    guid: str
    title: str
    link: str
