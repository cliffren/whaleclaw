"""Tests for the Anthropic provider adapter (mocked HTTP)."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from unittest.mock import patch

import pytest

from whaleclaw.providers.anthropic import AnthropicProvider
from whaleclaw.providers.base import Message
from whaleclaw.types import ProviderAuthError, ProviderRateLimitError


def _make_sse(*events: dict[str, object]) -> list[str]:
    """Build SSE lines from event dicts."""
    lines: list[str] = []
    for ev in events:
        lines.append(f"data: {json.dumps(ev)}")
    return lines


class _FakeResponse:
    """Minimal async response mock for httpx streaming."""

    def __init__(self, status_code: int, lines: list[str]) -> None:
        self.status_code = status_code
        self._lines = lines

    async def aiter_lines(self) -> AsyncIterator[str]:
        for line in self._lines:
            yield line

    async def aread(self) -> bytes:
        return b"error body"

    async def __aenter__(self) -> _FakeResponse:
        return self

    async def __aexit__(self, *args: object) -> None:
        pass


class _FakeClient:
    """Minimal async client mock."""

    def __init__(self, response: _FakeResponse) -> None:
        self._response = response

    def stream(self, *args: object, **kwargs: object) -> _FakeResponse:
        return self._response

    async def __aenter__(self) -> _FakeClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        pass


@pytest.fixture()
def provider() -> AnthropicProvider:
    return AnthropicProvider(api_key="test-key")


class TestAnthropicProvider:
    def test_missing_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(ProviderAuthError):
            AnthropicProvider(api_key="")

    @pytest.mark.asyncio
    async def test_streaming_chat(self, provider: AnthropicProvider) -> None:
        sse_lines = _make_sse(
            {"type": "message_start", "message": {"usage": {"input_tokens": 10}}},
            {
                "type": "content_block_delta",
                "delta": {"type": "text_delta", "text": "Hello"},
            },
            {
                "type": "content_block_delta",
                "delta": {"type": "text_delta", "text": " world"},
            },
            {
                "type": "message_delta",
                "delta": {"stop_reason": "end_turn"},
                "usage": {"output_tokens": 5},
            },
        )

        fake_resp = _FakeResponse(200, sse_lines)
        fake_client = _FakeClient(fake_resp)

        chunks: list[str] = []

        async def on_stream(chunk: str) -> None:
            chunks.append(chunk)

        with patch("whaleclaw.providers.anthropic.httpx.AsyncClient", return_value=fake_client):
            result = await provider.chat(
                [Message(role="user", content="hi")],
                "claude-sonnet-4-20250514",
                on_stream=on_stream,
            )

        assert result.content == "Hello world"
        assert result.input_tokens == 10
        assert result.output_tokens == 5
        assert chunks == ["Hello", " world"]

    @pytest.mark.asyncio
    async def test_auth_error(self, provider: AnthropicProvider) -> None:
        fake_resp = _FakeResponse(401, [])
        fake_client = _FakeClient(fake_resp)

        with (
            patch("whaleclaw.providers.anthropic.httpx.AsyncClient", return_value=fake_client),
            pytest.raises(ProviderAuthError),
        ):
            await provider.chat(
                [Message(role="user", content="hi")],
                "claude-sonnet-4-20250514",
            )

    @pytest.mark.asyncio
    async def test_rate_limit(self, provider: AnthropicProvider) -> None:
        fake_resp = _FakeResponse(429, [])
        fake_client = _FakeClient(fake_resp)

        with (
            patch("whaleclaw.providers.anthropic.httpx.AsyncClient", return_value=fake_client),
            pytest.raises(ProviderRateLimitError),
        ):
            await provider.chat(
                [Message(role="user", content="hi")],
                "claude-sonnet-4-20250514",
            )
