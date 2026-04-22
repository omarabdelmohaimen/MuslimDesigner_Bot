"""
Main entry point for the Quran Media Bot.
Registers all routers, middlewares, and starts polling.
"""
from __future__ import annotations

import asyncio
import logging
import sys
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

# ─── Path setup ───────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.config import config
from bot.database import db
from bot.middlewares import UserMiddleware, AdminMiddleware

# ─── Handlers ─────────────────────────────────────────────────────────────────
from bot.handlers.user.start  import router as start_router
from bot.handlers.user.browse import router as browse_router
from bot.handlers.user.media  import router as media_router

from bot.handlers.admin.menu          import router as admin_menu_router
from bot.handlers.admin.media_upload  import router as media_upload_router
from bot.handlers.admin.media_manage  import router as media_manage_router
from bot.handlers.admin.surah_manage  import router as surah_manage_router
from bot.handlers.admin.sheikh_manage import router as sheikh_manage_router
from bot.handlers.admin.album_manage  import router as album_manage_router
from bot.handlers.admin.broadcast     import router as broadcast_router

logging.basicConfig(
    level    = logging.INFO,
    format   = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt  = "%Y-%m-%d %H:%M:%S",
    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot/bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


async def main() -> None:
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN is not set! Add it to your .env file.")
        sys.exit(1)

    # ── Connect DB ─────────────────────────────────────────────────────────────
    logger.info("Connecting to database …")
    await db.connect()
    logger.info("Database ready ✓")

    # ── Bot + Dispatcher ───────────────────────────────────────────────────────
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # ── Global Middleware (register / update user on every event) ──────────────
    dp.message.middleware(UserMiddleware())
    dp.callback_query.middleware(UserMiddleware())

    # ── Admin Middleware applied to admin routers ──────────────────────────────
    for admin_router in [
        admin_menu_router,
        media_upload_router,
        media_manage_router,
        surah_manage_router,
        sheikh_manage_router,
        album_manage_router,
        broadcast_router,
    ]:
        admin_router.message.middleware(AdminMiddleware())
        admin_router.callback_query.middleware(AdminMiddleware())

    # ── Register Routers (order matters: more specific first) ──────────────────
    dp.include_router(start_router)
    dp.include_router(browse_router)
    dp.include_router(media_router)
    dp.include_router(admin_menu_router)
    dp.include_router(media_upload_router)
    dp.include_router(media_manage_router)
    dp.include_router(surah_manage_router)
    dp.include_router(sheikh_manage_router)
    dp.include_router(album_manage_router)
    dp.include_router(broadcast_router)

    # ── Start polling ──────────────────────────────────────────────────────────
    logger.info(f"Starting {config.BOT_NAME} v{config.BOT_VERSION} …")
    await bot.delete_webhook(drop_pending_updates=True)

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await db.close()
        await bot.session.close()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
