from __future__ import annotations

from math import ceil
from typing import Sequence, Tuple

from telegram import ReplyKeyboardMarkup


def _kb(rows):
    return ReplyKeyboardMarkup(
        rows,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="اختر من القائمة",
    )


def main_menu() -> ReplyKeyboardMarkup:
    return _kb([
        ["كرومات", "تصاميم"],
        ["مناظر طبيعية"],
    ])


def category_menu(category: str) -> ReplyKeyboardMarkup:
    return _kb([
        ["سور", "شيوخ"],
        ["بحث عن سورة"],
        ["رجوع", "الرئيسية"],
    ])


def admin_dashboard() -> ReplyKeyboardMarkup:
    return _kb([
        ["إضافة محتوى", "حذف محتوى"],
        ["إضافة شيخ جديد"],
        ["الإحصائيات"],
        ["الرئيسية"],
    ])


def admin_category_menu(action: str) -> ReplyKeyboardMarkup:
    return _kb([
        ["كرومات", "تصاميم"],
        ["مناظر طبيعية"],
        ["رجوع", "الرئيسية"],
    ])


def admin_type_menu(action: str, category: str) -> ReplyKeyboardMarkup:
    if category == "nature":
        return _kb([["رجوع", "الرئيسية"]])
    return _kb([
        ["سور", "شيوخ"],
        ["رجوع", "الرئيسية"],
    ])


def paginate(items: Sequence[str], page: int, per_page: int):
    total_pages = max(1, ceil(len(items) / per_page))
    page = max(0, min(page, total_pages - 1))
    start = page * per_page
    end = start + per_page
    return page, total_pages, list(items[start:end])


def targets_menu(
    items: Sequence[str],
    page: int,
    per_page: int,
    back_label: str = "رجوع",
    home_label: str = "الرئيسية",
) -> Tuple[ReplyKeyboardMarkup, int, int, list]:
    page, total_pages, chunk = paginate(items, page, per_page)
    rows = [[name] for name in chunk]
    nav = []
    if page > 0:
        nav.append("السابق")
    if page + 1 < total_pages:
        nav.append("التالي")
    if nav:
        rows.append(nav)
    rows.append([back_label, home_label])
    return _kb(rows), page, total_pages, chunk


def items_menu(
    items_count: int,
    page: int,
    per_page: int,
    back_label: str = "رجوع",
    home_label: str = "الرئيسية",
    include_clear: bool = True,
):
    total_pages = max(1, ceil(max(1, items_count) / per_page))
    page = max(0, min(page, total_pages - 1))
    start = page * per_page
    end = min(items_count, start + per_page)
    rows = []
    for idx in range(start, end):
        rows.append([f"حذف {idx + 1}"])
    nav = []
    if page > 0:
        nav.append("السابق")
    if page + 1 < total_pages:
        nav.append("التالي")
    if include_clear:
        nav.append("حذف الكل")
    if nav:
        rows.append(nav)
    rows.append([back_label, home_label])
    return _kb(rows), page, total_pages, list(range(start, end))


def upload_menu() -> ReplyKeyboardMarkup:
    return _kb([
        ["تم", "إلغاء"],
    ])


def clear_confirm_menu() -> ReplyKeyboardMarkup:
    return _kb([
        ["نعم، احذف الكل", "إلغاء"],
    ])
