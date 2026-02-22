"""Media processing pipeline - dispatch by type."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from whaleclaw.media.link_summary import LinkSummarizer
from whaleclaw.media.transcribe import TranscriptionProcessor
from whaleclaw.media.vision import VisionProcessor


class MediaResult(BaseModel):
    """Result of media processing."""

    type: str
    text: str | None = None
    description: str | None = None
    metadata: dict[str, Any] = {}


class MediaPipeline:
    """Dispatch media processing by attachment type."""

    def __init__(self) -> None:
        self._vision = VisionProcessor()
        self._transcribe = TranscriptionProcessor()
        self._link = LinkSummarizer()

    async def process(self, attachment_type: str, path: str) -> MediaResult:
        if attachment_type in ("image", "picture", "photo"):
            desc = await self._vision.describe(path)
            return MediaResult(type="image", description=desc)
        if attachment_type in ("audio", "voice", "video"):
            text = await self._transcribe.transcribe(path)
            return MediaResult(type="audio", text=text)
        if attachment_type in ("url", "link"):
            text = await self._link.summarize(path)
            return MediaResult(type="link", text=text)
        return MediaResult(
            type=attachment_type,
            description=f"不支持的类型: {attachment_type}",
        )
