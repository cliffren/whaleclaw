"""Tests for MediaPipeline."""

from __future__ import annotations

import pytest

from whaleclaw.media.pipeline import MediaPipeline, MediaResult


@pytest.fixture
def pipeline() -> MediaPipeline:
    return MediaPipeline()


@pytest.mark.asyncio
async def test_process_image(pipeline: MediaPipeline) -> None:
    result = await pipeline.process("image", "/tmp/test.png")
    assert isinstance(result, MediaResult)
    assert result.type == "image"
    assert result.description == "图片理解需要多模态模型支持"


@pytest.mark.asyncio
async def test_process_audio(pipeline: MediaPipeline) -> None:
    result = await pipeline.process("audio", "/tmp/test.mp3")
    assert isinstance(result, MediaResult)
    assert result.type == "audio"
    assert result.text == "音频转文字功能尚未启用"
