"""
Media detail and download handlers.
"""
from __future__ import annotations

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery

from bot.database import db
from bot.keyboards import UserKeyboards
from bot.utils.helpers import build_media_caption

router = Router()


# ─── Media Item Selected ───────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("media:"))
async def cb_media_detail(callback: CallbackQuery, bot: Bot):
    # media:{media_id}:{back_cb}
    rest = callback.data[6:]
    # Split carefully: media_id is first token
    parts = rest.split(":", 1)
    media_id = int(parts[0])
    back_cb  = parts[1] if len(parts) > 1 else "home"

    item = await db.get_media_item(media_id)
    if not item:
        await callback.answer("الملف غير موجود!", show_alert=True)
        return

    caption = build_media_caption(item)
    kb = UserKeyboards.media_detail(media_id, back_cb)

    try:
        media_type = item["media_type"]
        file_id    = item["file_id"]

        if media_type == "video":
            await callback.message.answer_video(
                video=file_id,
                caption=caption,
                reply_markup=kb,
                parse_mode="HTML",
            )
        elif media_type == "photo":
            await callback.message.answer_photo(
                photo=file_id,
                caption=caption,
                reply_markup=kb,
                parse_mode="HTML",
            )
        elif media_type == "audio":
            await callback.message.answer_audio(
                audio=file_id,
                caption=caption,
                reply_markup=kb,
                parse_mode="HTML",
            )
        else:  # document
            await callback.message.answer_document(
                document=file_id,
                caption=caption,
                reply_markup=kb,
                parse_mode="HTML",
            )

        await callback.message.delete()

    except Exception as e:
        # Fallback: just show text with download button
        await callback.message.edit_text(
            caption,
            reply_markup=kb,
            parse_mode="HTML",
        )

    await callback.answer()


# ─── Download handler ──────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("download:"))
async def cb_download(callback: CallbackQuery, bot: Bot):
    # download:{media_id}:{back_cb}
    rest = callback.data[9:]
    parts = rest.split(":", 1)
    media_id = int(parts[0])
    back_cb  = parts[1] if len(parts) > 1 else "home"

    item = await db.get_media_item(media_id)
    if not item:
        await callback.answer("الملف غير موجود!", show_alert=True)
        return

    # Log download
    await db.log_download(callback.from_user.id, media_id)

    kb = UserKeyboards.after_download(back_cb)
    title = item.get("title_ar") or item.get("title", "الملف")

    try:
        media_type = item["media_type"]
        file_id    = item["file_id"]
        caption    = f"⬇️ <b>جارٍ إرسال:</b> {title}"

        if media_type == "video":
            await callback.message.answer_video(
                video=file_id,
                caption=caption,
                reply_markup=kb,
                parse_mode="HTML",
            )
        elif media_type == "photo":
            await callback.message.answer_photo(
                photo=file_id,
                caption=caption,
                reply_markup=kb,
                parse_mode="HTML",
            )
        elif media_type == "audio":
            await callback.message.answer_audio(
                audio=file_id,
                caption=caption,
                reply_markup=kb,
                parse_mode="HTML",
            )
        else:
            await callback.message.answer_document(
                document=file_id,
                caption=caption,
                reply_markup=kb,
                parse_mode="HTML",
            )

        await callback.answer(f"✅ تم إرسال: {title}", show_alert=False)

    except Exception as e:
        await callback.answer(f"❌ حدث خطأ أثناء الإرسال: {str(e)}", show_alert=True)
