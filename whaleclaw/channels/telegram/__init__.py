"""Telegram channel — bot integration via polling or webhook."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from contextlib import suppress
from typing import Any

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)

from whaleclaw.channels.base import ChannelMessage, ChannelPlugin
from whaleclaw.channels.telegram.bot import BOT_COMMANDS, TelegramBot
from whaleclaw.channels.telegram.config import TelegramConfig
from whaleclaw.utils.log import get_logger

log = get_logger(__name__)


class TelegramChannel(ChannelPlugin):
    """Telegram channel plugin — manages bot application lifecycle."""

    name = "telegram"

    def __init__(self, config: TelegramConfig | None = None) -> None:
        self._config = config or TelegramConfig()
        self._bot: TelegramBot | None = None
        self._app: Application | None = None  # type: ignore[type-arg]
        self._polling_task: asyncio.Task[None] | None = None
        self._callback: Callable[
            [ChannelMessage], Awaitable[None]
        ] | None = None

    @property
    def bot(self) -> TelegramBot | None:
        return self._bot

    async def start(self) -> None:
        if not self._config.bot_token:
            log.warning("telegram.not_configured")
            return

        self._bot = TelegramBot(self._config)

        # Build the python-telegram-bot Application
        app = (
            Application.builder()
            .token(self._config.bot_token)
            .build()
        )
        self._app = app

        # Register command handlers for all slash commands
        cmd_names = [c.command for c in BOT_COMMANDS]
        app.add_handler(CommandHandler(cmd_names, self._bot.handle_command))

        # Register generic message handler (non-command text, photos, documents)
        app.add_handler(
            MessageHandler(
                (filters.TEXT | filters.PHOTO | filters.Document.ALL | filters.VIDEO | filters.AUDIO | filters.VOICE | filters.VIDEO_NOTE) & ~filters.COMMAND,
                self._bot.handle_message,
            )
        )

        # Initialize the application (needed before set_my_commands)
        await app.initialize()

        # Register bot commands in Telegram menu
        try:
            await app.bot.set_my_commands(BOT_COMMANDS)
            log.info("telegram.commands_registered", count=len(BOT_COMMANDS))
        except Exception as exc:
            log.warning("telegram.commands_register_failed", error=str(exc))

        if self._config.mode == "polling":
            await self._start_polling()
        else:
            log.info("telegram.webhook_mode", path=self._config.webhook_path)

        log.info("telegram.started", mode=self._config.mode)

    async def _start_polling(self) -> None:
        """Start polling in a background task."""
        app = self._app
        if app is None:
            return

        async def _poll() -> None:
            try:
                updater = app.updater
                if updater is None:
                    log.error("telegram.no_updater")
                    return
                await updater.start_polling(
                    allowed_updates=Update.ALL_TYPES,
                    drop_pending_updates=True,
                )
                await app.start()
                log.info("telegram.polling_started")
                # Keep alive until cancelled
                while True:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                log.info("telegram.polling_cancelled")
            except Exception as exc:
                log.exception("telegram.polling_error", error=str(exc))

        self._polling_task = asyncio.create_task(
            _poll(), name="telegram-polling"
        )

    async def stop(self) -> None:
        if self._polling_task is not None:
            self._polling_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._polling_task
            self._polling_task = None

        if self._app is not None:
            try:
                if self._app.updater and self._app.updater.running:
                    await self._app.updater.stop()
                if self._app.running:
                    await self._app.stop()
                await self._app.shutdown()
            except Exception as exc:
                log.warning("telegram.stop_error", error=str(exc))
            self._app = None

        log.info("telegram.stopped")

    async def send(
        self, peer_id: str, content: str, **kwargs: Any
    ) -> None:
        if self._app is None:
            return
        # peer_id format: "tg_<chat_id>"
        chat_id_str = peer_id.removeprefix("tg_")
        try:
            chat_id = int(chat_id_str)
        except ValueError:
            log.warning("telegram.invalid_peer_id", peer_id=peer_id)
            return
        await self._app.bot.send_message(chat_id=chat_id, text=content)

    async def on_message(
        self,
        callback: Callable[[ChannelMessage], Awaitable[None]],
    ) -> None:
        self._callback = callback
