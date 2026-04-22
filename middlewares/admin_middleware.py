"""
Middleware / filter that blocks non-admin users from admin handlers.
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from bot.config import config
from bot.database import db


class AdminMiddleware(BaseMiddleware):
    """Attached only to admin-specific routers."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = None
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user

        if user is None:
            return  # skip unknown event types

        # Check config ADMIN_IDS first (fast), then DB
        if user.id not in config.ADMIN_IDS:
            db_user = await db.get_user(user.id)
            if not db_user or not db_user.get("is_admin"):
                if isinstance(event, CallbackQuery):
                    await event.answer("⛔️ هذا القسم للمشرفين فقط.", show_alert=True)
                elif isinstance(event, Message):
                    await event.answer("⛔️ هذا القسم للمشرفين فقط.")
                return  # block the handler

        return await handler(event, data)
