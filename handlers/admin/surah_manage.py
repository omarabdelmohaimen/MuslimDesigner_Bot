"""
Admin: Manage Quranic surahs (add, edit, delete, list).
"""
from __future__ import annotations

import math

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import config
from bot.database import db
from bot.keyboards import AdminKeyboards
from bot.utils.states import AddSurahStates, EditSurahStates

router = Router()


# ─── List Surahs ──────────────────────────────────────────────────────────────
@router.callback_query(F.data == "admin_surahs")
async def cb_admin_surahs(callback: CallbackQuery):
    await _show_surahs_list(callback, page=1)
    await callback.answer()


@router.callback_query(F.data.startswith("adm_surahs_page:"))
async def cb_surahs_page(callback: CallbackQuery):
    page = int(callback.data.split(":")[1])
    await _show_surahs_list(callback, page=page)
    await callback.answer()


async def _show_surahs_list(callback: CallbackQuery, page: int):
    total = await db.get_surah_count()
    surahs = await db.get_surahs(page=page)
    total_pages = math.ceil(total / config.PAGE_SIZE) if total else 1

    text = f"📖 <b>إدارة السور القرآنية</b>\nالصفحة {page}/{total_pages} | إجمالي: {total}"
    kb = AdminKeyboards.surahs_list(surahs, page, total_pages)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


# ─── View Surah ───────────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("adm_view_surah:"))
async def cb_view_surah(callback: CallbackQuery):
    surah_id = int(callback.data.split(":")[1])
    s = await db.get_surah(surah_id)
    if not s:
        await callback.answer("السورة غير موجودة!", show_alert=True)
        return

    text = (
        f"📖 <b>تفاصيل السورة</b>\n\n"
        f"الرقم:      <b>{s['number']}</b>\n"
        f"الاسم عربي: <b>{s['name_ar']}</b>\n"
        f"الاسم إنجليزي: <b>{s['name_en']}</b>\n"
        f"عدد الآيات: <b>{s['verses']}</b>"
    )
    await callback.message.edit_text(
        text,
        reply_markup=AdminKeyboards.surah_actions(surah_id),
        parse_mode="HTML",
    )
    await callback.answer()


# ─── Add Surah ────────────────────────────────────────────────────────────────
@router.callback_query(F.data == "adm_add_surah")
async def cb_add_surah(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "📖 <b>إضافة سورة جديدة</b>\n\nأدخل رقم السورة (1-114):",
        reply_markup=AdminKeyboards.cancel("admin_surahs"),
        parse_mode="HTML",
    )
    await state.set_state(AddSurahStates.entering_number)
    await callback.answer()


@router.message(AddSurahStates.entering_number, F.text)
async def msg_surah_number(message: Message, state: FSMContext):
    try:
        num = int(message.text.strip())
        if num < 1 or num > 114:
            raise ValueError
        await state.update_data(number=num)
        await message.answer(
            "📖 أدخل اسم السورة بالعربية:",
            reply_markup=AdminKeyboards.cancel("admin_surahs"),
        )
        await state.set_state(AddSurahStates.entering_name_ar)
    except ValueError:
        await message.answer("⚠️ رقم غير صالح. أدخل رقماً بين 1 و 114:")


@router.message(AddSurahStates.entering_name_ar, F.text)
async def msg_surah_name_ar(message: Message, state: FSMContext):
    await state.update_data(name_ar=message.text.strip())
    await message.answer(
        "📖 أدخل اسم السورة بالإنجليزية:",
        reply_markup=AdminKeyboards.cancel("admin_surahs"),
    )
    await state.set_state(AddSurahStates.entering_name_en)


@router.message(AddSurahStates.entering_name_en, F.text)
async def msg_surah_name_en(message: Message, state: FSMContext):
    await state.update_data(name_en=message.text.strip())
    await message.answer(
        "📖 أدخل عدد آيات السورة:",
        reply_markup=AdminKeyboards.cancel("admin_surahs"),
    )
    await state.set_state(AddSurahStates.entering_verses)


@router.message(AddSurahStates.entering_verses, F.text)
async def msg_surah_verses(message: Message, state: FSMContext):
    try:
        verses = int(message.text.strip())
        data = await state.get_data()
        surah_id = await db.add_surah(
            number  = data["number"],
            name_ar = data["name_ar"],
            name_en = data["name_en"],
            verses  = verses,
        )
        await db.log_admin_action(
            message.from_user.id,
            f"أضاف سورة: {data['name_ar']}",
            "surah",
            surah_id,
        )
        await state.clear()
        await message.answer(
            f"✅ تم إضافة سورة <b>{data['name_ar']}</b> بنجاح!",
            reply_markup=AdminKeyboards.back_to_admin(),
            parse_mode="HTML",
        )
    except ValueError:
        await message.answer("⚠️ أدخل رقماً صحيحاً:")


# ─── Edit Surah ───────────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("adm_edit_surah:"))
async def cb_edit_surah(callback: CallbackQuery, state: FSMContext):
    surah_id = int(callback.data.split(":")[1])
    await state.update_data(surah_id=surah_id, editing="surah")
    await callback.message.edit_text(
        "✏️ ما الذي تريد تعديله؟\n\n"
        "أرسل:\n"
        "<code>name_ar|الاسم الجديد بالعربية</code>\n"
        "<code>name_en|New Name in English</code>\n"
        "<code>verses|عدد الآيات</code>",
        reply_markup=AdminKeyboards.cancel("admin_surahs"),
        parse_mode="HTML",
    )
    await state.set_state(EditSurahStates.entering_value)
    await callback.answer()


@router.message(EditSurahStates.entering_value, F.text)
async def msg_edit_surah_value(message: Message, state: FSMContext):
    data = await state.get_data()
    surah_id = data.get("surah_id")

    try:
        field, value = message.text.strip().split("|", 1)
        field = field.strip()
        value = value.strip()

        if field not in ("name_ar", "name_en", "verses"):
            raise ValueError("Invalid field")

        if field == "verses":
            value = int(value)

        await db.update_surah(surah_id, **{field: value})
        await db.log_admin_action(
            message.from_user.id,
            f"عدّل حقل {field} في السورة #{surah_id}",
            "surah",
            surah_id,
        )
        await state.clear()
        await message.answer(
            f"✅ تم تحديث السورة بنجاح!",
            reply_markup=AdminKeyboards.back_to_admin(),
        )
    except Exception as e:
        await message.answer(
            f"⚠️ صيغة غير صحيحة. استخدم:\n<code>field|value</code>\n\nالحقول المتاحة: name_ar, name_en, verses",
            parse_mode="HTML",
        )


# ─── Delete Surah ─────────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("adm_del_surah_confirm:"))
async def cb_del_surah_confirm(callback: CallbackQuery):
    surah_id = int(callback.data.split(":")[1])
    s = await db.get_surah(surah_id)
    name = s["name_ar"] if s else "—"
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ نعم احذف", callback_data=f"adm_del_surah:{surah_id}"),
        InlineKeyboardButton(text="❌ إلغاء",    callback_data="admin_surahs"),
    )
    await callback.message.edit_text(
        f"⚠️ هل تريد حذف سورة <b>{name}</b>؟",
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm_del_surah:"))
async def cb_del_surah(callback: CallbackQuery):
    surah_id = int(callback.data.split(":")[1])
    s = await db.get_surah(surah_id)
    name = s["name_ar"] if s else "—"
    await db.delete_surah(surah_id)
    await db.log_admin_action(
        callback.from_user.id, f"حذف سورة: {name}", "surah", surah_id
    )
    await callback.message.edit_text(
        f"🗑️ تم حذف سورة <b>{name}</b>.",
        reply_markup=AdminKeyboards.back_to_admin(),
        parse_mode="HTML",
    )
    await callback.answer("✅ تم الحذف")
