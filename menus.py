from __future__ import annotations

from math import ceil
from typing import Sequence

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 كرومات", callback_data="u:cat:chroma")],
        [InlineKeyboardButton("🎨 تصاميم", callback_data="u:cat:designs")],
        [InlineKeyboardButton("🌿 مناظر طبيعية", callback_data="u:nature")],
    ])


def category_menu(category: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📖 سور", callback_data=f"u:type:{category}:surahs")],
        [InlineKeyboardButton("🎤 شيوخ", callback_data=f"u:type:{category}:sheikhs")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="u:home")],
    ])


def admin_dashboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ إضافة محتوى", callback_data="a:add")],
        [InlineKeyboardButton("🗑️ حذف محتوى", callback_data="a:del")],
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="a:stats")],
        [InlineKeyboardButton("🏠 الصفحة الرئيسية", callback_data="a:home")],
    ])


def admin_category_menu(action: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 كرومات", callback_data=f"a:cat:{action}:chroma")],
        [InlineKeyboardButton("🎨 تصاميم", callback_data=f"a:cat:{action}:designs")],
        [InlineKeyboardButton("🌿 مناظر طبيعية", callback_data=f"a:cat:{action}:nature")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="a:panel")],
    ])


def admin_type_menu(action: str, category: str) -> InlineKeyboardMarkup:
    if category == "nature":
        return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data=f"a:{action}")]])

    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📖 سور", callback_data=f"a:type:{action}:{category}:surahs")],
        [InlineKeyboardButton("🎤 شيوخ", callback_data=f"a:type:{action}:{category}:sheikhs")],
        [InlineKeyboardButton("🔙 رجوع", callback_data=f"a:{action}")],
    ])


def paginate(items: Sequence[str], page: int, per_page: int):
    total_pages = max(1, ceil(len(items) / per_page))
    page = max(0, min(page, total_pages - 1))
    start = page * per_page
    end = start + per_page
    return page, total_pages, list(items[start:end])


def paginated_targets_menu(
    items: Sequence[str],
    page: int,
    per_page: int,
    item_prefix: str,
    page_prefix: str,
    back_callback: str,
) -> InlineKeyboardMarkup:
    page, total_pages, chunk = paginate(items, page, per_page)
    keyboard = []

    for i, label in enumerate(chunk):
        absolute_index = page * per_page + i
        keyboard.append([InlineKeyboardButton(label, callback_data=f"{item_prefix}:{page}:{absolute_index}")])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"{page_prefix}:page:{page - 1}"))
    nav.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="noop"))
    if page + 1 < total_pages:
        nav.append(InlineKeyboardButton("➡️", callback_data=f"{page_prefix}:page:{page + 1}"))
    keyboard.append(nav)
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data=back_callback)])
    return InlineKeyboardMarkup(keyboard)


def item_list_menu(
    items_count: int,
    item_prefix: str,
    page_prefix: str,
    back_callback: str,
    page: int = 0,
    per_page: int = 8,
) -> InlineKeyboardMarkup:
    total_pages = max(1, ceil(max(1, items_count) / per_page))
    page = max(0, min(page, total_pages - 1))
    start = page * per_page
    end = min(items_count, start + per_page)

    keyboard = []
    for idx in range(start, end):
        keyboard.append([InlineKeyboardButton(f"🗑️ حذف العنصر {idx + 1}", callback_data=f"{item_prefix}:{page}:{idx}")])

    keyboard.append([InlineKeyboardButton("🧹 حذف الكل", callback_data=f"{item_prefix}:clear:{page}")])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"{page_prefix}:page:{page - 1}"))
    nav.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="noop"))
    if page + 1 < total_pages:
        nav.append(InlineKeyboardButton("➡️", callback_data=f"{page_prefix}:page:{page + 1}"))
    keyboard.append(nav)
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data=back_callback)])
    return InlineKeyboardMarkup(keyboard)


def upload_menu(done_callback: str, cancel_callback: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تم", callback_data=done_callback)],
        [InlineKeyboardButton("❌ إلغاء", callback_data=cancel_callback)],
    ])
