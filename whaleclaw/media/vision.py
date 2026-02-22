"""Image vision and OCR processing."""

from __future__ import annotations


class VisionProcessor:
    """Image understanding and OCR."""

    async def describe(self, image_path: str, prompt: str | None = None) -> str:
        return "图片理解需要多模态模型支持"

    async def ocr(self, image_path: str) -> str:
        return "OCR 功能尚未启用"
