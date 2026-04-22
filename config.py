"""
Configuration file for the Quran Media Bot.
All settings are loaded from environment variables or .env file.
"""
import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    # ─── Telegram ────────────────────────────────────────────────────────────
    BOT_TOKEN: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))
    ADMIN_IDS: List[int] = field(
        default_factory=lambda: [
            int(x.strip())
            for x in os.getenv("ADMIN_IDS", "").split(",")
            if x.strip().isdigit()
        ]
    )

    # ─── Database ────────────────────────────────────────────────────────────
    DB_PATH: str = field(default_factory=lambda: os.getenv("DB_PATH", "bot/quran_bot.db"))

    # ─── Pagination ──────────────────────────────────────────────────────────
    PAGE_SIZE: int = 10

    # ─── Bot Info ────────────────────────────────────────────────────────────
    BOT_NAME: str = "بوت القرآن الكريم"
    BOT_VERSION: str = "1.0.0"


config = Config()
