"""Audio/video transcription."""

from __future__ import annotations


class TranscriptionProcessor:
    """Transcribe audio to text."""

    async def transcribe(self, audio_path: str, language: str = "zh") -> str:
        return "音频转文字功能尚未启用"
