"""
Browse handlers: categories → subcategories → surahs/sheikhs/albums → media.
"""
from __future__ import annotations

import math
from typing import Optional

from aiogram import Router, F
from aiogram.types import CallbackQuery

from bot.database import db
from bot.keyboards import UserKeyboards
from bot.config import config

router = Router()


# ─── Category selected ────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("cat:"))
async def cb_category(callback: CallbackQuery):
    cat_id = int(callback.data.split(":")[1])
    category = await db.get_category(cat_id)
    if not category:
        await callback.answer("التصنيف غير موجود!", show_alert=True)
        return

    subcategories = await db.get_subcategories(cat_id)
    text = f"{category['icon']} <b>{category['name_ar']}</b>\n\nاختر قسماً:"
    kb = UserKeyboards.subcategory_menu(subcategories, cat_id)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


# ─── Subcategory selected ──────────────────────────────────────────────────────
@router.callback_query(F.data.regexp(r"^sub:\d+:cat:\d+$"))
async def cb_subcategory(callback: CallbackQuery):
    parts = callback.data.split(":")
    sub_id = int(parts[1])
    cat_id = int(parts[3])

    sub = await db.get_subcategory(sub_id)
    cat = await db.get_category(cat_id)
    if not sub or not cat:
        await callback.answer("القسم غير موجود!", show_alert=True)
        return

    slug = sub.get("slug", "")

    # Surahs sub-section
    if slug == "surahs":
        await _show_surah_list(callback, sub_id, cat_id, page=1)

    # Sheikhs sub-section
    elif slug == "sheikhs":
        sheikhs = await db.get_sheikhs()
        ctx = f"sub:{sub_id}:cat:{cat_id}"
        text = f"🎙️ <b>المشايخ - {cat['name_ar']}</b>\n\nاختر شيخاً:"
        if not sheikhs:
            text = (
                f"🎙️ <b>المشايخ - {cat['name_ar']}</b>\n\n"
                "⏳ <i>سيتم إضافة المشايخ قريباً.\n"
                "تواصل مع المشرف لإضافة المشايخ من لوحة الإدارة.</i>"
            )
        kb = UserKeyboards.sheikh_list(sheikhs, ctx)
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

    # Natural landscapes / albums
    else:
        albums = await db.get_albums(sub_id)
        ctx = f"sub:{sub_id}:cat:{cat_id}"
        text = f"{sub['icon']} <b>{sub['name_ar']}</b>\n\nاختر ألبوماً:"
        kb = UserKeyboards.album_list(albums, sub_id, back_cb=f"cat:{cat_id}")
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

    await callback.answer()


# ─── Surah page navigation ─────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("surah_page:"))
async def cb_surah_page(callback: CallbackQuery):
    # surah_page:{page}:{context}
    parts = callback.data.split(":", 2)
    page = int(parts[1])
    ctx  = parts[2]  # e.g. "sub:3:cat:1"
    ctx_parts = ctx.split(":")
    sub_id = int(ctx_parts[1])
    cat_id = int(ctx_parts[3])
    await _show_surah_list(callback, sub_id, cat_id, page)
    await callback.answer()


async def _show_surah_list(callback: CallbackQuery, sub_id: int, cat_id: int, page: int):
    cat = await db.get_category(cat_id)
    sub = await db.get_subcategory(sub_id)
    surahs  = await db.get_surahs(page)
    total   = await db.get_surah_count()
    ctx     = f"sub:{sub_id}:cat:{cat_id}"

    icon = cat.get("icon", "📖") if cat else "📖"
    cat_name = cat.get("name_ar", "") if cat else ""
    total_pages = math.ceil(total / config.PAGE_SIZE)

    text = (
        f"{icon} <b>{cat_name}</b> — <b>السور القرآنية</b>\n"
        f"الصفحة {page} من {total_pages} | إجمالي: {total} سورة\n\n"
        "اختر سورة:"
    )
    kb = UserKeyboards.surah_list(surahs, page, total, ctx)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


# ─── Surah selected → show media ──────────────────────────────────────────────
@router.callback_query(F.data.startswith("surah:"))
async def cb_surah(callback: CallbackQuery):
    # surah:{surah_id}:{context}
    parts = callback.data.split(":", 2)
    surah_id = int(parts[1])
    ctx = parts[2]  # sub:{sub_id}:cat:{cat_id}
    ctx_parts = ctx.split(":")
    sub_id = int(ctx_parts[1])
    cat_id = int(ctx_parts[3])

    surah = await db.get_surah(surah_id)
    sub   = await db.get_subcategory(sub_id)
    cat   = await db.get_category(cat_id)

    if not surah:
        await callback.answer("السورة غير موجودة!", show_alert=True)
        return

    back_cb = f"media_ctx:surah:{surah_id}:sub:{sub_id}:cat:{cat_id}:p:1"
    await _show_media_list(callback, cat_id, sub_id, surah_id, None, None, 1, back_cb)
    await callback.answer()


# ─── Sheikh selected → show media ─────────────────────────────────────────────
@router.callback_query(F.data.startswith("sheikh:"))
async def cb_sheikh(callback: CallbackQuery):
    # sheikh:{sheikh_id}:{context}
    parts = callback.data.split(":", 2)
    sheikh_id = int(parts[1])
    ctx = parts[2]
    ctx_parts = ctx.split(":")
    sub_id = int(ctx_parts[1])
    cat_id = int(ctx_parts[3])

    sheikh = await db.get_sheikh(sheikh_id)
    if not sheikh:
        await callback.answer("الشيخ غير موجود!", show_alert=True)
        return

    back_cb = f"media_ctx:sheikh:{sheikh_id}:sub:{sub_id}:cat:{cat_id}:p:1"
    await _show_media_list(callback, cat_id, sub_id, None, sheikh_id, None, 1, back_cb)
    await callback.answer()


# ─── Album selected → show media ──────────────────────────────────────────────
@router.callback_query(F.data.startswith("album:"))
async def cb_album(callback: CallbackQuery):
    # album:{album_id}:sub:{sub_id}
    parts = callback.data.split(":")
    album_id = int(parts[1])
    sub_id   = int(parts[3])

    sub = await db.get_subcategory(sub_id)
    cat_id = sub["category_id"] if sub else 0

    album = await db.get_album(album_id)
    if not album:
        await callback.answer("الألبوم غير موجود!", show_alert=True)
        return

    back_cb = f"media_ctx:album:{album_id}:sub:{sub_id}:cat:{cat_id}:p:1"
    await _show_media_list(callback, cat_id, sub_id, None, None, album_id, 1, back_cb)
    await callback.answer()


# ─── Media page navigation ─────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("media_page:"))
async def cb_media_page(callback: CallbackQuery):
    # media_page:{page}:{back_cb}
    rest = callback.data[len("media_page:"):]
    page_str, back_cb = rest.split(":", 1)
    page = int(page_str)

    # Reconstruct filters from back_cb: media_ctx:TYPE:ID:sub:X:cat:Y:p:N
    await _process_media_ctx(callback, back_cb.replace(f":p:{page-1}", f":p:{page}").replace(f":p:{page+1}", f":p:{page}"), page)
    await callback.answer()


@router.callback_query(F.data.startswith("media_ctx:"))
async def cb_media_ctx(callback: CallbackQuery):
    parts = callback.data.split(":")
    # media_ctx:TYPE:ID:sub:SUB_ID:cat:CAT_ID:p:PAGE
    entity_type = parts[1]
    entity_id   = int(parts[2])
    sub_id      = int(parts[4])
    cat_id      = int(parts[6])
    page        = int(parts[8])

    surah_id  = entity_id if entity_type == "surah"  else None
    sheikh_id = entity_id if entity_type == "sheikh" else None
    album_id  = entity_id if entity_type == "album"  else None

    back_cb = callback.data
    await _show_media_list(callback, cat_id, sub_id, surah_id, sheikh_id, album_id, page, back_cb)
    await callback.answer()


async def _process_media_ctx(callback: CallbackQuery, back_cb: str, page: int):
    parts = back_cb.split(":")
    entity_type = parts[1]
    entity_id   = int(parts[2])
    sub_id      = int(parts[4])
    cat_id      = int(parts[6])

    surah_id  = entity_id if entity_type == "surah"  else None
    sheikh_id = entity_id if entity_type == "sheikh" else None
    album_id  = entity_id if entity_type == "album"  else None

    new_back_cb = f"media_ctx:{entity_type}:{entity_id}:sub:{sub_id}:cat:{cat_id}:p:{page}"
    await _show_media_list(callback, cat_id, sub_id, surah_id, sheikh_id, album_id, page, new_back_cb)


async def _show_media_list(
    callback: CallbackQuery,
    cat_id: int,
    sub_id: int,
    surah_id: Optional[int],
    sheikh_id: Optional[int],
    album_id: Optional[int],
    page: int,
    back_cb: str,
):
    cat   = await db.get_category(cat_id)
    sub   = await db.get_subcategory(sub_id)

    media = await db.get_media(
        category_id=cat_id,
        subcategory_id=sub_id,
        surah_id=surah_id,
        sheikh_id=sheikh_id,
        album_id=album_id,
        page=page,
    )
    total = await db.count_media(
        category_id=cat_id,
        subcategory_id=sub_id,
        surah_id=surah_id,
        sheikh_id=sheikh_id,
        album_id=album_id,
    )
    total_pages_count = math.ceil(total / config.PAGE_SIZE) if total else 1

    # Build breadcrumb header
    cat_name = cat.get("name_ar", "") if cat else ""
    sub_name = sub.get("name_ar", "") if sub else ""

    header_parts = [f"<b>{cat_name}</b>"]
    if sub_name:
        header_parts.append(sub_name)

    if surah_id:
        surah = await db.get_surah(surah_id)
        if surah:
            header_parts.append(f"سورة {surah['name_ar']}")
    elif sheikh_id:
        sheikh = await db.get_sheikh(sheikh_id)
        if sheikh:
            header_parts.append(sheikh["name_ar"])
    elif album_id:
        album = await db.get_album(album_id)
        if album:
            header_parts.append(album["name_ar"])

    breadcrumb = " ← ".join(header_parts)

    text = (
        f"📂 {breadcrumb}\n"
        f"الصفحة {page}/{total_pages_count} | "
        f"إجمالي الملفات: {total}\n\n"
        "اختر ملفاً:"
    )
    kb = UserKeyboards.media_list(media, page, total, back_cb)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


# ─── Back button handling ──────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("back:"))
async def cb_back(callback: CallbackQuery):
    target = callback.data[5:]  # strip "back:"
    # Simulate clicking on the target
    callback.data = target
    # Route based on target type
    if target.startswith("sub:"):
        await cb_subcategory(callback)
    elif target.startswith("cat:"):
        await cb_category(callback)
    elif target.startswith("media_ctx:"):
        await cb_media_ctx(callback)
    else:
        await callback.answer()


# ─── No-op button ─────────────────────────────────────────────────────────────
@router.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery):
    await callback.answer()
