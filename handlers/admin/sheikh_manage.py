"""
Admin: Manage Sheikhs (add, edit, delete, list).
"""
from __future__ import annotations

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database import db
from bot.keyboards import AdminKeyboards
from bot.utils.states import AddSheikhStates, EditSheikhStates

router = Router()


# ─── List Sheikhs ─────────────────────────────────────────────────────────────
@router.callback_query(F.data == "admin_sheikhs")
async def cb_admin_sheikhs(callback: CallbackQuery):
    sheikhs = await db.get_sheikhs()
    text = f"🎙️ <b>إدارة المشايخ</b>\nإجمالي: {len(sheikhs)} شيخ"
    await callback.message.edit_text(
        text,
        reply_markup=AdminKeyboards.sheikhs_list(sheikhs),
        parse_mode="HTML",
    )
    await callback.answer()


# ─── View Sheikh ──────────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("adm_view_sheikh:"))
async def cb_view_sheikh(callback: CallbackQuery):
    sheikh_id = int(callback.data.split(":")[1])
    sh = await db.get_sheikh(sheikh_id)
    if not sh:
        await callback.answer("الشيخ غير موجود!", show_alert=True)
        return

    text = (
        f"🎙️ <b>تفاصيل الشيخ</b>\n\n"
        f"الاسم عربي: <b>{sh['name_ar']}</b>\n"
        f"الاسم إنجليزي: <b>{sh['name_en']}</b>\n"
        f"السيرة: {sh.get('bio') or '—'}"
    )
    await callback.message.edit_text(
        text,
        reply_markup=AdminKeyboards.sheikh_actions(sheikh_id),
        parse_mode="HTML",
    )
    await callback.answer()


# ─── Add Sheikh ───────────────────────────────────────────────────────────────
@router.callback_query(F.data == "adm_add_sheikh")
async def cb_add_sheikh(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "🎙️ <b>إضافة شيخ جديد</b>\n\nأدخل اسم الشيخ بالعربية:",
        reply_markup=AdminKeyboards.cancel("admin_sheikhs"),
        parse_mode="HTML",
    )
    await state.set_state(AddSheikhStates.entering_name_ar)
    await callback.answer()


@router.message(AddSheikhStates.entering_name_ar, F.text)
async def msg_sheikh_name_ar(message: Message, state: FSMContext):
    await state.update_data(name_ar=message.text.strip())
    await message.answer(
        "🎙️ أدخل اسم الشيخ بالإنجليزية:",
        reply_markup=AdminKeyboards.cancel("admin_sheikhs"),
    )
    await state.set_state(AddSheikhStates.entering_name_en)


@router.message(AddSheikhStates.entering_name_en, F.text)
async def msg_sheikh_name_en(message: Message, state: FSMContext):
    await state.update_data(name_en=message.text.strip())
    await message.answer(
        "🎙️ أدخل نبذة عن الشيخ (أو /skip للتخطي):",
        reply_markup=AdminKeyboards.cancel("admin_sheikhs"),
    )
    await state.set_state(AddSheikhStates.entering_bio)


@router.message(AddSheikhStates.entering_bio, F.text)
async def msg_sheikh_bio(message: Message, state: FSMContext):
    bio = message.text.strip()
    if bio.lower() == "/skip":
        bio = ""
    data = await state.get_data()
    sheikh_id = await db.add_sheikh(
        name_ar = data["name_ar"],
        name_en = data["name_en"],
        bio     = bio,
    )
    await db.log_admin_action(
        message.from_user.id,
        f"أضاف شيخاً: {data['name_ar']}",
        "sheikh",
        sheikh_id,
    )
    await state.clear()
    await message.answer(
        f"✅ تم إضافة الشيخ <b>{data['name_ar']}</b> بنجاح!",
        reply_markup=AdminKeyboards.back_to_admin(),
        parse_mode="HTML",
    )


# ─── Edit Sheikh ──────────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("adm_edit_sheikh:"))
async def cb_edit_sheikh(callback: CallbackQuery, state: FSMContext):
    sheikh_id = int(callback.data.split(":")[1])
    await state.update_data(sheikh_id=sheikh_id)
    await callback.message.edit_text(
        "✏️ أرسل التعديل بالصيغة:\n"
        "<code>name_ar|الاسم الجديد</code>\n"
        "<code>name_en|New Name</code>\n"
        "<code>bio|السيرة الجديدة</code>",
        reply_markup=AdminKeyboards.cancel("admin_sheikhs"),
        parse_mode="HTML",
    )
    await state.set_state(EditSheikhStates.entering_value)
    await callback.answer()


@router.message(EditSheikhStates.entering_value, F.text)
async def msg_edit_sheikh_value(message: Message, state: FSMContext):
    data = await state.get_data()
    sheikh_id = data.get("sheikh_id")
    try:
        field, value = message.text.strip().split("|", 1)
        field = field.strip()
        value = value.strip()
        if field not in ("name_ar", "name_en", "bio"):
            raise ValueError
        await db.update_sheikh(sheikh_id, **{field: value})
        await db.log_admin_action(
            message.from_user.id,
            f"عدّل {field} للشيخ #{sheikh_id}",
            "sheikh",
            sheikh_id,
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


# ─── Delete Sheikh ────────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("adm_del_sheikh_confirm:"))
async def cb_del_sheikh_confirm(callback: CallbackQuery):
    sheikh_id = int(callback.data.split(":")[1])
    sh = await db.get_sheikh(sheikh_id)
    name = sh["name_ar"] if sh else "—"
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="✅ نعم احذف", callback_data=f"adm_del_sheikh:{sheikh_id}"),
        InlineKeyboardButton(text="❌ إلغاء",    callback_data="admin_sheikhs"),
    )
    await callback.message.edit_text(
        f"⚠️ هل تريد حذف الشيخ <b>{name}</b>؟",
        reply_markup=b.as_markup(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm_del_sheikh:"))
async def cb_del_sheikh(callback: CallbackQuery):
    sheikh_id = int(callback.data.split(":")[1])
    sh = await db.get_sheikh(sheikh_id)
    name = sh["name_ar"] if sh else "—"
    await db.delete_sheikh(sheikh_id)
    await db.log_admin_action(
        callback.from_user.id, f"حذف شيخاً: {name}", "sheikh", sheikh_id
    )
    await callback.message.edit_text(
        f"🗑️ تم حذف الشيخ <b>{name}</b>.",
        reply_markup=AdminKeyboards.back_to_admin(),
        parse_mode="HTML",
    )
    await callback.answer("✅ تم الحذف")
