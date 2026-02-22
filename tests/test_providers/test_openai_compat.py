"""Tests for the OpenAI-compatible provider base (mocked HTTP)."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from unittest.mock import patch

import pytest

from whaleclaw.providers.base import Message
from whaleclaw.providers.openai import OpenAIProvider
from whaleclaw.types import ProviderAuthError


class _FakeResponse:
    def __init__(self, status_code: int, lines: list[str]) -> None:
        self.status_code = status_code
        self._lines = lines

    async def aiter_lines(self) -> AsyncIterator[str]:
        for line in self._lines:
            yield line

    async def aread(self) -> bytes:
        return b"error"

    async def __aenter__(self):  # noqa: ANN204
        return self

    async def __aexit__(self, *a: object) -> None:
        pass


class _FakeClient:
    def __init__(self, resp: _FakeResponse) -> None:
        self._resp = resp

    def stream(self, *a: object, **kw: object) -> _FakeResponse:
        return self._resp

    async def __aenter__(self):  # noqa: ANN204
        return self

    async def __aexit__(self, *a: object) -> None:
        pass


@pytest.fixture()
def provider() -> OpenAIProvider:
    return OpenAIProvider(api_key="test-key")


@pytest.mark.asyncio
async def test_streaming(provider: OpenAIProvider) -> None:
    lines = [
        "data: " + json.dumps({
            "choices": [{"delta": {"content": "Hi"}, "finish_reason": None}],
        }),
        "data: " + json.dumps({
            "choices": [{"delta": {"content": " there"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 3},
        }),
        "data: [DONE]",
    ]
    fake = _FakeClient(_FakeResponse(200, lines))
    chunks: list[str] = []

    async def on_stream(c: str) -> None:
        chunks.append(c)

    with patch("whaleclaw.providers.openai_compat.httpx.AsyncClient", return_value=fake):
        result = await provider.chat(
            [Message(role="user", content="hi")],
            "gpt-4o",
            on_stream=on_stream,
        )

    assert result.content == "Hi there"
    assert chunks == ["Hi", " there"]
    assert result.input_tokens == 5
    assert result.output_tokens == 3


@pytest.mark.asyncio
async def test_auth_error(provider: OpenAIProvider) -> None:
    fake = _FakeClient(_FakeResponse(401, []))
    with (
        patch("whaleclaw.providers.openai_compat.httpx.AsyncClient", return_value=fake),
        pytest.raises(ProviderAuthError),
    ):
        await provider.chat([Message(role="user", content="hi")], "gpt-4o")
