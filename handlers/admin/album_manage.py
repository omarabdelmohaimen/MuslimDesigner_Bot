"""
Admin: Manage albums for Natural Landscapes section.
"""
from __future__ import annotations

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database import db
from bot.keyboards import AdminKeyboards
from bot.utils.states import AddAlbumStates

router = Router()


# ─── List Albums ──────────────────────────────────────────────────────────────
@router.callback_query(F.data == "admin_albums")
async def cb_admin_albums(callback: CallbackQuery):
    albums = await db.get_albums()
    text = f"🗂️ <b>إدارة الألبومات</b>\nإجمالي: {len(albums)} ألبوم"
    await callback.message.edit_text(
        text,
        reply_markup=AdminKeyboards.albums_list(albums),
        parse_mode="HTML",
    )
    await callback.answer()


# ─── View Album ───────────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("adm_view_album:"))
async def cb_view_album(callback: CallbackQuery):
    album_id = int(callback.data.split(":")[1])
    a = await db.get_album(album_id)
    if not a:
        await callback.answer("الألبوم غير موجود!", show_alert=True)
        return

    # Count media in this album
    media_count = await db.count_media(album_id=album_id)
    text = (
        f"🗂️ <b>تفاصيل الألبوم</b>\n\n"
        f"الاسم: <b>{a['name_ar']}</b>\n"
        f"الاسم بالإنجليزية: <b>{a['name']}</b>\n"
        f"الوصف: {a.get('description') or '—'}\n"
        f"عدد الملفات: <b>{media_count}</b>"
    )
    await callback.message.edit_text(
        text,
        reply_markup=AdminKeyboards.album_actions(album_id),
        parse_mode="HTML",
    )
    await callback.answer()


# ─── Add Album ────────────────────────────────────────────────────────────────
@router.callback_query(F.data == "adm_add_album")
async def cb_add_album(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "🗂️ <b>إضافة ألبوم جديد</b>\n\nأدخل اسم الألبوم بالإنجليزية:",
        reply_markup=AdminKeyboards.cancel("admin_albums"),
        parse_mode="HTML",
    )
    await state.set_state(AddAlbumStates.entering_name)
    await callback.answer()


@router.message(AddAlbumStates.entering_name, F.text)
async def msg_album_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await message.answer(
        "🗂️ أدخل اسم الألبوم بالعربية:",
        reply_markup=AdminKeyboards.cancel("admin_albums"),
    )
    await state.set_state(AddAlbumStates.entering_name_ar)


@router.message(AddAlbumStates.entering_name_ar, F.text)
async def msg_album_name_ar(message: Message, state: FSMContext):
    await state.update_data(name_ar=message.text.strip())
    await message.answer(
        "🗂️ أدخل وصفاً للألبوم (أو /skip للتخطي):",
        reply_markup=AdminKeyboards.cancel("admin_albums"),
    )
    await state.set_state(AddAlbumStates.entering_desc)


@router.message(AddAlbumStates.entering_desc, F.text)
async def msg_album_desc(message: Message, state: FSMContext):
    desc = message.text.strip()
    if desc.lower() == "/skip":
        desc = ""
    data = await state.get_data()

    # Get landscapes subcategory
    landscape_cat = await db.get_category_by_slug("landscapes")
    sub_id = None
    if landscape_cat:
        subs = await db.get_subcategories(landscape_cat["id"])
        if subs:
            sub_id = subs[0]["id"]

    album_id = await db.add_album(
        name           = data["name"],
        name_ar        = data["name_ar"],
        subcategory_id = sub_id,
        description    = desc,
    )
    await db.log_admin_action(
        message.from_user.id,
        f"أضاف ألبوم: {data['name_ar']}",
        "album",
        album_id,
    )
    await state.clear()
    await message.answer(
        f"✅ تم إضافة الألبوم <b>{data['name_ar']}</b> بنجاح!",
        reply_markup=AdminKeyboards.back_to_admin(),
        parse_mode="HTML",
    )


# ─── Edit Album ───────────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("adm_edit_album:"))
async def cb_edit_album(callback: CallbackQuery, state: FSMContext):
    album_id = int(callback.data.split(":")[1])
    await state.update_data(album_id=album_id)
    await callback.message.edit_text(
        "✏️ أرسل التعديل:\n"
        "<code>name|New Name</code>\n"
        "<code>name_ar|الاسم الجديد</code>\n"
        "<code>description|وصف جديد</code>",
        reply_markup=AdminKeyboards.cancel("admin_albums"),
        parse_mode="HTML",
    )
    # Reuse EditSheikhStates structure by using FSM directly
    from aiogram.fsm.state import State, StatesGroup
    await state.set_state("edit_album_value")
    await callback.answer()


@router.message(F.text, lambda m: True)
async def _catch_album_edit(message: Message, state: FSMContext):
    current = await state.get_state()
    if current != "edit_album_value":
        return  # Don't handle, let other handlers catch

    data = await state.get_data()
    album_id = data.get("album_id")
    if not album_id:
        return

    try:
        field, value = message.text.strip().split("|", 1)
        field = field.strip()
        value = value.strip()
        if field not in ("name", "name_ar", "description"):
            raise ValueError
        await db.update_album(album_id, **{field: value})
        await db.log_admin_action(
            message.from_user.id,
            f"عدّل {field} للألبوم #{album_id}",
            "album",
            album_id,
        )
        await state.clear()
        await message.answer(
            "✅ تم التحديث!",
            reply_markup=AdminKeyboards.back_to_admin(),
        )
    except Exception:
        await message.answer(
            "⚠️ صيغة غير صحيحة. استخدم: <code>field|value</code>",
            parse_mode="HTML",
        )


# ─── Delete Album ─────────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("adm_del_album_confirm:"))
async def cb_del_album_confirm(callback: CallbackQuery):
    album_id = int(callback.data.split(":")[1])
    a = await db.get_album(album_id)
    name = a["name_ar"] if a else "—"
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="✅ نعم احذف", callback_data=f"adm_del_album:{album_id}"),
        InlineKeyboardButton(text="❌ إلغاء",    callback_data="admin_albums"),
    )
    await callback.message.edit_text(
        f"⚠️ هل تريد حذف الألبوم <b>{name}</b>؟",
        reply_markup=b.as_markup(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm_del_album:"))
async def cb_del_album(callback: CallbackQuery):
    album_id = int(callback.data.split(":")[1])
    a = await db.get_album(album_id)
    name = a["name_ar"] if a else "—"
    await db.delete_album(album_id)
    await db.log_admin_action(
        callback.from_user.id, f"حذف ألبوم: {name}", "album", album_id
    )
    await callback.message.edit_text(
        f"🗑️ تم حذف الألبوم <b>{name}</b>.",
        reply_markup=AdminKeyboards.back_to_admin(),
        parse_mode="HTML",
    )
    await callback.answer("✅ تم الحذف")
