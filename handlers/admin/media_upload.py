"""
Admin: Add new media via a multi-step FSM flow.
Flow: category → subcategory → (surah|sheikh|album) → title → title_ar → upload file
"""
from __future__ import annotations

import math
from typing import Optional

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import config
from bot.database import db
from bot.keyboards import AdminKeyboards
from bot.utils.states import AddMediaStates

router = Router()


# ─── Step 1: Choose Category ──────────────────────────────────────────────────
@router.callback_query(F.data == "admin_add_media")
async def cb_add_media_start(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    categories = await db.get_categories()
    text = "➕ <b>إضافة محتوى جديد</b>\n\nاختر التصنيف الرئيسي:"
    await callback.message.edit_text(
        text,
        reply_markup=AdminKeyboards.choose_category(categories),
        parse_mode="HTML",
    )
    await state.set_state(AddMediaStates.choosing_category)
    await callback.answer()


# ─── Step 2: Category chosen → choose subcategory ─────────────────────────────
@router.callback_query(AddMediaStates.choosing_category, F.data.startswith("adm_cat:"))
async def cb_choose_subcategory(callback: CallbackQuery, state: FSMContext):
    cat_id = int(callback.data.split(":")[1])
    await state.update_data(category_id=cat_id)

    cat = await db.get_category(cat_id)
    subcategories = await db.get_subcategories(cat_id)

    text = (
        f"📁 <b>{cat['name_ar']}</b>\n\n"
        "اختر القسم الفرعي:"
    )
    await callback.message.edit_text(
        text,
        reply_markup=AdminKeyboards.choose_subcategory(subcategories, cat_id),
        parse_mode="HTML",
    )
    await state.set_state(AddMediaStates.choosing_subcategory)
    await callback.answer()


# ─── Step 3: Subcategory chosen → choose surah / sheikh / album ───────────────
@router.callback_query(
    AddMediaStates.choosing_subcategory,
    F.data.regexp(r"^adm_sub:\d+:cat:\d+$"),
)
async def cb_choose_target(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    sub_id = int(parts[1])
    cat_id = int(parts[3])
    await state.update_data(subcategory_id=sub_id, category_id=cat_id)

    sub = await db.get_subcategory(sub_id)
    slug = sub.get("slug", "") if sub else ""

    if slug == "surahs":
        # Ask to choose a surah
        total = await db.get_surah_count()
        surahs = await db.get_surahs(page=1)
        total_pages = math.ceil(total / config.PAGE_SIZE)
        await callback.message.edit_text(
            "📖 اختر السورة:",
            reply_markup=AdminKeyboards.choose_surah(surahs, sub_id, cat_id, 1, total_pages),
            parse_mode="HTML",
        )
        await state.update_data(surah_page=1)
        await state.set_state(AddMediaStates.choosing_surah)

    elif slug == "sheikhs":
        sheikhs = await db.get_sheikhs()
        await callback.message.edit_text(
            "🎙️ اختر الشيخ:",
            reply_markup=AdminKeyboards.choose_sheikh(sheikhs, sub_id, cat_id),
            parse_mode="HTML",
        )
        await state.set_state(AddMediaStates.choosing_sheikh)

    else:
        # Albums (landscapes etc.)
        albums = await db.get_albums(sub_id)
        await callback.message.edit_text(
            "🗂️ اختر الألبوم:",
            reply_markup=AdminKeyboards.choose_album(albums, sub_id, cat_id),
            parse_mode="HTML",
        )
        await state.set_state(AddMediaStates.choosing_album)

    await callback.answer()


# ─── Surah page navigation (during add media) ─────────────────────────────────
@router.callback_query(
    AddMediaStates.choosing_surah,
    F.data.startswith("adm_surah_page:"),
)
async def cb_surah_page_admin(callback: CallbackQuery, state: FSMContext):
    # adm_surah_page:{page}:sub:{sub_id}:cat:{cat_id}
    parts = callback.data.split(":")
    page   = int(parts[1])
    sub_id = int(parts[3])
    cat_id = int(parts[5])

    total = await db.get_surah_count()
    surahs = await db.get_surahs(page=page)
    total_pages = math.ceil(total / config.PAGE_SIZE)

    await callback.message.edit_text(
        f"📖 اختر السورة (الصفحة {page}/{total_pages}):",
        reply_markup=AdminKeyboards.choose_surah(surahs, sub_id, cat_id, page, total_pages),
        parse_mode="HTML",
    )
    await state.update_data(surah_page=page)
    await callback.answer()


# ─── Surah chosen ─────────────────────────────────────────────────────────────
@router.callback_query(
    AddMediaStates.choosing_surah,
    F.data.startswith("adm_surah:"),
)
async def cb_surah_chosen(callback: CallbackQuery, state: FSMContext):
    # adm_surah:{id}:sub:{sub_id}:cat:{cat_id}
    parts = callback.data.split(":")
    surah_id = int(parts[1])  # 0 = skip
    sub_id   = int(parts[3])
    cat_id   = int(parts[5])

    await state.update_data(surah_id=surah_id if surah_id else None)
    await _ask_title(callback, state)
    await callback.answer()


# ─── Sheikh chosen ────────────────────────────────────────────────────────────
@router.callback_query(
    AddMediaStates.choosing_sheikh,
    F.data.startswith("adm_sheikh:"),
)
async def cb_sheikh_chosen(callback: CallbackQuery, state: FSMContext):
    # adm_sheikh:{id}:sub:{sub_id}:cat:{cat_id}:sur:{surah_id}
    parts = callback.data.split(":")
    sheikh_id = int(parts[1])  # 0 = skip
    await state.update_data(sheikh_id=sheikh_id if sheikh_id else None)
    await _ask_title(callback, state)
    await callback.answer()


# ─── Album chosen ─────────────────────────────────────────────────────────────
@router.callback_query(
    AddMediaStates.choosing_album,
    F.data.startswith("adm_album:"),
)
async def cb_album_chosen(callback: CallbackQuery, state: FSMContext):
    # adm_album:{id}:sub:{sub_id}:cat:{cat_id}
    parts = callback.data.split(":")
    album_id = int(parts[1])  # 0 = skip
    await state.update_data(album_id=album_id if album_id else None)
    await _ask_title(callback, state)
    await callback.answer()


async def _ask_title(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await callback.message.edit_text(
        "✏️ <b>العنوان بالإنجليزية</b>\n\n"
        "أدخل عنوان الملف بالإنجليزية (أو اضغط /skip لتخطي):",
        reply_markup=AdminKeyboards.cancel(),
        parse_mode="HTML",
    )
    await state.set_state(AddMediaStates.entering_title)


# ─── Enter title (English) ────────────────────────────────────────────────────
@router.message(AddMediaStates.entering_title, F.text)
async def msg_enter_title(message: Message, state: FSMContext):
    title = message.text.strip()
    if title.lower() == "/skip":
        title = "untitled"
    await state.update_data(title=title)
    await message.answer(
        "✏️ <b>العنوان بالعربية</b>\n\n"
        "أدخل عنوان الملف بالعربية (أو /skip للتخطي):",
        reply_markup=AdminKeyboards.cancel(),
        parse_mode="HTML",
    )
    await state.set_state(AddMediaStates.entering_title_ar)


# ─── Enter title (Arabic) ─────────────────────────────────────────────────────
@router.message(AddMediaStates.entering_title_ar, F.text)
async def msg_enter_title_ar(message: Message, state: FSMContext):
    title_ar = message.text.strip()
    if title_ar.lower() == "/skip":
        title_ar = ""
    await state.update_data(title_ar=title_ar)
    await message.answer(
        "📎 <b>رفع الملف</b>\n\n"
        "الآن أرسل الملف المراد إضافته:\n"
        "• يمكن إرسال فيديو 🎬\n"
        "• صورة 🖼️\n"
        "• ملف 📄\n"
        "• صوت 🎵",
        reply_markup=AdminKeyboards.cancel(),
        parse_mode="HTML",
    )
    await state.set_state(AddMediaStates.uploading_file)


# ─── Receive uploaded file ─────────────────────────────────────────────────────
@router.message(
    AddMediaStates.uploading_file,
    F.video | F.photo | F.document | F.audio,
)
async def msg_receive_file(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()

    # Extract file info
    file_id = file_unique_id = ""
    media_type = "document"
    file_size = duration = 0
    thumbnail_id = ""

    if message.video:
        file_id        = message.video.file_id
        file_unique_id = message.video.file_unique_id
        media_type     = "video"
        file_size      = message.video.file_size or 0
        duration       = message.video.duration or 0
        if message.video.thumbnail:
            thumbnail_id = message.video.thumbnail.file_id

    elif message.photo:
        photo          = message.photo[-1]  # highest resolution
        file_id        = photo.file_id
        file_unique_id = photo.file_unique_id
        media_type     = "photo"
        file_size      = photo.file_size or 0

    elif message.audio:
        file_id        = message.audio.file_id
        file_unique_id = message.audio.file_unique_id
        media_type     = "audio"
        file_size      = message.audio.file_size or 0
        duration       = message.audio.duration or 0
        if message.audio.thumbnail:
            thumbnail_id = message.audio.thumbnail.file_id

    elif message.document:
        file_id        = message.document.file_id
        file_unique_id = message.document.file_unique_id
        media_type     = "document"
        file_size      = message.document.file_size or 0
        if message.document.thumbnail:
            thumbnail_id = message.document.thumbnail.file_id

    # Save to DB
    media_id = await db.add_media(
        category_id    = data.get("category_id"),
        subcategory_id = data.get("subcategory_id"),
        surah_id       = data.get("surah_id"),
        sheikh_id      = data.get("sheikh_id"),
        album_id       = data.get("album_id"),
        title          = data.get("title", "untitled"),
        title_ar       = data.get("title_ar", ""),
        media_type     = media_type,
        file_id        = file_id,
        file_unique_id = file_unique_id,
        file_size      = file_size,
        duration       = duration,
        thumbnail_id   = thumbnail_id,
    )

    # Log admin action
    await db.log_admin_action(
        message.from_user.id,
        f"أضاف ملفاً جديداً: {data.get('title', 'untitled')}",
        "media",
        media_id,
    )

    await state.clear()
    await message.answer(
        f"✅ <b>تم إضافة الملف بنجاح!</b>\n\n"
        f"🆔 رقم الملف: <code>{media_id}</code>\n"
        f"📌 العنوان: {data.get('title', '')}\n"
        f"📊 النوع: {media_type}",
        reply_markup=AdminKeyboards.back_to_admin(),
        parse_mode="HTML",
    )


@router.message(AddMediaStates.uploading_file)
async def msg_wrong_file(message: Message, state: FSMContext):
    await message.answer(
        "⚠️ الرجاء إرسال ملف صالح (فيديو، صورة، ملف، أو صوت).",
        reply_markup=AdminKeyboards.cancel(),
    )
