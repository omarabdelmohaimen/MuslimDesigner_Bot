from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict, Optional

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from menus import (
    admin_category_menu,
    admin_dashboard,
    admin_type_menu,
    category_menu,
    item_list_menu,
    main_menu,
    paginated_targets_menu,
    upload_menu,
)
from storage import SURAHS, Storage

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0") or 0)
DATA_FILE = Path("data/content.json")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("quran_media_bot")

storage = Storage(DATA_FILE)
SESSIONS: Dict[int, Dict[str, object]] = {}


def is_admin(user_id: int) -> bool:
    return bool(ADMIN_ID) and user_id == ADMIN_ID


def admin_target_list_menu(action: str, category: str, content_type: str, page: int, data):
    items = storage.get_targets(content_type, data)
    return paginated_targets_menu(
        items=items,
        page=page,
        per_page=data["settings"]["page_size"],
        item_prefix=f"a:pick:{action}:{category}:{content_type}",
        page_prefix=f"a:list:{action}:{category}:{content_type}",
        back_callback=f"a:{action}",
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 أهلاً بك في بوت القرآن\nاختر القسم من القائمة:",
        reply_markup=main_menu(),
    )


async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ غير مسموح")
        return
    await update.message.reply_text("🛠 لوحة التحكم", reply_markup=admin_dashboard())


async def send_item(message, item):
    media_type = item.get("media_type", "photo")
    file_id = item.get("file_id")
    caption = item.get("caption") or None
    if not file_id:
        return
    if media_type == "video":
        await message.reply_video(file_id, caption=caption)
    elif media_type == "document":
        await message.reply_document(file_id, caption=caption)
    else:
        await message.reply_photo(file_id, caption=caption)


async def show_target_content(query, category: str, content_type: str, page: int, idx: int, data):
    target_name = storage.get_target_name(content_type, idx, data)
    if not target_name:
        await query.answer("الهدف غير موجود", show_alert=True)
        return

    items = storage.get_items(data, category, content_type, target_name)
    back_menu = paginated_targets_menu(
        items=storage.get_targets(content_type, data),
        page=page,
        per_page=data["settings"]["page_size"],
        item_prefix=f"u:view:{category}:{content_type}",
        page_prefix=f"u:list:{category}:{content_type}",
        back_callback=f"u:type:{category}:{content_type}",
    )

    if not items:
        await query.message.reply_text(f"❌ لا يوجد محتوى لـ {target_name}", reply_markup=back_menu)
        return

    await query.message.reply_text(f"📂 {target_name}\nعدد العناصر: {len(items)}")
    for item in items:
        await send_item(query.message, item)
    await query.message.reply_text("🔙 الرجوع للقائمة", reply_markup=back_menu)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return

    session = SESSIONS.get(user_id)
    if not session:
        return

    if session.get("mode") not in {"upload", "upload_nature"}:
        return

    msg = update.message
    file_id = None
    media_type = None
    caption = msg.caption or ""

    if msg.photo:
        file_id = msg.photo[-1].file_id
        media_type = "photo"
    elif msg.video:
        file_id = msg.video.file_id
        media_type = "video"
    elif msg.document:
        file_id = msg.document.file_id
        media_type = "document"
    else:
        await msg.reply_text("📎 ابعت صورة أو فيديو أو ملف")
        return

    data = storage.load()
    item = {"media_type": media_type, "file_id": file_id, "caption": caption}

    if session.get("mode") == "upload_nature":
        storage.add_item(data, "nature", None, None, item)
    else:
        storage.add_item(
            data,
            str(session["category"]),
            str(session["content_type"]),
            str(session["target_name"]),
            item,
        )

    storage.save(data)
    await msg.reply_text("✅ تم الحفظ", reply_markup=upload_menu("a:done", "a:cancel"))


async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data or ""
    user_id = query.from_user.id
    payload = storage.load()

    if data == "noop":
        return

    # ================= USER =================
    if data == "u:home":
        await query.edit_message_text("📚 الصفحة الرئيسية", reply_markup=main_menu())
        return

    if data == "u:nature":
        items = payload["categories"]["nature"]
        if not items:
            await query.edit_message_text("🌿 لا يوجد محتوى بعد", reply_markup=main_menu())
            return
        await query.edit_message_text("🌿 مناظر طبيعية")
        for item in items:
            await send_item(query.message, item)
        await query.message.reply_text("🔙 العودة", reply_markup=main_menu())
        return

    if data.startswith("u:cat:"):
        _, _, category = data.split(":", 2)
        await query.edit_message_text(f"{category}", reply_markup=category_menu(category))
        return

    if data.startswith("u:type:"):
        _, _, category, content_type = data.split(":")
        targets = storage.get_targets(content_type, payload)
        title = "📖 اختر السورة:" if content_type == "surahs" else "🎤 اختر الشيخ:"
        menu = paginated_targets_menu(
            items=targets,
            page=0,
            per_page=payload["settings"]["page_size"],
            item_prefix=f"u:view:{category}:{content_type}",
            page_prefix=f"u:list:{category}:{content_type}",
            back_callback=f"u:cat:{category}",
        )
        await query.edit_message_text(title, reply_markup=menu)
        return

    if data.startswith("u:list:"):
        # u:list:category:type:page:N
        parts = data.split(":")
        if len(parts) == 6 and parts[4] == "page":
            _, _, category, content_type, _, page = parts
            targets = storage.get_targets(content_type, payload)
            menu = paginated_targets_menu(
                items=targets,
                page=int(page),
                per_page=payload["settings"]["page_size"],
                item_prefix=f"u:view:{category}:{content_type}",
                page_prefix=f"u:list:{category}:{content_type}",
                back_callback=f"u:cat:{category}",
            )
            await query.edit_message_reply_markup(reply_markup=menu)
        return

    if data.startswith("u:view:"):
        # u:view:category:type:page:idx
        _, _, category, content_type, page, idx = data.split(":")
        await show_target_content(query, category, content_type, int(page), int(idx), payload)
        return

    # ================= ADMIN =================
    if not is_admin(user_id):
        return

    if data == "a:home":
        await query.edit_message_text("🏠 الصفحة الرئيسية", reply_markup=main_menu())
        return

    if data == "a:panel":
        await query.edit_message_text("🛠 لوحة التحكم", reply_markup=admin_dashboard())
        return

    if data == "a:add":
        await query.edit_message_text("➕ اختر القسم للإضافة", reply_markup=admin_category_menu("add"))
        return

    if data == "a:del":
        await query.edit_message_text("🗑️ اختر القسم للحذف", reply_markup=admin_category_menu("del"))
        return

    if data == "a:stats":
        stats = storage.stats(payload)
        text = (
            "📊 الإحصائيات\n"
            f"• كرومات: {stats['chroma']}\n"
            f"• تصاميم: {stats['designs']}\n"
            f"• مناظر طبيعية: {stats['nature']}"
        )
        await query.edit_message_text(text, reply_markup=admin_dashboard())
        return

    if data.startswith("a:cat:"):
        _, _, action, category = data.split(":")
        if action == "add":
            if category == "nature":
                SESSIONS[user_id] = {"mode": "upload_nature", "category": "nature"}
                await query.edit_message_text(
                    "🌿 أرسل الصور/الفيديوهات/الملفات الآن، ثم اضغط تم عند الانتهاء.",
                    reply_markup=upload_menu("a:done", "a:cancel"),
                )
            else:
                await query.edit_message_text("اختر النوع:", reply_markup=admin_type_menu("add", category))
            return

        if action == "del":
            if category == "nature":
                items = payload["categories"]["nature"]
                if not items:
                    await query.edit_message_text("🌿 لا يوجد محتوى لحذفه", reply_markup=admin_dashboard())
                    return
                await query.edit_message_text(
                    "🌿 المناظر الطبيعية",
                    reply_markup=item_list_menu(
                        items_count=len(items),
                        item_prefix="a:rmnature",
                        page_prefix="a:rmnature",
                        back_callback="a:del",
                        page=0,
                        per_page=payload["settings"]["item_page_size"],
                    ),
                )
            else:
                await query.edit_message_text("اختر النوع:", reply_markup=admin_type_menu("del", category))
            return

    if data.startswith("a:type:"):
        _, _, action, category, content_type = data.split(":")
        title = "📖 اختر السورة" if content_type == "surahs" else "🎤 اختر الشيخ"
        if action == "add":
            menu = admin_target_list_menu(action, category, content_type, 0, payload)
            await query.edit_message_text(title, reply_markup=menu)
        else:
            menu = admin_target_list_menu(action, category, content_type, 0, payload)
            await query.edit_message_text(title + " للحذف", reply_markup=menu)
        return

    if data.startswith("a:list:"):
        # a:list:action:category:type:page:N
        parts = data.split(":")
        if len(parts) == 7 and parts[5] == "page":
            _, _, action, category, content_type, _, page = parts
            menu = admin_target_list_menu(action, category, content_type, int(page), payload)
            await query.edit_message_reply_markup(reply_markup=menu)
        return

    if data.startswith("a:pick:"):
        # a:pick:action:category:type:page:idx
        _, _, action, category, content_type, page, idx = data.split(":")
        idx_i = int(idx)
        target_name = storage.get_target_name(content_type, idx_i, payload)
        if not target_name:
            await query.answer("الهدف غير موجود", show_alert=True)
            return

        if action == "add":
            SESSIONS[user_id] = {
                "mode": "upload",
                "category": category,
                "content_type": content_type,
                "target_index": idx_i,
                "target_name": target_name,
            }
            await query.edit_message_text(
                f"📤 أرسل المحتوى الآن لـ: {target_name}",
                reply_markup=upload_menu("a:done", f"a:type:add:{category}:{content_type}"),
            )
            return

        # delete flow: open item list for target
        items = storage.get_items(payload, category, content_type, target_name)
        if not items:
            await query.edit_message_text("❌ لا يوجد عناصر لحذفها", reply_markup=admin_dashboard())
            return
        await query.edit_message_text(
            f"🗑️ عناصر: {target_name}",
            reply_markup=item_list_menu(
                items_count=len(items),
                item_prefix=f"a:rmitem:{category}:{content_type}:{idx_i}",
                page_prefix=f"a:rmitem:{category}:{content_type}:{idx_i}",
                back_callback=f"a:type:del:{category}:{content_type}",
                page=0,
                per_page=payload["settings"]["item_page_size"],
            ),
        )
        return

    if data.startswith("a:rmnature:"):
        # a:rmnature:page:N OR a:rmnature:clear:P OR a:rmnature:P:IDX
        parts = data.split(":")
        if len(parts) == 4 and parts[2] == "page":
            page = int(parts[3])
            items = payload["categories"]["nature"]
            await query.edit_message_reply_markup(
                reply_markup=item_list_menu(
                    items_count=len(items),
                    item_prefix="a:rmnature",
                    page_prefix="a:rmnature",
                    back_callback="a:del",
                    page=page,
                    per_page=payload["settings"]["item_page_size"],
                )
            )
            return
        if len(parts) == 4 and parts[2] == "clear":
            storage.clear_target(payload, "nature", None, None)
            storage.save(payload)
            await query.edit_message_text("✅ تم حذف كل المناظر الطبيعية", reply_markup=admin_dashboard())
            return
        if len(parts) == 4:
            page = int(parts[2])
            item_index = int(parts[3])
            if storage.remove_item(payload, "nature", None, None, item_index):
                storage.save(payload)
                await query.edit_message_text("✅ تم حذف العنصر", reply_markup=admin_dashboard())
            else:
                await query.answer("العنصر غير موجود", show_alert=True)
            return

    if data.startswith("a:rmitem:"):
        # a:rmitem:category:type:targetidx:page:idx OR a:rmitem:category:type:targetidx:clear:page
        parts = data.split(":")
        if len(parts) == 7 and parts[5] == "page":
            _, _, category, content_type, target_idx, _, page = parts
            target_name = storage.get_target_name(content_type, int(target_idx), payload)
            items = storage.get_items(payload, category, content_type, target_name or "")
            await query.edit_message_reply_markup(
                reply_markup=item_list_menu(
                    items_count=len(items),
                    item_prefix=f"a:rmitem:{category}:{content_type}:{target_idx}",
                    page_prefix=f"a:rmitem:{category}:{content_type}:{target_idx}",
                    back_callback=f"a:pick:del:{category}:{content_type}:0:{target_idx}",
                    page=int(page),
                    per_page=payload["settings"]["item_page_size"],
                )
            )
            return
        if len(parts) == 7 and parts[5] == "clear":
            _, _, category, content_type, target_idx, _, _page = parts
            target_name = storage.get_target_name(content_type, int(target_idx), payload)
            if not target_name:
                await query.answer("الهدف غير موجود", show_alert=True)
                return
            storage.clear_target(payload, category, content_type, target_name)
            storage.save(payload)
            await query.edit_message_text(f"✅ تم حذف كل العناصر من {target_name}", reply_markup=admin_dashboard())
            return
        if len(parts) == 7:
            _, _, category, content_type, target_idx, page, item_index = parts
            target_name = storage.get_target_name(content_type, int(target_idx), payload)
            if not target_name:
                await query.answer("الهدف غير موجود", show_alert=True)
                return
            if storage.remove_item(payload, category, content_type, target_name, int(item_index)):
                storage.save(payload)
                await query.edit_message_text("✅ تم حذف العنصر", reply_markup=admin_dashboard())
            else:
                await query.answer("العنصر غير موجود", show_alert=True)
            return

    if data == "a:done":
        SESSIONS.pop(user_id, None)
        await query.edit_message_text("✅ تم حفظ المحتوى", reply_markup=admin_dashboard())
        return

    if data == "a:cancel":
        SESSIONS.pop(user_id, None)
        await query.edit_message_text("❌ تم الإلغاء", reply_markup=admin_dashboard())
        return

    logger.info("Unhandled callback: %s", data)


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is missing. Put it in .env")
    if not ADMIN_ID:
        raise RuntimeError("ADMIN_ID is missing. Put it in .env")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CallbackQueryHandler(handle_callbacks))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL, handle_message))
    logger.info("Bot started")
    app.run_polling(close_loop=False)


if __name__ == "__main__":
    main()

app.run_polling()