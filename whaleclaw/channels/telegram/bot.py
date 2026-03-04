"""Telegram bot — core message handling logic."""

from __future__ import annotations

import asyncio
import base64
import random
import re
import uuid
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING, Any

from telegram import BotCommand, Update
from telegram.ext import ContextTypes

from whaleclaw.channels.telegram.config import TelegramConfig
from whaleclaw.plugins.evomap.bridge import build_memory_hint_from_hook_data
from whaleclaw.plugins.hooks import HookContext, HookManager, HookPoint
from whaleclaw.providers.base import ImageContent
from whaleclaw.providers.nvidia import NvidiaProvider
from whaleclaw.utils.log import get_logger
from whaleclaw.config.paths import WHALECLAW_HOME

if TYPE_CHECKING:
    from whaleclaw.config.schema import WhaleclawConfig
    from whaleclaw.memory.manager import MemoryManager
    from whaleclaw.sessions.group_compressor import SessionGroupCompressor
    from whaleclaw.sessions.manager import SessionManager
    from whaleclaw.tools.registry import ToolRegistry

log = get_logger(__name__)

_IMG_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_FILE_RE = re.compile(r"(?<!!)\[([^\]]+)\]\((/[^)]+)\)")
_FILE_EXTS = {
    ".txt", ".md", ".json", ".log",
    ".pptx", ".ppt", ".pdf", ".docx", ".doc",
    ".xlsx", ".xls", ".csv",
    ".zip", ".tar", ".gz",
    ".mp3", ".wav", ".aif", ".aiff", ".m4a", ".aac", ".ogg", ".opus", ".flac",
    ".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm",
}

# ── Tool status display ─────────────────────────────────────
_TOOL_ICONS: dict[str, str] = {
    "bash": "💻",
    "file_read": "📖",
    "file_write": "✍️",
    "file_edit": "✏️",
    "browser": "🌐",
    "memory_search": "🔍",
    "memory_add": "📝",
    "memory_list": "📋",
    "skill": "🎓",
    "desktop_capture": "📷",
}
_KEY_FIELDS: dict[str, str] = {
    "bash": "command",
    "file_read": "path",
    "file_write": "path",
    "file_edit": "path",
    "memory_search": "query",
    "memory_add": "content",
    "browser": "url",
}
_PREVIEW_MAX = 32


def _tool_icon(name: str) -> str:
    return _TOOL_ICONS.get(name, "🛠️")


def _tool_preview(name: str, args: dict[str, Any]) -> str:
    field = _KEY_FIELDS.get(name, next(iter(args), None))
    if not field:
        return ""
    val = str(args.get(field, "")).replace("\n", " ").strip()
    if not val:
        return ""
    if len(val) > _PREVIEW_MAX:
        return val[:_PREVIEW_MAX] + "…"
    return val


# ── Status message tracker ──────────────────────────────────
_THINKING_FRAMES = (".", "..", "...")
_THINKING_MIN_MS = 1800
_THINKING_MAX_MS = 2200
_SUPPRESSION_MS = 2000


class StatusMessageTracker:
    """Manages a single editable Telegram status message during agent execution.

    Design:
    - One status message per agent run, edited in place (never spam new messages).
    - Animated thinking dots while LLM is processing.
    - Tool calls shown with icon + truncated key argument.
    - Network retry shown as warning line.
    - Telegram 429 rate-limit handled via backoff (silent skip during cooldown).
    - All edits serialised via asyncio task chain to avoid concurrent edit errors.
    - Post-completion suppression prevents stale events from editing after reply sent.
    """

    def __init__(self, bot: Any, chat_id: int, thread_id: int | None = None) -> None:
        self._bot = bot
        self._chat_id = chat_id
        self._thread_id = thread_id
        self._msg_id: int | None = None
        self._last_text: str = ""
        self._tool_lines: list[str] = []
        self._retrying: bool = False
        self._retry_text: str = ""
        self._completed: bool = False
        self._rate_limited_until: float = 0.0
        self._task_chain: asyncio.Task[None] | None = None

        # Thinking animation state
        self._anim_task: asyncio.Task[None] | None = None

    # ── Public API ─────────────────────────────────────────

    def start_thinking(self) -> None:
        """Start the animated thinking dots."""
        if self._anim_task and not self._anim_task.done():
            return
        self._anim_task = asyncio.create_task(self._thinking_loop())

    def stop_thinking(self) -> None:
        if self._anim_task:
            self._anim_task.cancel()
            self._anim_task = None

    async def on_tool_start(self, tool_name: str, args: dict[str, Any]) -> None:
        self.stop_thinking()
        preview = _tool_preview(tool_name, args)
        icon = _tool_icon(tool_name)
        if preview:
            line = f"{icon} {tool_name}: {preview}"
        else:
            line = f"{icon} {tool_name}"
        self._tool_lines.append(line)
        self._retrying = False
        self._enqueue_update()

    async def on_retry(self, attempt: int, max_attempts: int, error: str) -> None:  # noqa: ARG002
        self._retrying = True
        self._retry_text = f"⚠️ 网络抖动，重试 {attempt}/{max_attempts}…"
        self._enqueue_update()

    async def clear(self) -> None:
        """Mark as completed and delete the status message."""
        self._completed = True
        self.stop_thinking()
        if self._msg_id is not None:
            with suppress(Exception):
                await self._bot.delete_message(
                    chat_id=self._chat_id, message_id=self._msg_id
                )
            self._msg_id = None

    # ── Internal ───────────────────────────────────────────

    def _build_text(self, frame_idx: int | None = None) -> str:
        if frame_idx is not None and not self._tool_lines:
            # Pure thinking state — animated dots
            dots = _THINKING_FRAMES[frame_idx % len(_THINKING_FRAMES)]
            return f"💭[思考{dots:<3}]"
        lines = list(self._tool_lines[-8:])  # cap at 8 tool lines
        if self._retrying:
            lines.append(self._retry_text)
        return "\n".join(lines) if lines else "💭[思考...]"

    async def _thinking_loop(self) -> None:
        frame = 0
        while not self._completed:
            delay = random.randint(_THINKING_MIN_MS, _THINKING_MAX_MS) / 1000
            await asyncio.sleep(delay)
            if self._completed:
                break
            # Only animate when no tools have been called yet
            if not self._tool_lines:
                await self._safe_edit(self._build_text(frame))
            frame += 1

    def _enqueue_update(self) -> None:
        """Serialise edit calls: chain as a task after the previous one."""
        async def _do() -> None:
            if self._completed:
                return
            await self._safe_edit(self._build_text())

        prev = self._task_chain
        async def _chained() -> None:
            if prev:
                with suppress(Exception):
                    await prev
            await _do()

        self._task_chain = asyncio.create_task(_chained())

    async def _safe_edit(self, text: str) -> None:
        """Edit or create the status message, with rate-limit handling."""
        now = asyncio.get_running_loop().time()
        if now < self._rate_limited_until:
            return  # in cooldown — skip silently

        text = text.strip()
        if not text or text == self._last_text:
            return

        try:
            if self._msg_id is None:
                sent = await self._bot.send_message(
                    chat_id=self._chat_id,
                    text=text,
                    disable_notification=True,
                    message_thread_id=self._thread_id,
                )
                self._msg_id = sent.message_id
                self._last_text = text
            else:
                await self._bot.edit_message_text(
                    chat_id=self._chat_id,
                    message_id=self._msg_id,
                    text=text,
                )
                self._last_text = text
        except Exception as exc:
            msg = str(exc).lower()
            # 429 rate limit
            retry_after = self._parse_retry_after(exc)
            if retry_after:
                self._rate_limited_until = now + retry_after
                return
            # Message not modified — skip
            if "message is not modified" in msg:
                return
            # Message deleted / gone — send a fresh one next time
            if any(k in msg for k in ("message to edit not found", "message can't be edited",
                                       "message is too old", "message_id_invalid")):
                self._msg_id = None
                self._last_text = ""
            # Other errors: ignore silently

    @staticmethod
    def _parse_retry_after(exc: Exception) -> float:
        """Extract retry_after seconds from a Telegram 429 error."""
        msg = str(exc)
        import re as _re
        m = _re.search(r"retry.?after\D*(\d+)", msg, _re.IGNORECASE)
        if m:
            return float(m.group(1))
        return 0.0


# ── Commands registered in the Telegram menu ────────────────
BOT_COMMANDS = [
    BotCommand("help", "Show available commands"),
    BotCommand("new", "Reset current session"),
    BotCommand("reset", "Reset current session (alias)"),
    BotCommand("status", "Show session status"),
    BotCommand("models", "List available models"),
    BotCommand("model", "Switch model (e.g. /model openai/gpt-5.2)"),
    BotCommand("think", "Set thinking depth (off/low/medium/high)"),
    BotCommand("compact", "Compress session context (L0/L1 summary)"),
]


def _format_exception_text(exc: Exception) -> str:
    """Return a readable exception text even when ``str(exc)`` is empty."""
    msg = str(exc).strip()
    return msg if msg else exc.__class__.__name__


class TelegramBot:
    """Process incoming Telegram messages and route to the Agent."""

    def __init__(self, config: TelegramConfig) -> None:
        self._config = config
        self._whaleclaw_config: WhaleclawConfig | None = None
        self._session_manager: SessionManager | None = None
        self._tool_registry: ToolRegistry | None = None
        self._memory_manager: MemoryManager | None = None
        self._hook_manager: HookManager | None = None
        self._group_compressor: SessionGroupCompressor | None = None
        self._compression_ready_fn: Callable[[], bool] | None = None

    def bind_agent(
        self,
        config: WhaleclawConfig,
        session_manager: SessionManager,
        registry: ToolRegistry,
        memory_manager: MemoryManager | None = None,
        hook_manager: HookManager | None = None,
        group_compressor: SessionGroupCompressor | None = None,
        compression_ready_fn: Callable[[], bool] | None = None,
    ) -> None:
        """Inject Agent dependencies so handle_message can run the full loop."""
        self._whaleclaw_config = config
        self._session_manager = session_manager
        self._tool_registry = registry
        self._memory_manager = memory_manager
        self._hook_manager = hook_manager
        self._group_compressor = group_compressor
        self._compression_ready_fn = compression_ready_fn

    # ── Main message handler ───────────────────────────────

    async def handle_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Process a received Telegram message."""
        message = update.effective_message
        if message is None:
            return

        user = update.effective_user
        if user is None:
            return

        chat = update.effective_chat
        if chat is None:
            return

        user_id = user.id
        chat_id = chat.id
        is_group = chat.type in ("group", "supergroup")

        # ── Permission check ──
        if (
            self._config.dm_policy == "closed"
            and self._config.allowed_user_ids
            and user_id not in self._config.allowed_user_ids
        ):
            await message.reply_text("⛔ 您不在白名单中，无法使用此 Bot。")
            return

        # ── In group, only respond to @bot mentions ──
        if is_group:
            bot_user = context.bot
            text = message.text or message.caption or ""
            if f"@{bot_user.username}" not in text and not (
                message.reply_to_message
                and message.reply_to_message.from_user
                and message.reply_to_message.from_user.id == bot_user.id
            ):
                return
            # Strip the @mention
            text = text.replace(f"@{bot_user.username}", "").strip()
        else:
            text = message.text or message.caption or ""

        # ── Handle photos and documents ──
        download_texts = []
        images = []
        try:
            dl_dir = WHALECLAW_HOME / "downloads"
            dl_dir.mkdir(parents=True, exist_ok=True)
            if message.photo:
                photo = message.photo[-1]
                file = await photo.get_file()
                filepath = dl_dir / f"image_{uuid.uuid4().hex[:8]}.jpg"
                await file.download_to_drive(filepath)
                download_texts.append(f"![用户发送了一张图片]({filepath})")
                try:
                    with open(filepath, "rb") as f:
                        b64_data = base64.b64encode(f.read()).decode("ascii")
                    images.append(ImageContent(mime="image/jpeg", data=b64_data))
                except Exception as e:
                    log.warning("telegram.image_encode_failed", error=str(e))
            elif message.document:
                doc = message.document
                file = await doc.get_file()
                filename = doc.file_name or f"file_{uuid.uuid4().hex[:8]}"
                filepath = dl_dir / filename
                await file.download_to_drive(filepath)
                download_texts.append(f"[用户发送了一个文件，已保存至 {filepath}]")
            elif message.video:
                vid = message.video
                file = await vid.get_file()
                filename = vid.file_name or f"video_{uuid.uuid4().hex[:8]}.mp4"
                filepath = dl_dir / filename
                await file.download_to_drive(filepath)
                download_texts.append(f"[用户发送了一段视频，已保存至 {filepath}]")
            elif message.audio:
                aud = message.audio
                file = await aud.get_file()
                filename = aud.file_name or f"audio_{uuid.uuid4().hex[:8]}.mp3"
                filepath = dl_dir / filename
                await file.download_to_drive(filepath)
                download_texts.append(f"[用户发送了一段音频，已保存至 {filepath}]")
            elif message.voice:
                voc = message.voice
                file = await voc.get_file()
                filepath = dl_dir / f"voice_{uuid.uuid4().hex[:8]}.ogg"
                await file.download_to_drive(filepath)
                download_texts.append(f"[用户发送了一段语音消息，已保存至 {filepath}]")
            elif message.video_note:
                vn = message.video_note
                file = await vn.get_file()
                filepath = dl_dir / f"video_note_{uuid.uuid4().hex[:8]}.mp4"
                await file.download_to_drive(filepath)
                download_texts.append(f"[用户发送了一段视频留言，已保存至 {filepath}]")
        except Exception as e:
            log.warning("telegram.download_failed", error=str(e))
            
        if download_texts:
            text = text + "\n\n" + "\n".join(download_texts) if text else "\n".join(download_texts)

        text = text.strip()
        if not text:
            return

        peer_id = f"tg_{chat_id}"

        log.info(
            "telegram.message",
            user_id=user_id,
            chat_id=chat_id,
            is_group=is_group,
            text_len=len(text),
            text_preview=(" ".join(text.split())[:80]),
            has_images=bool(images),
        )

        await self._run_agent_and_reply(text, peer_id, message, images=images)

    # ── Command handlers ───────────────────────────────────

    async def handle_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Route slash commands."""
        message = update.effective_message
        if message is None:
            return

        text = message.text or ""
        if not text.startswith("/"):
            return

        # Permission check
        user = update.effective_user
        if (
            user
            and self._config.dm_policy == "closed"
            and self._config.allowed_user_ids
            and user.id not in self._config.allowed_user_ids
        ):
            await message.reply_text("⛔ 您不在白名单中。")
            return

        chat = update.effective_chat
        peer_id = f"tg_{chat.id}" if chat else "tg_unknown"

        if not self._session_manager:
            await message.reply_text("⚠️ Agent 尚未就绪。")
            return

        session = await self._session_manager.get_or_create("telegram", peer_id)

        # Parse command
        parts = text.split(maxsplit=1)
        cmd = parts[0].lower().split("@")[0]  # strip @botname suffix
        arg = parts[1].strip() if len(parts) > 1 else ""

        reply = await self._dispatch_command(cmd, arg, session, peer_id)
        if reply is not None:
            await message.reply_text(reply)

    async def _dispatch_command(
        self, cmd: str, arg: str, session: Any, peer_id: str
    ) -> str | None:
        """Dispatch a command and return the reply text."""
        if cmd in {"/help", "/h"}:
            return (
                "📋 可用命令:\n"
                "/new, /reset — 重置当前会话\n"
                "/status — 显示会话状态\n"
                "/models — 查看可切换模型\n"
                "/model <序号|provider/model> — 切换模型\n"
                "/think <off|low|medium|high> — 设置思考深度\n"
                "/compact — 压缩会话上下文"
            )

        if cmd in {"/new", "/reset"}:
            if self._session_manager:
                await self._session_manager.delete(session.id)
            return "🔄 会话已重置。下次发消息将自动创建新会话。"

        if cmd == "/status":
            msg_count = session.message_count or len(session.messages)
            return (
                f"📊 会话状态:\n"
                f"ID: {session.id[:12]}…\n"
                f"模型: {session.model}\n"
                f"思考深度: {session.thinking_level}\n"
                f"消息数: {msg_count}"
            )

        if cmd == "/models":
            models = self._list_selectable_models()
            if not models:
                return "当前没有可切换模型，请先在配置中启用并验证模型。"
            lines = ["📦 可切换模型:"]
            for i, mid in enumerate(models, start=1):
                marker = " ✅" if mid == session.model else ""
                lines.append(f"{i}. {mid}{marker}")
            lines.append("\n发送 /model <序号> 或 /model <provider/model> 切换。")
            return "\n".join(lines)

        if cmd == "/model":
            if not arg:
                return f"当前模型: {session.model}\n发送 /models 查看可选模型。"
            models = self._list_selectable_models()
            target = arg
            if arg.isdigit():
                idx = int(arg)
                if idx < 1 or idx > len(models):
                    return f"序号无效: {arg}\n发送 /models 查看可选模型。"
                target = models[idx - 1]
            if target not in models:
                return f"模型不可用: {target}\n发送 /models 查看可选模型。"
            if self._session_manager:
                await self._session_manager.update_model(session, target)
            return f"✅ 已切换模型到: {target}"

        if cmd == "/think":
            valid = {"off", "low", "medium", "high"}
            if not arg or arg.lower() not in valid:
                return (
                    f"当前思考深度: {session.thinking_level}\n"
                    f"用法: /think <off|low|medium|high>"
                )
            level = arg.lower()
            if self._session_manager:
                await self._session_manager.update_thinking(session, level)
            return f"✅ 思考深度已设为: {level}"

        if cmd == "/compact":
            if self._compression_ready_fn and not self._compression_ready_fn():
                return "⏳ 压缩任务正在进行中，请稍后再试。"
            if not self._group_compressor or not self._session_manager:
                return "⚠️ 会话压缩功能未启用。"

            from whaleclaw.providers.router import ModelRouter

            if not self._whaleclaw_config:
                return "⚠️ 配置未就绪。"

            router = ModelRouter(self._whaleclaw_config.models)
            model_id = self._whaleclaw_config.agent.summarizer.model.strip()
            if not model_id:
                return "⚠️ 未配置压缩模型。"

            loaded = await self._session_manager.get(session.id)
            if not loaded or not loaded.messages:
                return "当前会话没有消息可压缩。"

            stats = await self._group_compressor.prewarm_session(
                session_id=loaded.id,
                messages=loaded.messages,
                router=router,
                model_id=model_id,
            )
            return (
                f"✅ 压缩完成\n"
                f"总组数: {stats['total_groups']}\n"
                f"处理: {stats['processed_groups']}\n"
                f"缓存命中: {stats['cache_hits']}\n"
                f"新生成: {stats['generated']}"
            )

        return None

    # ── Agent execution ────────────────────────────────────

    async def _run_agent_and_reply(
        self,
        text: str,
        peer_id: str,
        message: Any,
        images: list[ImageContent] | None = None,
    ) -> None:
        """Run Agent and send replies to Telegram."""
        if not self._whaleclaw_config or not self._session_manager or not self._tool_registry:
            await message.reply_text(text)
            return

        from whaleclaw.agent.loop import run_agent
        from whaleclaw.gateway.protocol import make_message as make_ws_msg
        from whaleclaw.gateway.ws import broadcast_all
        from whaleclaw.providers.router import ModelRouter

        if self._compression_ready_fn is not None and not self._compression_ready_fn():
            await message.reply_text("⏳ 会话压缩中，请稍后再试。")
            return

        session = await self._session_manager.get_or_create("telegram", peer_id)

        # Check if it's a command first
        if text.strip().startswith("/"):
            parts = text.split(maxsplit=1)
            cmd = parts[0].lower().split("@")[0]
            arg = parts[1].strip() if len(parts) > 1 else ""
            cmd_reply = await self._dispatch_command(cmd, arg, session, peer_id)
            if cmd_reply is not None:
                await message.reply_text(cmd_reply)
                return

        await self._session_manager.add_message(session, "user", text)

        await broadcast_all(
            make_ws_msg(session.id, f"📨 **Telegram** `{peer_id}`:\n{text}")
        )

        # ── Status message tracker (progress feedback without spamming) ──
        chat = message.chat
        thread_id: int | None = getattr(message, "message_thread_id", None)
        tracker = StatusMessageTracker(
            bot=message.get_bot(),
            chat_id=chat.id,
            thread_id=thread_id,
        )
        tracker.start_thinking()

        async def _on_tool_call(tool_name: str, args: dict) -> None:  # type: ignore[type-arg]
            await tracker.on_tool_start(tool_name, args)

        async def _on_retry(attempt: int, max_attempts: int, error: str) -> None:
            await tracker.on_retry(attempt, max_attempts, error)

        router = ModelRouter(self._whaleclaw_config.models)
        extra_memory = ""
        if self._hook_manager is not None:
            try:
                hook_out = await self._hook_manager.run(
                    HookPoint.BEFORE_MESSAGE,
                    HookContext(
                        hook=HookPoint.BEFORE_MESSAGE,
                        session_id=session.id,
                        data={
                            "message": text,
                            "channel": "telegram",
                            "peer_id": peer_id,
                        },
                    ),
                )
                if hook_out.proceed:
                    extra_memory = build_memory_hint_from_hook_data(hook_out.data)
            except Exception:
                pass

        try:
            reply = await run_agent(
                message=text,
                session_id=session.id,
                config=self._whaleclaw_config,
                session=session,
                router=router,
                registry=self._tool_registry,
                on_tool_call=_on_tool_call,
                on_retry=_on_retry,
                images=images,
                session_manager=self._session_manager,
                session_store=self._session_manager._store,  # noqa: SLF001
                memory_manager=self._memory_manager,
                extra_memory=extra_memory,
                group_compressor=self._group_compressor,
                user_message_persisted=True,
            )
            log.info("telegram.agent_reply", reply_len=len(reply), preview=reply[:200])
        except Exception as exc:
            await tracker.clear()
            if self._hook_manager is not None:
                with suppress(Exception):
                    await self._hook_manager.run(
                        HookPoint.ON_ERROR,
                        HookContext(
                            hook=HookPoint.ON_ERROR,
                            session_id=session.id,
                            data={
                                "error": str(exc),
                                "message": text,
                                "channel": "telegram",
                            },
                        ),
                    )
            error_text = _format_exception_text(exc)
            log.exception("telegram.agent_error", error=error_text, model=session.model)
            await message.reply_text(f"❌ 处理失败: {error_text}")
            await broadcast_all(
                make_ws_msg(session.id, f"❌ **Telegram处理失败**: {error_text}")
            )
            return

        # Clear status message before sending the reply
        await tracker.clear()

        if not reply.strip():
            await message.reply_text("任务执行中但未返回结果，请稍后重试或查看 WebChat。")
            return

        try:
            await self._session_manager.add_message(session, "assistant", reply)
            text_content, image_paths, file_paths = self._prepare_reply_payload(reply)

            # Telegram has 4096 char limit per message — split if needed
            if text_content:
                for chunk in _split_text(text_content, 4000):
                    await message.reply_text(chunk)

            for img_path in image_paths:
                try:
                    await message.reply_photo(photo=open(img_path, "rb"))  # noqa: SIM115
                except Exception:
                    log.exception("telegram.image_send_failed", path=str(img_path))

            for fp in file_paths:
                try:
                    await message.reply_document(document=open(fp, "rb"))  # noqa: SIM115
                except Exception:
                    log.exception("telegram.file_send_failed", path=str(fp))

            await broadcast_all(
                make_ws_msg(session.id, f"🤖 **Telegram回复**:\n{reply}")
            )
        except Exception as exc:
            log.exception("telegram.reply_failed")
            await message.reply_text(reply[:4000] if reply else f"回复发送失败: {exc}")

    # ── Helpers ─────────────────────────────────────────────

    def _list_selectable_models(self) -> list[str]:
        """Return verified and configured model IDs."""
        if self._whaleclaw_config is None:
            return []

        providers_cfg = self._whaleclaw_config.models
        result: list[str] = []
        all_providers = [
            "anthropic", "openai", "deepseek", "qwen", "zhipu",
            "minimax", "moonshot", "google", "nvidia", "bailian",
        ]
        for pname in all_providers:
            pcfg = getattr(providers_cfg, pname, None)
            if not pcfg:
                continue
            has_auth = bool(pcfg.api_key) or (
                getattr(pcfg, "auth_mode", "api_key") == "oauth"
                and bool(pcfg.oauth_access)
            )
            if not has_auth:
                continue
            for cm in pcfg.configured_models:
                if not cm.verified:
                    continue
                if pname == "openai" and pcfg.auth_mode == "oauth" and cm.id != "gpt-5.2":
                    continue
                if pname == "nvidia" and not NvidiaProvider.model_supports_tools(cm.id):
                    continue
                result.append(f"{pname}/{cm.id}")
        return result

    def _prepare_reply_payload(
        self, reply: str
    ) -> tuple[str, list[Path], list[Path]]:
        """Extract text/image/file payloads from agent reply."""
        image_paths: list[Path] = []
        for match in _IMG_RE.finditer(reply):
            path = match.group(2)
            local = Path(path)
            if local.is_file() and local.suffix.lower() in {
                ".png", ".jpg", ".jpeg", ".gif", ".webp",
            }:
                image_paths.append(local)

        file_paths: list[Path] = []
        file_replacements: list[tuple[str, str]] = []
        seen_paths: set[str] = set()

        for match in _FILE_RE.finditer(reply):
            name, path = match.group(1), match.group(2)
            local = Path(path)
            if (
                local.is_file()
                and local.suffix.lower() in _FILE_EXTS
                and path not in seen_paths
            ):
                seen_paths.add(path)
                file_paths.append(local)
                file_replacements.append((match.group(0), f"📎 {name}"))

        clean_text = reply
        for match in _IMG_RE.finditer(reply):
            clean_text = clean_text.replace(match.group(0), "")
        for md_str, label in file_replacements:
            clean_text = clean_text.replace(md_str, label)
        return clean_text.strip(), image_paths, file_paths


def _split_text(text: str, max_len: int = 4000) -> list[str]:
    """Split long text into chunks respecting newline boundaries."""
    if len(text) <= max_len:
        return [text]

    chunks: list[str] = []
    while text:
        if len(text) <= max_len:
            chunks.append(text)
            break
        # Find the last newline before max_len
        cut = text.rfind("\n", 0, max_len)
        if cut < max_len // 2:
            cut = max_len
        chunks.append(text[:cut])
        text = text[cut:].lstrip("\n")
    return chunks
