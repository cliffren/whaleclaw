"""TTS engines - abstract base and implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod

import structlog

logger = structlog.get_logger()


class TTSEngine(ABC):
    """Abstract TTS engine."""

    @abstractmethod
    async def synthesize(self, text: str, voice: str = "default") -> bytes:
        """Synthesize text to audio bytes."""
        ...


class EdgeTTSEngine(TTSEngine):
    """Edge TTS engine (edge-tts)."""

    async def synthesize(self, text: str, voice: str = "default") -> bytes:
        import importlib.util

        if importlib.util.find_spec("edge_tts") is None:
            logger.warning("edge_tts not installed, TTS disabled")
            return b""
        return b""


class OpenAITTSEngine(TTSEngine):
    """OpenAI TTS API engine."""

    async def synthesize(self, text: str, voice: str = "default") -> bytes:
        logger.warning("OpenAI TTS needs API key")
        return b""
