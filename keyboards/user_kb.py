"""
User-facing inline keyboard builder.
All labels are in Arabic for a smooth Arabic UX.
"""
from __future__ import annotations

import math
from typing import List, Dict, Optional

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.config import config

# ─── Navigation constants ──────────────────────────────────────────────────────
NAV_HOME  = "🏠 الرئيسية"
NAV_BACK  = "🔙 رجوع"
NAV_PREV  = "◀️ السابق"
NAV_NEXT  = "▶️ التالي"
NAV_DL    = "⬇️ تحميل"


class UserKeyboards:
    """Factory class for all user keyboards."""

    # ── Main Menu ──────────────────────────────────────────────────────────────
    @staticmethod
    def main_menu(categories: List[Dict]) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        for cat in categories:
            builder.button(
                text=f"{cat['icon']} {cat['name_ar']}",
                callback_data=f"cat:{cat['id']}",
            )
        builder.adjust(1)
        return builder.as_markup()

    # ── Category → Subcategories ───────────────────────────────────────────────
    @staticmethod
    def subcategory_menu(
        subcategories: List[Dict], category_id: int
    ) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        for sub in subcategories:
            builder.button(
                text=f"{sub['icon']} {sub['name_ar']}",
                callback_data=f"sub:{sub['id']}:cat:{category_id}",
            )
        builder.button(text=NAV_HOME, callback_data="home")
        builder.adjust(1)
        return builder.as_markup()

    # ── Surah List (paginated) ─────────────────────────────────────────────────
    @staticmethod
    def surah_list(
        surahs: List[Dict],
        page: int,
        total: int,
        context: str,  # e.g. "chr_sub:3" or "des_sub:5"
    ) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        total_pages = math.ceil(total / config.PAGE_SIZE)

        for s in surahs:
            builder.button(
                text=f"{s['number']}. {s['name_ar']}",
                callback_data=f"surah:{s['id']}:{context}",
            )
        builder.adjust(2)

        # Pagination row
        nav_buttons = []
        if page > 1:
            nav_buttons.append(
                InlineKeyboardButton(
                    text=NAV_PREV,
                    callback_data=f"surah_page:{page-1}:{context}",
                )
            )
        if page < total_pages:
            nav_buttons.append(
                InlineKeyboardButton(
                    text=NAV_NEXT,
                    callback_data=f"surah_page:{page+1}:{context}",
                )
            )
        if nav_buttons:
            builder.row(*nav_buttons)

        builder.row(
            InlineKeyboardButton(text=NAV_BACK, callback_data=f"back:{context}"),
            InlineKeyboardButton(text=NAV_HOME, callback_data="home"),
        )
        return builder.as_markup()

    # ── Sheikh List ────────────────────────────────────────────────────────────
    @staticmethod
    def sheikh_list(
        sheikhs: List[Dict], context: str
    ) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        if sheikhs:
            for sh in sheikhs:
                builder.button(
                    text=f"🎙️ {sh['name_ar']}",
                    callback_data=f"sheikh:{sh['id']}:{context}",
                )
        else:
            builder.button(
                text="⏳ قريباً - سيتم إضافة المشايخ قريباً",
                callback_data="noop",
            )
        builder.adjust(1)
        builder.row(
            InlineKeyboardButton(text=NAV_BACK, callback_data=f"back:{context}"),
            InlineKeyboardButton(text=NAV_HOME, callback_data="home"),
        )
        return builder.as_markup()

    # ── Album List ─────────────────────────────────────────────────────────────
    @staticmethod
    def album_list(
        albums: List[Dict], subcategory_id: int, back_cb: str
    ) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        if albums:
            for a in albums:
                builder.button(
                    text=f"🗂️ {a['name_ar']}",
                    callback_data=f"album:{a['id']}:sub:{subcategory_id}",
                )
        else:
            builder.button(
                text="📭 لا توجد ألبومات بعد",
                callback_data="noop",
            )
        builder.adjust(1)
        builder.row(
            InlineKeyboardButton(text=NAV_BACK, callback_data=back_cb),
            InlineKeyboardButton(text=NAV_HOME, callback_data="home"),
        )
        return builder.as_markup()

    # ── Media List (paginated) ─────────────────────────────────────────────────
    @staticmethod
    def media_list(
        media_items: List[Dict],
        page: int,
        total: int,
        back_cb: str,
    ) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        total_pages = math.ceil(total / config.PAGE_SIZE) if total else 1

        if not media_items:
            builder.button(text="📭 لا يوجد محتوى بعد", callback_data="noop")
        else:
            for item in media_items:
                icon = _media_icon(item["media_type"])
                label = item.get("title_ar") or item["title"]
                builder.button(
                    text=f"{icon} {label}",
                    callback_data=f"media:{item['id']}:{back_cb}",
                )
        builder.adjust(1)

        # Pagination
        nav_buttons = []
        if page > 1:
            nav_buttons.append(
                InlineKeyboardButton(
                    text=NAV_PREV,
                    callback_data=f"media_page:{page-1}:{back_cb}",
                )
            )
        if page < total_pages:
            nav_buttons.append(
                InlineKeyboardButton(
                    text=NAV_NEXT,
                    callback_data=f"media_page:{page+1}:{back_cb}",
                )
            )
        if nav_buttons:
            builder.row(*nav_buttons)

        builder.row(
            InlineKeyboardButton(text=NAV_BACK, callback_data=back_cb),
            InlineKeyboardButton(text=NAV_HOME, callback_data="home"),
        )
        return builder.as_markup()

    # ── Media Detail ───────────────────────────────────────────────────────────
    @staticmethod
    def media_detail(media_id: int, back_cb: str) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.button(
            text=NAV_DL,
            callback_data=f"download:{media_id}:{back_cb}",
        )
        builder.row(
            InlineKeyboardButton(text=NAV_BACK, callback_data=back_cb),
            InlineKeyboardButton(text=NAV_HOME, callback_data="home"),
        )
        return builder.as_markup()

    # ── After Download ─────────────────────────────────────────────────────────
    @staticmethod
    def after_download(back_cb: str) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text=NAV_BACK, callback_data=back_cb),
            InlineKeyboardButton(text=NAV_HOME, callback_data="home"),
        )
        return builder.as_markup()

    # ── Confirm / Cancel ───────────────────────────────────────────────────────
    @staticmethod
    def confirm(yes_cb: str, no_cb: str = "admin_menu") -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="✅ تأكيد", callback_data=yes_cb),
            InlineKeyboardButton(text="❌ إلغاء", callback_data=no_cb),
        )
        return builder.as_markup()

    # ── Simple back to home ────────────────────────────────────────────────────
    @staticmethod
    def home_only() -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.button(text=NAV_HOME, callback_data="home")
        return builder.as_markup()


def _media_icon(media_type: str) -> str:
    return {
        "video":    "🎬",
        "photo":    "🖼️",
        "document": "📄",
        "audio":    "🎵",
    }.get(media_type, "📦")
