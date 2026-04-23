from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Dict, Optional

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from menus import (
    admin_category_menu,
    admin_dashboard,
    admin_type_menu,
    category_menu,
    clear_confirm_menu,
    items_menu,
    main_menu,
    targets_menu,
    upload_menu,
)
from storage import Storage

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


def get_session(user_id: int) -> Dict[str, object]:
    session = SESSIONS.setdefault(user_id, {})
    session.setdefault("role", "user")
    session.setdefault("screen", "home")
    session.setdefault("page", 0)
    return session


def set_session(user_id: int, **kwargs) -> Dict[str, object]:
    session = get_session(user_id)
    session.update(kwargs)
    return session


def clear_session(user_id: int) -> None:
    SESSIONS.pop(user_id, None)


def page_text(title: str, page: int, total_pages: int) -> str:
    return f"{title}\nالصفحة {page + 1}/{total_pages}"


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


async def show_main_menu(update: Update, text: str = "📚 الصفحة الرئيسية"):
    uid = update.effective_user.id
    set_session(uid, role="user", screen="home", page=0)
    await update.message.reply_text(text, reply_markup=main_menu())


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_main_menu(update, "📚 أهلاً بك في بوت القرآن")


async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ غير مسموح")
        return
    set_session(update.effective_user.id, role="admin", screen="admin_dashboard", page=0)
    await update.message.reply_text("🛠️ لوحة التحكم", reply_markup=admin_dashboard())


def current_targets(content_type: str, payload) -> list[str]:
    return storage.get_targets(content_type, payload)


def current_items(payload, category: str, content_type: Optional[str], target_name: Optional[str]) -> list[dict]:
    return storage.get_items(payload, category, content_type, target_name)


async def show_targets_screen(update: Update, session: Dict[str, object], payload, title: str, content_type: str, category: str):
    items = current_targets(content_type, payload)
    page = int(session.get("page", 0))
    markup, page, total_pages, _chunk = targets_menu(
        items=items,
        page=page,
        per_page=payload["settings"]["page_size"],
    )
    session["page"] = page
    session["screen"] = session.get("screen", "targets")
    session["content_type"] = content_type
    session["category"] = category
    await update.message.reply_text(page_text(title, page, total_pages), reply_markup=markup)


async def show_items_screen(update: Update, session: Dict[str, object], payload, title: str, category: str, content_type: Optional[str], target_name: Optional[str]):
    items = current_items(payload, category, content_type, target_name)
    page = int(session.get("page", 0))
    markup, page, total_pages, _indices = items_menu(
        items_count=len(items),
        page=page,
        per_page=payload["settings"]["item_page_size"],
    )
    session["page"] = page
    await update.message.reply_text(page_text(title, page, total_pages), reply_markup=markup)


async def handle_home(update: Update, session: Dict[str, object]):
    session.clear()
    session["role"] = "user"
    session["screen"] = "home"
    session["page"] = 0
    await update.message.reply_text("📚 الصفحة الرئيسية", reply_markup=main_menu())


async def handle_back(update: Update, session: Dict[str, object], payload):
    screen = session.get("screen")
    role = session.get("role", "user")
    uid = update.effective_user.id

    if role == "admin":
        if screen in {"admin_add_category", "admin_del_category"}:
            set_session(uid, screen="admin_dashboard", page=0)
            await update.message.reply_text("🛠️ لوحة التحكم", reply_markup=admin_dashboard())
            return
        if screen in {"admin_add_type", "admin_del_type"}:
            action = str(session.get("action", "add"))
            set_session(uid, screen=f"admin_{action}_category", page=0)
            await update.message.reply_text("اختر القسم:", reply_markup=admin_category_menu(action))
            return
        if screen in {"admin_add_targets", "admin_del_targets"}:
            action = str(session.get("action", "add"))
            category = str(session.get("category", "chroma"))
            set_session(uid, screen=f"admin_{action}_type", page=0)
            await update.message.reply_text("اختر النوع:", reply_markup=admin_type_menu(action, category))
            return
        if screen == "admin_upload_target":
            action = str(session.get("action", "add"))
            category = str(session.get("category", "chroma"))
            content_type = str(session.get("content_type", "surahs"))
            set_session(uid, screen="admin_add_targets", page=0)
            title = "📖 اختر السورة" if content_type == "surahs" else "🎤 اختر الشيخ"
            await show_targets_screen(update, session, payload, title, content_type, category)
            return
        if screen == "admin_upload_nature":
            set_session(uid, screen="admin_dashboard", page=0)
            await update.message.reply_text("🛠️ لوحة التحكم", reply_markup=admin_dashboard())
            return
        if screen == "admin_clear_confirm":
            previous = str(session.get("return_screen", "admin_dashboard"))
            set_session(uid, screen=previous)
            if previous == "admin_del_items":
                await update.message.reply_text("تم الإلغاء", reply_markup=items_menu(len(current_items(payload, str(session.get("category", "chroma")), session.get("content_type"), session.get("target_name"))), int(session.get("page", 0)), payload["settings"]["item_page_size"])[0])
            elif previous == "admin_del_nature_items":
                await update.message.reply_text("تم الإلغاء", reply_markup=items_menu(len(payload["categories"]["nature"]), int(session.get("page", 0)), payload["settings"]["item_page_size"])[0])
            else:
                await update.message.reply_text("تم الإلغاء", reply_markup=admin_dashboard())
            return
        if screen == "admin_del_items":
            category = str(session.get("category", "chroma"))
            content_type = session.get("content_type")
            set_session(uid, screen="admin_del_targets", page=0)
            title = "📖 اختر السورة للحذف" if content_type == "surahs" else "🎤 اختر الشيخ للحذف"
            await show_targets_screen(update, session, payload, title, str(content_type), category)
            return
        if screen == "admin_del_nature_items":
            set_session(uid, screen="admin_del_category", page=0)
            await update.message.reply_text("اختر القسم للحذف:", reply_markup=admin_category_menu("del"))
            return

    if screen == "user_category":
        set_session(uid, screen="home", page=0)
        await update.message.reply_text("اختر القسم من القائمة:", reply_markup=main_menu())
        return

    if screen == "user_targets":
        category = str(session.get("category", "chroma"))
        set_session(uid, screen="user_category", page=0)
        await update.message.reply_text("اختر النوع:", reply_markup=category_menu(category))
        return

    if screen == "user_content":
        category = str(session.get("category", "chroma"))
        content_type = str(session.get("content_type", "surahs"))
        set_session(uid, screen="user_targets", page=0)
        title = "📖 اختر السورة:" if content_type == "surahs" else "🎤 اختر الشيخ:"
        await show_targets_screen(update, session, payload, title, content_type, category)
        return

    await show_main_menu(update, "📚 الصفحة الرئيسية")


async def handle_user_text(update: Update, session: Dict[str, object], payload, text: str):
    screen = session.get("screen", "home")
    uid = update.effective_user.id

    if text == "🎬 كرومات":
        set_session(uid, screen="user_category", category="chroma", content_type=None, page=0)
        await update.message.reply_text("🎬 قسم الكرومات", reply_markup=category_menu("chroma"))
        return

    if text == "🎨 تصاميم":
        set_session(uid, screen="user_category", category="designs", content_type=None, page=0)
        await update.message.reply_text("🎨 قسم التصاميم", reply_markup=category_menu("designs"))
        return

    if text == "🌿 مناظر طبيعية":
        items = payload["categories"]["nature"]
        if not items:
            await update.message.reply_text("🌿 لا يوجد محتوى بعد", reply_markup=main_menu())
            return
        await update.message.reply_text("🌿 مناظر طبيعية")
        for item in items:
            await send_item(update.message, item)
        await update.message.reply_text("اختر قسمًا آخر", reply_markup=main_menu())
        return

    if text == "📖 سور":
        if screen not in {"user_category", "user_targets"}:
            return
        category = str(session.get("category", "chroma"))
        set_session(uid, screen="user_targets", content_type="surahs", page=0)
        await show_targets_screen(update, session, payload, "📖 اختر السورة", "surahs", category)
        return

    if text == "🎤 شيوخ":
        if screen not in {"user_category", "user_targets"}:
            return
        category = str(session.get("category", "chroma"))
        set_session(uid, screen="user_targets", content_type="sheikhs", page=0)
        await show_targets_screen(update, session, payload, "🎤 اختر الشيخ", "sheikhs", category)
        return

    if screen == "user_targets":
        content_type = str(session.get("content_type", "surahs"))
        category = str(session.get("category", "chroma"))
        targets = current_targets(content_type, payload)
        page_size = payload["settings"]["page_size"]
        page = int(session.get("page", 0))

        if text == "⬅️":
            session["page"] = max(0, page - 1)
            title = "📖 اختر السورة" if content_type == "surahs" else "🎤 اختر الشيخ"
            await show_targets_screen(update, session, payload, title, content_type, category)
            return
        if text == "➡️":
            max_page = max(0, (len(targets) - 1) // page_size)
            session["page"] = min(max_page, page + 1)
            title = "📖 اختر السورة" if content_type == "surahs" else "🎤 اختر الشيخ"
            await show_targets_screen(update, session, payload, title, content_type, category)
            return
        if text in targets:
            items = current_items(payload, category, content_type, text)
            if not items:
                await update.message.reply_text(f"❌ لا يوجد محتوى لـ {text}", reply_markup=main_menu())
                return
            set_session(uid, screen="user_content", target_name=text)
            await update.message.reply_text(f"📂 {text}\nعدد العناصر: {len(items)}")
            for item in items:
                await send_item(update.message, item)
            set_session(uid, screen="user_targets")
            title = "📖 اختر السورة" if content_type == "surahs" else "🎤 اختر الشيخ"
            await show_targets_screen(update, session, payload, title, content_type, category)
            return

    await update.message.reply_text("اختر من القائمة", reply_markup=main_menu())


async def handle_admin_text(update: Update, session: Dict[str, object], payload, text: str):
    uid = update.effective_user.id
    screen = session.get("screen", "admin_dashboard")

    if text == "🏠 الرئيسية":
        await show_main_menu(update, "📚 الصفحة الرئيسية")
        return

    if screen == "admin_dashboard":
        if text == "➕ إضافة محتوى":
            set_session(uid, screen="admin_add_category", action="add", page=0)
            await update.message.reply_text("➕ اختر القسم للإضافة", reply_markup=admin_category_menu("add"))
            return
        if text == "🗑️ حذف محتوى":
            set_session(uid, screen="admin_del_category", action="del", page=0)
            await update.message.reply_text("🗑️ اختر القسم للحذف", reply_markup=admin_category_menu("del"))
            return
        if text == "📊 الإحصائيات":
            stats = storage.stats(payload)
            await update.message.reply_text(
                "📊 الإحصائيات\n"
                f"• كرومات: {stats['chroma']}\n"
                f"• تصاميم: {stats['designs']}\n"
                f"• مناظر طبيعية: {stats['nature']}",
                reply_markup=admin_dashboard(),
            )
            return

    if screen == "admin_add_category":
        if text in {"🎬 كرومات", "🎨 تصاميم"}:
            category = "chroma" if text == "🎬 كرومات" else "designs"
            set_session(uid, category=category, screen="admin_add_type", page=0)
            await update.message.reply_text("اختر النوع:", reply_markup=admin_type_menu("add", category))
            return
        if text == "🌿 مناظر طبيعية":
            set_session(uid, category="nature", screen="admin_upload_nature", mode="upload_nature", page=0)
            await update.message.reply_text(
                "🌿 أرسل الصور/الفيديوهات/الملفات الآن.\nاضغط تم عند الانتهاء.",
                reply_markup=upload_menu(),
            )
            return

    if screen == "admin_add_type":
        if text in {"📖 سور", "🎤 شيوخ"}:
            content_type = "surahs" if text == "📖 سور" else "sheikhs"
            category = str(session.get("category", "chroma"))
            set_session(uid, content_type=content_type, screen="admin_add_targets", page=0)
            title = "📖 اختر السورة" if content_type == "surahs" else "🎤 اختر الشيخ"
            await show_targets_screen(update, session, payload, title, content_type, category)
            return

    if screen == "admin_add_targets":
        content_type = str(session.get("content_type", "surahs"))
        category = str(session.get("category", "chroma"))
        targets = current_targets(content_type, payload)
        page_size = payload["settings"]["page_size"]
        page = int(session.get("page", 0))

        if text == "⬅️":
            session["page"] = max(0, page - 1)
            title = "📖 اختر السورة" if content_type == "surahs" else "🎤 اختر الشيخ"
            await show_targets_screen(update, session, payload, title, content_type, category)
            return
        if text == "➡️":
            max_page = max(0, (len(targets) - 1) // page_size)
            session["page"] = min(max_page, page + 1)
            title = "📖 اختر السورة" if content_type == "surahs" else "🎤 اختر الشيخ"
            await show_targets_screen(update, session, payload, title, content_type, category)
            return
        if text in targets:
            set_session(uid, target_name=text, screen="admin_upload_target", mode="upload")
            await update.message.reply_text(
                f"📤 أرسل المحتوى الآن لـ: {text}\nيمكنك إرسال صورة أو فيديو أو ملف أكثر من مرة.",
                reply_markup=upload_menu(),
            )
            return

    if screen in {"admin_upload_target", "admin_upload_nature"}:
        if text == "❌ إلغاء":
            clear_session(uid)
            await update.message.reply_text("❌ تم الإلغاء", reply_markup=admin_dashboard())
            return
        if text == "✅ تم":
            set_session(uid, screen="admin_dashboard", page=0)
            await update.message.reply_text("✅ تم حفظ المحتوى", reply_markup=admin_dashboard())
            return
        await update.message.reply_text("📎 ابعت صورة أو فيديو أو ملف، أو اضغط تم", reply_markup=upload_menu())
        return

    if screen == "admin_del_category":
        if text in {"🎬 كرومات", "🎨 تصاميم"}:
            category = "chroma" if text == "🎬 كرومات" else "designs"
            set_session(uid, category=category, screen="admin_del_type", page=0)
            await update.message.reply_text("اختر النوع:", reply_markup=admin_type_menu("del", category))
            return
        if text == "🌿 مناظر طبيعية":
            items = payload["categories"]["nature"]
            if not items:
                set_session(uid, screen="admin_dashboard", page=0)
                await update.message.reply_text("🌿 لا يوجد محتوى للحذف", reply_markup=admin_dashboard())
                return
            set_session(uid, category="nature", content_type=None, target_name=None, screen="admin_del_nature_items", page=0)
            markup, page, total_pages, _indices = items_menu(len(items), 0, payload["settings"]["item_page_size"])
            session["page"] = page
            await update.message.reply_text(page_text("🌿 المناظر الطبيعية", page, total_pages), reply_markup=markup)
            return

    if screen == "admin_del_type":
        if text in {"📖 سور", "🎤 شيوخ"}:
            content_type = "surahs" if text == "📖 سور" else "sheikhs"
            category = str(session.get("category", "chroma"))
            set_session(uid, content_type=content_type, screen="admin_del_targets", page=0)
            title = "📖 اختر السورة للحذف" if content_type == "surahs" else "🎤 اختر الشيخ للحذف"
            await show_targets_screen(update, session, payload, title, content_type, category)
            return

    if screen == "admin_del_targets":
        content_type = str(session.get("content_type", "surahs"))
        category = str(session.get("category", "chroma"))
        targets = current_targets(content_type, payload)
        page_size = payload["settings"]["page_size"]
        page = int(session.get("page", 0))

        if text == "⬅️":
            session["page"] = max(0, page - 1)
            title = "📖 اختر السورة للحذف" if content_type == "surahs" else "🎤 اختر الشيخ للحذف"
            await show_targets_screen(update, session, payload, title, content_type, category)
            return
        if text == "➡️":
            max_page = max(0, (len(targets) - 1) // page_size)
            session["page"] = min(max_page, page + 1)
            title = "📖 اختر السورة للحذف" if content_type == "surahs" else "🎤 اختر الشيخ للحذف"
            await show_targets_screen(update, session, payload, title, content_type, category)
            return
        if text in targets:
            target_name = text
            items = current_items(payload, category, content_type, target_name)
            if not items:
                set_session(uid, screen="admin_dashboard", page=0)
                await update.message.reply_text("❌ لا يوجد عناصر للحذف", reply_markup=admin_dashboard())
                return
            set_session(uid, target_name=target_name, screen="admin_del_items", page=0)
            markup, page, total_pages, _indices = items_menu(len(items), 0, payload["settings"]["item_page_size"])
            session["page"] = page
            await update.message.reply_text(page_text(f"🗑️ {target_name}", page, total_pages), reply_markup=markup)
            return

    if screen == "admin_del_items":
        category = str(session.get("category", "chroma"))
        content_type = session.get("content_type")
        target_name = session.get("target_name")
        items = current_items(payload, category, content_type, target_name)
        page_size = payload["settings"]["item_page_size"]
        page = int(session.get("page", 0))

        if text == "⬅️":
            session["page"] = max(0, page - 1)
            markup, page, total_pages, _indices = items_menu(len(items), session["page"], page_size)
            session["page"] = page
            await update.message.reply_text(page_text(f"🗑️ {target_name}", page, total_pages), reply_markup=markup)
            return
        if text == "➡️":
            max_page = max(0, (max(1, len(items)) - 1) // page_size)
            session["page"] = min(max_page, page + 1)
            markup, page, total_pages, _indices = items_menu(len(items), session["page"], page_size)
            session["page"] = page
            await update.message.reply_text(page_text(f"🗑️ {target_name}", page, total_pages), reply_markup=markup)
            return
        if text == "🧹 حذف الكل":
            set_session(uid, screen="admin_clear_confirm", return_screen="admin_del_items")
            await update.message.reply_text("هل تريد حذف كل العناصر؟", reply_markup=clear_confirm_menu())
            return
        m = re.match(r"^🗑️ حذف (\d+)$", text)
        if m:
            item_index = int(m.group(1)) - 1
            if storage.remove_item(payload, category, content_type, target_name, item_index):
                storage.save(payload)
                items = current_items(payload, category, content_type, target_name)
                markup, page, total_pages, _indices = items_menu(len(items), page, page_size)
                session["page"] = page
                await update.message.reply_text("✅ تم حذف العنصر", reply_markup=markup)
            else:
                await update.message.reply_text("❌ العنصر غير موجود", reply_markup=admin_dashboard())
                set_session(uid, screen="admin_dashboard", page=0)
            return

    if screen == "admin_del_nature_items":
        items = payload["categories"]["nature"]
        page_size = payload["settings"]["item_page_size"]
        page = int(session.get("page", 0))

        if text == "⬅️":
            session["page"] = max(0, page - 1)
            markup, page, total_pages, _indices = items_menu(len(items), session["page"], page_size)
            session["page"] = page
            await update.message.reply_text(page_text("🌿 المناظر الطبيعية", page, total_pages), reply_markup=markup)
            return
        if text == "➡️":
            max_page = max(0, (max(1, len(items)) - 1) // page_size)
            session["page"] = min(max_page, page + 1)
            markup, page, total_pages, _indices = items_menu(len(items), session["page"], page_size)
            session["page"] = page
            await update.message.reply_text(page_text("🌿 المناظر الطبيعية", page, total_pages), reply_markup=markup)
            return
        if text == "🧹 حذف الكل":
            set_session(uid, screen="admin_clear_confirm", return_screen="admin_del_nature_items")
            await update.message.reply_text("هل تريد حذف كل العناصر؟", reply_markup=clear_confirm_menu())
            return
        m = re.match(r"^🗑️ حذف (\d+)$", text)
        if m:
            item_index = int(m.group(1)) - 1
            if storage.remove_item(payload, "nature", None, None, item_index):
                storage.save(payload)
                items = payload["categories"]["nature"]
                markup, page, total_pages, _indices = items_menu(len(items), page, page_size)
                session["page"] = page
                await update.message.reply_text("✅ تم حذف العنصر", reply_markup=markup)
            else:
                await update.message.reply_text("❌ العنصر غير موجود", reply_markup=admin_dashboard())
                set_session(uid, screen="admin_dashboard", page=0)
            return

    if screen == "admin_clear_confirm":
        if text == "✅ نعم، احذف الكل":
            category = str(session.get("category", "chroma"))
            content_type = session.get("content_type")
            target_name = session.get("target_name")
            if category == "nature":
                storage.clear_target(payload, "nature", None, None)
            else:
                storage.clear_target(payload, category, content_type, target_name)
            storage.save(payload)
            set_session(uid, screen="admin_dashboard", page=0)
            await update.message.reply_text("✅ تم حذف الكل", reply_markup=admin_dashboard())
            return
        if text == "❌ إلغاء":
            previous = str(session.get("return_screen", "admin_dashboard"))
            if previous == "admin_del_items":
                category = str(session.get("category", "chroma"))
                content_type = session.get("content_type")
                target_name = session.get("target_name")
                items = current_items(payload, category, content_type, target_name)
                markup, page, total_pages, _indices = items_menu(len(items), int(session.get("page", 0)), payload["settings"]["item_page_size"])
                set_session(uid, screen="admin_del_items", page=page)
                await update.message.reply_text("تم الإلغاء", reply_markup=markup)
                return
            if previous == "admin_del_nature_items":
                items = payload["categories"]["nature"]
                markup, page, total_pages, _indices = items_menu(len(items), int(session.get("page", 0)), payload["settings"]["item_page_size"])
                set_session(uid, screen="admin_del_nature_items", page=page)
                await update.message.reply_text("تم الإلغاء", reply_markup=markup)
                return
            set_session(uid, screen="admin_dashboard", page=0)
            await update.message.reply_text("تم الإلغاء", reply_markup=admin_dashboard())
            return

    await update.message.reply_text("اختر من القائمة", reply_markup=admin_dashboard())


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = (update.message.text or "").strip()
    session = get_session(user_id)
    payload = storage.load()

    if text == "/start":
        await start(update, context)
        return
    if text == "/admin":
        await admin_cmd(update, context)
        return

    if text == "🏠 الرئيسية":
        await handle_home(update, session)
        return
    if text == "🔙 رجوع":
        await handle_back(update, session, payload)
        return

    if session.get("role") == "admin" and is_admin(user_id):
        await handle_admin_text(update, session, payload, text)
    else:
        await handle_user_text(update, session, payload, text)


async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return
    session = get_session(user_id)
    if session.get("screen") not in {"admin_upload_target", "admin_upload_nature"}:
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
        await msg.reply_text("📎 ابعت صورة أو فيديو أو ملف", reply_markup=upload_menu())
        return

    data = storage.load()
    item = {"media_type": media_type, "file_id": file_id, "caption": caption}

    if session.get("screen") == "admin_upload_nature":
        storage.add_item(data, "nature", None, None, item)
    else:
        storage.add_item(
            data,
            str(session.get("category", "chroma")),
            str(session.get("content_type", "surahs")),
            str(session.get("target_name", "")),
            item,
        )

    storage.save(data)
    await msg.reply_text("✅ تم الحفظ، أرسل المزيد أو اضغط تم", reply_markup=upload_menu())


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is missing. Put it in .env")
    if not ADMIN_ID:
        raise RuntimeError("ADMIN_ID is missing. Put it in .env")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL, handle_media))
    logger.info("Bot started")
    app.run_polling(close_loop=False)


if __name__ == "__main__":
    main()
