"""
Admin: List, edit, delete media items.
"""
from __future__ import annotations

import math
from typing import Optional

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import config
from bot.database import db
from bot.keyboards import AdminKeyboards
from bot.utils.states import EditMediaStates, SearchStates
from bot.utils.helpers import build_media_caption, media_type_label

router = Router()


# ─── List all media ────────────────────────────────────────────────────────────
@router.callback_query(F.data == "admin_list_media")
async def cb_list_media(callback: CallbackQuery):
    await _show_media_list(callback, page=1)


@router.callback_query(F.data.startswith("adm_media_list:"))
async def cb_media_list_page(callback: CallbackQuery):
    page = int(callback.data.split(":")[1])
    await _show_media_list(callback, page=page)


async def _show_media_list(callback: CallbackQuery, page: int = 1):
    total = await db.count_media()
    media = await db.get_media(page=page)
    total_pages = math.ceil(total / config.PAGE_SIZE) if total else 1

    if not media:
        await callback.message.edit_text(
            "📭 <b>لا توجد ملفات بعد.</b>\n\nأضف محتوى جديداً من القائمة.",
            reply_markup=AdminKeyboards.back_to_admin(),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    lines = [f"📋 <b>قائمة المحتوى</b> — الصفحة {page}/{total_pages} (إجمالي: {total})\n"]
    for item in media:
        title = item.get("title_ar") or item.get("title", "—")
        icon  = {"video":"🎬","photo":"🖼️","document":"📄","audio":"🎵"}.get(item["media_type"],"📦")
        lines.append(
            f"{icon} <code>#{item['id']}</code> {title}"
            + (f" | سورة: {item['surah_name_ar']}" if item.get("surah_name_ar") else "")
            + (f" | شيخ: {item['sheikh_name_ar']}" if item.get("sheikh_name_ar") else "")
        )
        lines.append(f"    ↳ /media_{item['id']}")

    text = "\n".join(lines)
    kb   = AdminKeyboards.media_list_nav(page, total_pages)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


# ─── View single media (via /media_ID command) ────────────────────────────────
@router.message(F.text.regexp(r"^/media_\d+$"))
async def cmd_view_media(message: Message):
    media_id = int(message.text.split("_")[1])
    item = await db.get_media_item(media_id)
    if not item:
        await message.answer("❌ الملف غير موجود.")
        return

    caption = build_media_caption(item)
    kb = AdminKeyboards.media_item_actions(media_id)
    await message.answer(
        f"📁 <b>تفاصيل الملف #{media_id}</b>\n\n{caption}",
        reply_markup=kb,
        parse_mode="HTML",
    )


# ─── Edit title ────────────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("adm_edit_title:"))
async def cb_edit_title(callback: CallbackQuery, state: FSMContext):
    media_id = int(callback.data.split(":")[1])
    await state.update_data(media_id=media_id)
    await callback.message.edit_text(
        "✏️ أدخل العنوان الجديد بالعربية:",
        reply_markup=AdminKeyboards.cancel("admin_list_media"),
        parse_mode="HTML",
    )
    await state.set_state(EditMediaStates.editing_title_ar)
    await callback.answer()


@router.message(EditMediaStates.editing_title_ar, F.text)
async def msg_edit_title(message: Message, state: FSMContext):
    data = await state.get_data()
    media_id = data.get("media_id")
    new_title = message.text.strip()

    await db.update_media(media_id, title_ar=new_title)
    await db.log_admin_action(
        message.from_user.id,
        f"عدّل عنوان الملف إلى: {new_title}",
        "media",
        media_id,
    )
    await state.clear()
    await message.answer(
        f"✅ تم تحديث العنوان إلى: <b>{new_title}</b>",
        reply_markup=AdminKeyboards.back_to_admin(),
        parse_mode="HTML",
    )


# ─── Delete media ──────────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("adm_del_confirm:"))
async def cb_del_confirm(callback: CallbackQuery):
    media_id = int(callback.data.split(":")[1])
    item = await db.get_media_item(media_id)
    title = item.get("title_ar") or item.get("title", "—") if item else "—"
    await callback.message.edit_text(
        f"⚠️ هل أنت متأكد من حذف الملف:\n<b>{title}</b> (#{media_id})؟",
        reply_markup=AdminKeyboards.confirm_delete(media_id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm_del:"))
async def cb_del_media(callback: CallbackQuery):
    media_id = int(callback.data.split(":")[1])
    item = await db.get_media_item(media_id)
    title = item.get("title_ar") or item.get("title", "—") if item else "—"

    await db.delete_media(media_id)
    await db.log_admin_action(
        callback.from_user.id,
        f"حذف ملفاً: {title}",
        "media",
        media_id,
    )
    await callback.message.edit_text(
        f"🗑️ تم حذف الملف: <b>{title}</b>",
        reply_markup=AdminKeyboards.back_to_admin(),
        parse_mode="HTML",
    )
    await callback.answer("✅ تم الحذف")


# ─── Search ────────────────────────────────────────────────────────────────────
@router.callback_query(F.data == "admin_search")
async def cb_admin_search(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "🔍 <b>بحث في المحتوى</b>\n\nأدخل كلمة البحث:",
        reply_markup=AdminKeyboards.cancel(),
        parse_mode="HTML",
    )
    await state.set_state(SearchStates.entering_query)
    await callback.answer()


@router.message(SearchStates.entering_query, F.text)
async def msg_search_query(message: Message, state: FSMContext):
    query = message.text.strip()
    results = await db.search_media(query)
    total = await db.search_media_count(query)
    await state.clear()

    if not results:
        await message.answer(
            f"🔍 نتائج البحث عن: <b>{query}</b>\n\n❌ لم يتم العثور على نتائج.",
            reply_markup=AdminKeyboards.back_to_admin(),
            parse_mode="HTML",
        )
        return

    lines = [f"🔍 نتائج البحث عن: <b>{query}</b> ({total} نتيجة)\n"]
    for item in results:
        title = item.get("title_ar") or item.get("title", "—")
        icon  = {"video":"🎬","photo":"🖼️","document":"📄","audio":"🎵"}.get(item["media_type"],"📦")
        lines.append(f"{icon} <code>#{item['id']}</code> {title} ↳ /media_{item['id']}")

    await message.answer(
        "\n".join(lines),
        reply_markup=AdminKeyboards.back_to_admin(),
        parse_mode="HTML",
    )
