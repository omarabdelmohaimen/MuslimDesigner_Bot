"""
Admin panel main menu and statistics.
"""
from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from bot.config import config
from bot.database import db
from bot.keyboards import AdminKeyboards

router = Router()


async def send_admin_menu(target, text: str = ""):
    """Send/edit the admin panel menu."""
    default_text = (
        "🛡️ <b>لوحة تحكم المشرف</b>\n\n"
        "مرحباً بك في لوحة الإدارة.\n"
        "اختر إجراءً:"
    )
    kb = AdminKeyboards.main_menu()
    if isinstance(target, Message):
        await target.answer(text or default_text, reply_markup=kb, parse_mode="HTML")
    elif isinstance(target, CallbackQuery):
        await target.message.edit_text(text or default_text, reply_markup=kb, parse_mode="HTML")
        await target.answer()


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    user_id = message.from_user.id
    # Double-check authorization
    if user_id not in config.ADMIN_IDS:
        db_user = await db.get_user(user_id)
        if not db_user or not db_user.get("is_admin"):
            await message.answer("⛔️ هذا الأمر للمشرفين فقط.")
            return
    await send_admin_menu(message)


@router.callback_query(F.data == "admin_menu")
async def cb_admin_menu(callback: CallbackQuery):
    await send_admin_menu(callback)


@router.callback_query(F.data == "admin_stats")
async def cb_admin_stats(callback: CallbackQuery):
    stats = await db.get_stats()
    text = (
        "📊 <b>إحصائيات البوت</b>\n\n"
        f"👥 المستخدمون:    <b>{stats['users']}</b>\n"
        f"🎬 الملفات:       <b>{stats['media']}</b>\n"
        f"📁 التصنيفات:     <b>{stats['categories']}</b>\n"
        f"📂 الأقسام:       <b>{stats['subcategories']}</b>\n"
        f"📖 السور:         <b>{stats['surahs']}</b>\n"
        f"🎙️ المشايخ:       <b>{stats['sheikhs']}</b>\n"
        f"🗂️ الألبومات:     <b>{stats['albums']}</b>\n"
        f"⬇️ التحميلات:     <b>{stats['downloads']}</b>\n"
    )
    await callback.message.edit_text(
        text, reply_markup=AdminKeyboards.back_to_admin(), parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_logs")
async def cb_admin_logs(callback: CallbackQuery):
    logs = await db.get_admin_logs(limit=15)
    if not logs:
        text = "📜 <b>سجل الإجراءات</b>\n\nلا توجد إجراءات مسجلة بعد."
    else:
        lines = ["📜 <b>آخر الإجراءات الإدارية</b>\n"]
        for log in logs:
            name = log.get("first_name") or log.get("username") or "مجهول"
            lines.append(
                f"• [{log['created_at'][:16]}] <b>{name}</b>\n"
                f"  ↳ {log['action']}"
                + (f" ({log['target_type']} #{log['target_id']})" if log.get("target_id") else "")
            )
        text = "\n".join(lines)

    await callback.message.edit_text(
        text, reply_markup=AdminKeyboards.back_to_admin(), parse_mode="HTML"
    )
    await callback.answer()
