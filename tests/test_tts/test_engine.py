"""Tests for TTS engines."""

from __future__ import annotations

import pytest

from whaleclaw.tts.engine import EdgeTTSEngine, OpenAITTSEngine


@pytest.mark.asyncio
async def test_edge_tts_stub() -> None:
    engine = EdgeTTSEngine()
    out = await engine.synthesize("hello", voice="default")
    assert isinstance(out, bytes)


@pytest.mark.asyncio
async def test_openai_tts_stub() -> None:
    engine = OpenAITTSEngine()
    out = await engine.synthesize("hello", voice="default")
    assert isinstance(out, bytes)
