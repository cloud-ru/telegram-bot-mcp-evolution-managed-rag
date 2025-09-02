from __future__ import annotations

import asyncio
import time
from typing import Callable, Awaitable
from loguru import logger

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.exceptions import TelegramBadRequest

from .config import Settings
from .mcp_client import McpClient
from .agent import build_agent


async def run_bot() -> None:
    settings = Settings.load()

    bot = Bot(token=settings.telegram_token)#
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def cmd_start(message: Message) -> None:
        await message.answer("Привет! Я твой AI-агент, готовый помочь тебе с вопросами по твоей базе знаний Evolution Managed RAG.")

    @dp.message(F.text)
    async def on_text(message: Message) -> None:
        user_text = message.text or ""
        if not user_text.strip():
            return
        user_id = message.from_user.id if message.from_user else None
        logger.info(f"User {user_id} query: {user_text!r}")

        # Initial placeholder message
        sent = await message.answer("⏳ Думаю")

        try:
            async with McpClient(settings.mcp_server_url, transport=settings.mcp_transport) as mcp:
                agent, astream_answer = build_agent(
                    mcp=mcp,
                    rag_tool_name=settings.mcp_rag_tool_name,
                    model_name=settings.gigachat_model,
                    temperature=settings.gigachat_temperature,
                    scope=settings.gigachat_scope,
                    credentials=settings.gigachat_credentials,
                    verify_ssl=settings.gigachat_verify_ssl,
                )

                # Stream updates to Telegram by editing the message text
                aggregator = _TelegramAggregator(
                    edit_fn=lambda text: sent.edit_text(text),
                    interval=settings.stream_edit_interval_sec,
                    min_chars_delta=settings.stream_min_chars_delta,
                    prefix="",
                )
                async for chunk in astream_answer(user_text):
                    await aggregator.feed(chunk)
                await aggregator.flush(final=True)
                final_text = aggregator.get_text()
                logger.info(f"Final answer to user {user_id}: {final_text!r}")
        except Exception as e:
            logger.exception(f"Error while processing message from {user_id}: {e}")
            await sent.edit_text(f"❌ Ошибка: {e}")
            return

    await dp.start_polling(bot)


class _TelegramAggregator:
    """Coalesces multiple small chunks into periodic message edits."""

    def __init__(
        self,
        edit_fn: Callable[[str], Awaitable[Message]],
        interval: float,
        min_chars_delta: int,
        prefix: str = "",
    ) -> None:
        self._edit_fn = edit_fn
        self._interval = interval
        self._min_delta = min_chars_delta
        self._prefix = prefix
        self._buffer: list[str] = []
        self._accum: list[str] = []
        self._last_edit = time.monotonic()
        self._last_sent_text: str = ""
        self._changed: bool = False

    def get_text(self) -> str:
        return self._last_sent_text

    async def feed(self, chunk: str) -> None:
        if not chunk:
            return
        self._buffer.append(chunk)
        self._changed = True
        now = time.monotonic()
        if (now - self._last_edit) >= self._interval or sum(len(c) for c in self._buffer) >= self._min_delta:
            await self._emit()

    async def flush(self, final: bool = False) -> None:
        # Выполним только если действительно есть изменения
        if self._changed:
            await self._emit(final=final)

    async def _emit(self, final: bool = False) -> None:
        if not self._changed:
            return
        # Переносим буфер в общий аккумулятор и формируем текст
        self._accum.extend(self._buffer)
        self._buffer.clear()
        text = self._prefix + "".join(self._accum)

        # Пропускаем редактирование, если текст не изменился
        if text == self._last_sent_text:
            self._changed = False
            return

        self._last_edit = time.monotonic()
        try:
            await self._edit_fn(text)
        except TelegramBadRequest as e:
            # Игнорируем known-case: "message is not modified"
            if "message is not modified" in str(e).lower():
                pass
            else:
                raise
        finally:
            # Считаем, что состояние синхронизировано
            self._last_sent_text = text
            self._changed = False