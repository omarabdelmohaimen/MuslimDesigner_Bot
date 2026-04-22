"""
Admin: Broadcast messages to all users.
"""
from __future__ import annotations

import asyncio
from typing import List

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.database import db
from bot.keyboards import AdminKeyboards
from bot.utils.states import BroadcastStates

router = Router()


@router.callback_query(F.data == "admin_broadcast")
async def cb_broadcast_start(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "📢 <b>إرسال بث للمستخدمين</b>\n\n"
        "أرسل الرسالة التي تريد بثها:\n"
        "يمكنك إرسال نص، صورة، فيديو، أو ملف.",
        reply_markup=AdminKeyboards.cancel(),
        parse_mode="HTML",
    )
    await state.set_state(BroadcastStates.entering_message)
    await callback.answer()


@router.message(BroadcastStates.entering_message)
async def msg_broadcast_content(message: Message, state: FSMContext):
    """Store the broadcast message and ask for confirmation."""
    # Determine message type
    if message.text:
        await state.update_data(
            msg_type="text",
            msg_text=message.text,
            msg_entities=message.entities,
        )
        preview = message.text[:200]
    elif message.photo:
        await state.update_data(
            msg_type="photo",
            file_id=message.photo[-1].file_id,
            caption=message.caption or "",
        )
        preview = f"[صورة] {message.caption or ''}"
    elif message.video:
        await state.update_data(
            msg_type="video",
            file_id=message.video.file_id,
            caption=message.caption or "",
        )
        preview = f"[فيديو] {message.caption or ''}"
    elif message.document:
        await state.update_data(
            msg_type="document",
            file_id=message.document.file_id,
            caption=message.caption or "",
        )
        preview = f"[ملف] {message.caption or ''}"
    else:
        await message.answer(
            "⚠️ نوع الرسالة غير مدعوم. أرسل نصاً أو صورة أو فيديو.",
            reply_markup=AdminKeyboards.cancel(),
        )
        return

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ إرسال الآن", callback_data="broadcast_confirm"),
        InlineKeyboardButton(text="❌ إلغاء",      callback_data="admin_menu"),
    )

    users_count = await db.get_user_count()
    await message.answer(
        f"📢 <b>تأكيد الإرسال</b>\n\n"
        f"سيتم إرسال الرسالة إلى <b>{users_count}</b> مستخدم.\n\n"
        f"<b>معاينة:</b>\n{preview[:300]}",
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )
    await state.set_state(BroadcastStates.confirming)


@router.callback_query(BroadcastStates.confirming, F.data == "broadcast_confirm")
async def cb_broadcast_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    await state.clear()

    users = await db.get_all_users()
    total_sent   = 0
    total_failed = 0

    status_msg = await callback.message.edit_text(
        f"📤 جارٍ الإرسال إلى {len(users)} مستخدم...\n⏳ يرجى الانتظار.",
        parse_mode="HTML",
    )

    for user in users:
        try:
            tg_id = user["telegram_id"]
            msg_type = data.get("msg_type", "text")

            if msg_type == "text":
                await bot.send_message(
                    chat_id=tg_id,
                    text=data.get("msg_text", ""),
                    parse_mode="HTML",
                )
            elif msg_type == "photo":
                await bot.send_photo(
                    chat_id=tg_id,
                    photo=data.get("file_id"),
                    caption=data.get("caption", ""),
                    parse_mode="HTML",
                )
            elif msg_type == "video":
                await bot.send_video(
                    chat_id=tg_id,
                    video=data.get("file_id"),
                    caption=data.get("caption", ""),
                    parse_mode="HTML",
                )
            elif msg_type == "document":
                await bot.send_document(
                    chat_id=tg_id,
                    document=data.get("file_id"),
                    caption=data.get("caption", ""),
                    parse_mode="HTML",
                )

            total_sent += 1
            # Rate limit: 30 msgs/sec max
            await asyncio.sleep(0.05)

        except Exception:
            total_failed += 1

    # Log broadcast
    admin_user = await db.get_user(callback.from_user.id)
    if admin_user:
        await db.execute(
            """INSERT INTO broadcast_logs (admin_id, message_text, total_sent, total_failed)
               VALUES (?,?,?,?)""",
            (admin_user["id"], str(data.get("msg_text", data.get("caption", "")))[:500],
             total_sent, total_failed),
        )

    await db.log_admin_action(
        callback.from_user.id,
        f"أرسل بثاً: {total_sent} ناجح، {total_failed} فشل",
    )

    await callback.message.edit_text(
        f"✅ <b>اكتمل الإرسال!</b>\n\n"
        f"✉️ تم الإرسال: <b>{total_sent}</b>\n"
        f"❌ فشل: <b>{total_failed}</b>",
        reply_markup=AdminKeyboards.back_to_admin(),
        parse_mode="HTML",
    )
    await callback.answer()
