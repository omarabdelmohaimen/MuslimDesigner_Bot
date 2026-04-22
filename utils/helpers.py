"""
Utility helpers used across the bot.
"""
from __future__ import annotations

import math
from typing import Optional

from bot.config import config


def total_pages(total: int, page_size: int = config.PAGE_SIZE) -> int:
    """Return the total number of pages given a total item count."""
    return max(1, math.ceil(total / page_size))


def format_file_size(size_bytes: int) -> str:
    """Human-readable file size."""
    if not size_bytes:
        return "غير معروف"
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def format_duration(seconds: int) -> str:
    """Format seconds into MM:SS or HH:MM:SS."""
    if not seconds:
        return ""
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def media_type_label(media_type: str) -> str:
    return {
        "video":    "📹 فيديو",
        "photo":    "🖼️ صورة",
        "document": "📄 ملف",
        "audio":    "🎵 صوت",
    }.get(media_type, "📦 ملف")


def build_media_caption(item: dict) -> str:
    """Build a rich caption for a media item."""
    lines = []
    title = item.get("title_ar") or item.get("title", "")
    if title:
        lines.append(f"📌 <b>{title}</b>")

    if item.get("surah_name_ar"):
        lines.append(f"📖 السورة: {item['surah_name_ar']} ({item.get('surah_number','')})")
    if item.get("sheikh_name_ar"):
        lines.append(f"🎙️ الشيخ: {item['sheikh_name_ar']}")
    if item.get("album_name_ar"):
        lines.append(f"🗂️ الألبوم: {item['album_name_ar']}")
    if item.get("category_name_ar"):
        lines.append(f"📁 التصنيف: {item['category_name_ar']}")

    lines.append(f"📊 النوع: {media_type_label(item.get('media_type',''))}")

    if item.get("file_size"):
        lines.append(f"💾 الحجم: {format_file_size(item['file_size'])}")
    if item.get("duration"):
        lines.append(f"⏱️ المدة: {format_duration(item['duration'])}")
    if item.get("description"):
        lines.append(f"\n📝 {item['description']}")

    lines.append(f"\n⬇️ التحميلات: {item.get('download_count', 0)}")
    return "\n".join(lines)


def is_admin(user_id: int) -> bool:
    """Quick check from config list (before DB check)."""
    return user_id in config.ADMIN_IDS


def paginate_text(items: list, page: int, page_size: int = config.PAGE_SIZE):
    """Return a slice of items for the current page."""
    start = (page - 1) * page_size
    return items[start: start + page_size]
