"""Tests for the Feishu bot message handler."""

from __future__ import annotations

import base64
import json
from types import SimpleNamespace
from typing import Any

import pytest

from whaleclaw.channels.feishu.bot import FeishuBot, _format_exception_text
from whaleclaw.channels.feishu.config import FeishuConfig
from whaleclaw.config.schema import ProviderModelEntry, WhaleclawConfig


class _StubClient:
    async def reply_message(  # noqa: D401
        self, message_id: str, msg_type: str, content: str
    ) -> dict[str, Any]:
        return {"data": {"message_id": "reply-1"}}

    async def download_resource(
        self, message_id: str, file_key: str, *, resource_type: str = "file"
    ) -> bytes:
        assert resource_type == "image"
        return b"fake-image-binary"


class _StubSessionManager:
    def __init__(self) -> None:
        self.updated_to: str | None = None

    async def update_model(self, session: Any, model: str) -> None:
        session.model = model
        self.updated_to = model


class TestExtractText:
    def test_text_message(self) -> None:
        message = {
            "message_type": "text",
            "content": json.dumps({"text": "hello world"}),
        }
        assert FeishuBot.extract_text(message) == "hello world"

    def test_post_message(self) -> None:
        message = {
            "message_type": "post",
            "content": json.dumps({
                "content": [
                    [
                        {"tag": "text", "text": "line one"},
                        {"tag": "text", "text": "line two"},
                    ]
                ]
            }),
        }
        assert "line one" in FeishuBot.extract_text(message)

    def test_empty_content(self) -> None:
        message = {"message_type": "text", "content": "{}"}
        assert FeishuBot.extract_text(message) == ""

    def test_invalid_json(self) -> None:
        message = {"message_type": "text", "content": "not json"}
        assert FeishuBot.extract_text(message) == ""


class TestFormatExceptionText:
    def test_empty_exception_message(self) -> None:
        assert _format_exception_text(TimeoutError()) == "TimeoutError"

    def test_non_empty_exception_message(self) -> None:
        assert _format_exception_text(RuntimeError("boom")) == "boom"


@pytest.mark.asyncio
async def test_handle_image_message_passes_images_to_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    bot = FeishuBot(_StubClient(), FeishuConfig(dm_policy="open"))
    captured: dict[str, Any] = {}

    async def _fake_run(
        text: str,
        peer_id: str,
        card_msg_id: str,
        *,
        images: list[Any] | None = None,
    ) -> None:
        captured["text"] = text
        captured["peer_id"] = peer_id
        captured["card_msg_id"] = card_msg_id
        captured["images"] = images or []

    monkeypatch.setattr(bot, "_run_agent_and_reply", _fake_run)

    await bot.handle_message({
        "sender": {"sender_id": {"open_id": "ou_xxx"}},
        "message": {
            "message_id": "msg-image-1",
            "chat_type": "p2p",
            "message_type": "image",
            "content": json.dumps({"image_key": "img_key_1"}),
        },
    })

    assert captured["text"] == "(用户发送了一张图片)"
    assert captured["peer_id"] == "ou_xxx"
    assert len(captured["images"]) == 1
    assert captured["images"][0].mime == "image/png"
    assert captured["images"][0].data == base64.b64encode(b"fake-image-binary").decode("ascii")


@pytest.mark.asyncio
async def test_model_command_lists_configured_models() -> None:
    bot = FeishuBot(_StubClient(), FeishuConfig(dm_policy="open"))
    cfg = WhaleclawConfig()
    cfg.models.qwen.api_key = "test-key"
    cfg.models.qwen.configured_models = [
        ProviderModelEntry(id="qwen3.5-plus", verified=True),
        ProviderModelEntry(id="qwen3-max", verified=False),
    ]
    bot._whaleclaw_config = cfg  # noqa: SLF001
    bot._session_manager = _StubSessionManager()  # noqa: SLF001
    session = SimpleNamespace(id="s1", model="qwen/qwen3.5-plus")

    out = await bot._handle_command("/models", session)  # noqa: SLF001

    assert out is not None
    assert "1. qwen/qwen3.5-plus (当前)" in out
    assert "qwen3-max" not in out


@pytest.mark.asyncio
async def test_model_command_switch_by_index() -> None:
    bot = FeishuBot(_StubClient(), FeishuConfig(dm_policy="open"))
    cfg = WhaleclawConfig()
    cfg.models.qwen.api_key = "test-key"
    cfg.models.qwen.configured_models = [
        ProviderModelEntry(id="qwen3.5-plus", verified=True),
        ProviderModelEntry(id="qwen3-max", verified=True),
    ]
    sm = _StubSessionManager()
    bot._whaleclaw_config = cfg  # noqa: SLF001
    bot._session_manager = sm  # noqa: SLF001
    session = SimpleNamespace(id="s1", model="qwen/qwen3.5-plus")

    out = await bot._handle_command("/model 2", session)  # noqa: SLF001

    assert out == "已切换模型到: qwen/qwen3-max"
    assert session.model == "qwen/qwen3-max"
    assert sm.updated_to == "qwen/qwen3-max"
