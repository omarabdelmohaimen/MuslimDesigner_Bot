from __future__ import annotations

import logging
import os
import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from menus import (
    admin_category_menu,
    admin_dashboard,
    admin_type_menu,
    sheikh_mode_menu,
    category_menu,
    clear_confirm_menu,
    items_menu,
    main_menu,
    targets_menu,
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


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    text = text.replace("ى", "ي").replace("ؤ", "و").replace("ئ", "ي")
    text = text.replace("ة", "ه")
    text = re.sub(r"[\u064B-\u065F\u0670\u0640]", "", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def find_surahs(query: str, available: Optional[Sequence[str]] = None) -> List[str]:
    q = normalize_text(query)
    if not q:
        return []
    source = list(available) if available is not None else SURAHS
    exact = [s for s in source if normalize_text(s) == q]
    if exact:
        return exact
    return [s for s in source if q in normalize_text(s)]


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


async def reply(update: Update, text: str, markup=None):
    await update.message.reply_text(text, reply_markup=markup)


async def show_main_menu(update: Update, text: str = "الصفحة الرئيسية"):
    uid = update.effective_user.id
    set_session(uid, role="user", screen="home", page=0, category=None, content_type=None, target_name=None, subtarget_name=None)
    await reply(update, text, main_menu())


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_main_menu(update, "أهلا بك في بوت القرآن")


async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await reply(update, "غير مسموح")
        return
    set_session(update.effective_user.id, role="admin", screen="admin_dashboard", page=0)
    await reply(update, "لوحة التحكم", admin_dashboard())


def current_targets(content_type: str, payload, *, category: Optional[str] = None, available_only: bool = False) -> list[str]:
    return storage.get_targets(content_type, payload, category=category, available_only=available_only)


def current_items(payload, category: str, content_type: Optional[str], target_name: Optional[str], subtarget_name: Optional[str] = None) -> list[dict]:
    return storage.get_items(payload, category, content_type, target_name, subtarget_name)


def available_surahs_for_category(payload, category: str) -> list[str]:
    return current_targets("surahs", payload, category=category, available_only=True)


def available_sheikhs_for_category(payload, category: str) -> list[str]:
    return current_targets("sheikhs", payload, category=category, available_only=True)


async def show_targets_screen(
    update: Update,
    session: Dict[str, object],
    payload,
    title: str,
    targets: Sequence[str],
    screen: str,
    category: Optional[str] = None,
    content_type: Optional[str] = None,
    extra: Optional[dict] = None,
):
    page = int(session.get("page", 0))
    markup, page, total_pages, chunk = targets_menu(
        items=targets,
        page=page,
        per_page=payload["settings"]["page_size"],
    )
    session["page"] = page
    session["screen"] = screen
    session["targets"] = list(targets)
    if category is not None:
        session["category"] = category
    if content_type is not None:
        session["content_type"] = content_type
    if extra:
        session.update(extra)
    await reply(update, page_text(title, page, total_pages), markup)


async def show_items_screen(
    update: Update,
    session: Dict[str, object],
    payload,
    title: str,
    category: str,
    content_type: Optional[str],
    target_name: Optional[str],
    subtarget_name: Optional[str],
    screen: str,
):
    items = current_items(payload, category, content_type, target_name, subtarget_name)
    page = int(session.get("page", 0))
    markup, page, total_pages, _indices = items_menu(
        items_count=len(items),
        page=page,
        per_page=payload["settings"]["item_page_size"],
    )
    session["page"] = page
    session["screen"] = screen
    await reply(update, page_text(title, page, total_pages), markup)


async def handle_home(update: Update, session: Dict[str, object]):
    session.clear()
    session["role"] = "user"
    session["screen"] = "home"
    session["page"] = 0
    await reply(update, "الصفحة الرئيسية", main_menu())


async def handle_back(update: Update, session: Dict[str, object], payload):
    screen = session.get("screen")
    role = session.get("role", "user")
    uid = update.effective_user.id

    if role == "admin":
        if screen in {"admin_add_category", "admin_del_category"}:
            set_session(uid, screen="admin_dashboard", page=0)
            await reply(update, "لوحة التحكم", admin_dashboard())
            return
        if screen in {"admin_add_type", "admin_del_type"}:
            action = str(session.get("action", "add"))
            set_session(uid, screen=f"admin_{action}_category", page=0)
            await reply(update, "اختر القسم", admin_category_menu(action))
            return
        if screen in {"admin_add_targets", "admin_del_targets"}:
            action = str(session.get("action", "add"))
            category = str(session.get("category", "chroma"))
            set_session(uid, screen=f"admin_{action}_type", page=0)
            await reply(update, "اختر النوع", admin_type_menu(action, category))
            return
        if screen == "admin_add_sheikh_mode":
            category = str(session.get("category", "chroma"))
            sheikh = str(session.get("target_name", ""))
            set_session(uid, screen="admin_add_targets", page=0, target_name=None, subtarget_name=None)
            await show_targets_screen(update, session, payload, "اختر الشيخ", current_targets("sheikhs", payload), "admin_add_targets", category, "sheikhs")
            return
        if screen == "admin_add_sheikh_surah":
            category = str(session.get("category", "chroma"))
            sheikh = str(session.get("target_name", ""))
            set_session(uid, screen="admin_add_sheikh_mode", page=0, target_name=sheikh)
            await reply(update, "اختر طريقة الإضافة", sheikh_mode_menu())
            return
        if screen in {"admin_upload_target", "admin_upload_nature"}:
            previous = str(session.get("return_screen", "admin_dashboard"))
            if previous == "admin_add_sheikh_mode":
                category = str(session.get("category", "chroma"))
                set_session(uid, screen="admin_add_sheikh_mode", page=0)
                await reply(update, "اختر طريقة الإضافة", sheikh_mode_menu())
                return
            if previous == "admin_add_sheikh_surah":
                category = str(session.get("category", "chroma"))
                sheikh = str(session.get("target_name", ""))
                set_session(uid, screen="admin_add_sheikh_mode", page=0, target_name=sheikh)
                await reply(update, "اختر طريقة الإضافة", sheikh_mode_menu())
                return
            if previous == "admin_add_targets":
                action = str(session.get("action", "add"))
                category = str(session.get("category", "chroma"))
                set_session(uid, screen="admin_add_type", page=0)
                await reply(update, "اختر النوع", admin_type_menu(action, category))
                return
            if previous == "admin_add_category":
                set_session(uid, screen="admin_add_category", page=0)
                await reply(update, "اختر القسم للإضافة", admin_category_menu("add"))
                return
            if previous == "admin_del_items":
                category = str(session.get("category", "chroma"))
                content_type = session.get("content_type")
                target_name = session.get("target_name")
                subtarget_name = session.get("subtarget_name")
                items = current_items(payload, category, content_type, target_name, subtarget_name)
                markup, page, total_pages, _indices = items_menu(len(items), int(session.get("page", 0)), payload["settings"]["item_page_size"])
                session["page"] = page
                await reply(update, "أعد الإرسال أو اضغط تم", markup)
                return
            if previous == "admin_del_nature_items":
                items = payload["categories"]["nature"]
                markup, page, total_pages, _indices = items_menu(len(items), int(session.get("page", 0)), payload["settings"]["item_page_size"])
                session["page"] = page
                await reply(update, "أعد الإرسال أو اضغط تم", markup)
                return
            set_session(uid, screen="admin_dashboard", page=0)
            await reply(update, "لوحة التحكم", admin_dashboard())
            return
        if screen == "admin_add_target":
            action = str(session.get("action", "add"))
            category = str(session.get("category", "chroma"))
            content_type = str(session.get("content_type", "surahs"))
            if content_type == "surahs":
                set_session(uid, screen="admin_add_targets", page=0)
                await show_targets_screen(update, session, payload, "اختر السورة", SURAHS, "admin_add_targets", category, content_type)
                return
            set_session(uid, screen="admin_add_targets", page=0)
            await show_targets_screen(update, session, payload, "اختر الشيخ", current_targets("sheikhs", payload), "admin_add_targets", category, content_type)
            return
        if screen == "admin_del_sheikh_surah":
            category = str(session.get("category", "chroma"))
            set_session(uid, screen="admin_del_targets", page=0, subtarget_name=None)
            await show_targets_screen(update, session, payload, "اختر الشيخ للحذف", available_sheikhs_for_category(payload, category), "admin_del_targets", category, "sheikhs")
            return
        if screen in {"admin_del_items", "admin_del_nature_items"}:
            set_session(uid, screen="admin_dashboard", page=0)
            await reply(update, "لوحة التحكم", admin_dashboard())
            return
        if screen == "admin_clear_confirm":
            previous = str(session.get("return_screen", "admin_dashboard"))
            set_session(uid, screen=previous)
            if previous == "admin_del_items":
                category = str(session.get("category", "chroma"))
                content_type = session.get("content_type")
                target_name = session.get("target_name")
                subtarget_name = session.get("subtarget_name")
                items = current_items(payload, category, content_type, target_name, subtarget_name)
                markup, page, total_pages, _indices = items_menu(len(items), int(session.get("page", 0)), payload["settings"]["item_page_size"])
                session["page"] = page
                await reply(update, "تم الإلغاء", markup)
                return
            if previous == "admin_del_nature_items":
                items = payload["categories"]["nature"]
                markup, page, total_pages, _indices = items_menu(len(items), int(session.get("page", 0)), payload["settings"]["item_page_size"])
                session["page"] = page
                await reply(update, "تم الإلغاء", markup)
                return
            await reply(update, "تم الإلغاء", admin_dashboard())
            return
        if screen == "admin_add_sheikh_name":
            set_session(uid, screen="admin_dashboard", page=0)
            await reply(update, "لوحة التحكم", admin_dashboard())
            return
        await reply(update, "اختر من القائمة", admin_dashboard())
        return

    # user
    if screen in {"user_category", "user_surahs", "user_sheikhs", "user_sheikh_surahs", "user_search_wait", "user_search_results"}:
        category = str(session.get("category", "chroma"))
        if screen == "user_sheikh_surahs":
            sheikh = str(session.get("target_name", ""))
            surahs = storage.get_surah_targets_for_sheikh(payload, category, sheikh)
            set_session(uid, screen="user_sheikhs", page=0, subtarget_name=None)
            await show_targets_screen(update, session, payload, "اختر الشيخ", available_sheikhs_for_category(payload, category), "user_sheikhs", category, "sheikhs")
            return
        if screen == "user_search_wait":
            set_session(uid, screen="user_category", page=0)
            await reply(update, "قسمك الحالي", category_menu(category))
            return
        if screen == "user_search_results":
            set_session(uid, screen="user_category", page=0)
            await reply(update, "قسمك الحالي", category_menu(category))
            return
        set_session(uid, screen="user_category", page=0)
        await reply(update, "قسمك الحالي", category_menu(category))
        return

    await show_main_menu(update, "الصفحة الرئيسية")


async def handle_user_text(update: Update, session: Dict[str, object], payload, text: str):
    uid = update.effective_user.id
    screen = session.get("screen", "home")

    if text == "كرومات":
        set_session(uid, screen="user_category", category="chroma", content_type=None, page=0, target_name=None, subtarget_name=None)
        await reply(update, "قسم الكرومات", category_menu("chroma"))
        return

    if text == "تصاميم":
        set_session(uid, screen="user_category", category="designs", content_type=None, page=0, target_name=None, subtarget_name=None)
        await reply(update, "قسم التصاميم", category_menu("designs"))
        return

    if text == "مناظر طبيعية":
        items = payload["categories"]["nature"]
        if not items:
            await reply(update, "لا يوجد محتوى بعد", main_menu())
            return
        await reply(update, "مناظر طبيعية")
        for item in items:
            await send_item(update.message, item)
        await reply(update, "اختر قسمًا آخر", main_menu())
        return

    if text == "سور":
        if screen not in {"user_category", "user_surahs", "user_search_results"}:
            return
        category = str(session.get("category", "chroma"))
        available = available_surahs_for_category(payload, category)
        if not available:
            await reply(update, "لا توجد سور متاحة الآن", category_menu(category))
            return
        set_session(uid, screen="user_surahs", content_type="surahs", page=0, target_name=None, subtarget_name=None)
        await show_targets_screen(update, session, payload, "اختر السورة", available, "user_surahs", category, "surahs")
        return

    if text == "شيوخ":
        if screen not in {"user_category", "user_sheikhs", "user_sheikh_surahs"}:
            return
        category = str(session.get("category", "chroma"))
        available = available_sheikhs_for_category(payload, category)
        if not available:
            await reply(update, "لا توجد شيوخ متاحون الآن", category_menu(category))
            return
        set_session(uid, screen="user_sheikhs", content_type="sheikhs", page=0, target_name=None, subtarget_name=None)
        await show_targets_screen(update, session, payload, "اختر الشيخ", available, "user_sheikhs", category, "sheikhs")
        return

    if text == "بحث عن سورة":
        if screen not in {"user_category", "user_surahs", "user_search_results"}:
            return
        category = str(session.get("category", "chroma"))
        set_session(uid, screen="user_search_wait", category=category, content_type="surahs", page=0)
        await reply(update, "اكتب اسم السورة أو جزءًا منه")
        return

    if screen == "user_search_wait":
        category = str(session.get("category", "chroma"))
        available = available_surahs_for_category(payload, category)
        matches = find_surahs(text, available)
        if not matches:
            await reply(update, "لم يتم العثور على نتائج. اكتب جزءًا آخر من اسم السورة")
            return
        set_session(uid, screen="user_search_results", page=0, targets=matches, category=category, content_type="surahs")
        await show_targets_screen(update, session, payload, "نتائج البحث", matches, "user_search_results", category, "surahs")
        return

    if screen == "user_surahs":
        category = str(session.get("category", "chroma"))
        targets = list(session.get("targets", available_surahs_for_category(payload, category)))
        page = int(session.get("page", 0))
        page_size = payload["settings"]["page_size"]

        if text == "السابق":
            session["page"] = max(0, page - 1)
            await show_targets_screen(update, session, payload, "اختر السورة", targets, "user_surahs", category, "surahs")
            return
        if text == "التالي":
            max_page = max(0, (len(targets) - 1) // page_size)
            session["page"] = min(max_page, page + 1)
            await show_targets_screen(update, session, payload, "اختر السورة", targets, "user_surahs", category, "surahs")
            return
        if text in targets:
            items = current_items(payload, category, "surahs", text)
            if not items:
                await reply(update, f"لا يوجد محتوى لـ {text}", category_menu(category))
                return
            await reply(update, f"{text}\nعدد العناصر: {len(items)}")
            for item in items:
                await send_item(update.message, item)
            await show_targets_screen(update, session, payload, "اختر السورة", targets, "user_surahs", category, "surahs")
            return

    if screen == "user_sheikhs":
        category = str(session.get("category", "chroma"))
        targets = list(session.get("targets", available_sheikhs_for_category(payload, category)))
        page = int(session.get("page", 0))
        page_size = payload["settings"]["page_size"]

        if text == "السابق":
            session["page"] = max(0, page - 1)
            await show_targets_screen(update, session, payload, "اختر الشيخ", targets, "user_sheikhs", category, "sheikhs")
            return
        if text == "التالي":
            max_page = max(0, (len(targets) - 1) // page_size)
            session["page"] = min(max_page, page + 1)
            await show_targets_screen(update, session, payload, "اختر الشيخ", targets, "user_sheikhs", category, "sheikhs")
            return
        if text in targets:
            surahs = storage.get_surah_targets_for_sheikh(payload, category, text)
            if not surahs:
                await reply(update, f"لا يوجد محتوى لـ {text}", category_menu(category))
                return
            set_session(uid, screen="user_sheikh_surahs", target_name=text, subtarget_name=None, page=0)
            await show_targets_screen(update, session, payload, f"{text} - اختر السورة", surahs, "user_sheikh_surahs", category, "sheikhs", extra={"target_name": text})
            return

    if screen == "user_sheikh_surahs":
        category = str(session.get("category", "chroma"))
        sheikh = str(session.get("target_name", ""))
        surahs = list(session.get("targets", storage.get_surah_targets_for_sheikh(payload, category, sheikh)))
        page = int(session.get("page", 0))
        page_size = payload["settings"]["page_size"]

        if text == "السابق":
            session["page"] = max(0, page - 1)
            await show_targets_screen(update, session, payload, f"{sheikh} - اختر السورة", surahs, "user_sheikh_surahs", category, "sheikhs", extra={"target_name": sheikh})
            return
        if text == "التالي":
            max_page = max(0, (len(surahs) - 1) // page_size)
            session["page"] = min(max_page, page + 1)
            await show_targets_screen(update, session, payload, f"{sheikh} - اختر السورة", surahs, "user_sheikh_surahs", category, "sheikhs", extra={"target_name": sheikh})
            return
        if text in surahs:
            items = current_items(payload, category, "sheikhs", sheikh, text)
            if not items:
                await reply(update, f"لا يوجد محتوى لـ {text}", category_menu(category))
                return
            await reply(update, f"{sheikh} / {text}\nعدد العناصر: {len(items)}")
            for item in items:
                await send_item(update.message, item)
            await show_targets_screen(update, session, payload, f"{sheikh} - اختر السورة", surahs, "user_sheikh_surahs", category, "sheikhs", extra={"target_name": sheikh})
            return

    if screen == "user_search_results":
        category = str(session.get("category", "chroma"))
        targets = list(session.get("targets", []))
        page = int(session.get("page", 0))
        page_size = payload["settings"]["page_size"]
        if text == "السابق":
            session["page"] = max(0, page - 1)
            await show_targets_screen(update, session, payload, "نتائج البحث", targets, "user_search_results", category, "surahs")
            return
        if text == "التالي":
            max_page = max(0, (len(targets) - 1) // page_size)
            session["page"] = min(max_page, page + 1)
            await show_targets_screen(update, session, payload, "نتائج البحث", targets, "user_search_results", category, "surahs")
            return
        if text in targets:
            items = current_items(payload, category, "surahs", text)
            if not items:
                await reply(update, f"لا يوجد محتوى لـ {text}", category_menu(category))
                return
            await reply(update, f"{text}\nعدد العناصر: {len(items)}")
            for item in items:
                await send_item(update.message, item)
            await show_targets_screen(update, session, payload, "نتائج البحث", targets, "user_search_results", category, "surahs")
            return

    await reply(update, "اختر من القائمة", main_menu())


async def handle_admin_text(update: Update, session: Dict[str, object], payload, text: str):
    uid = update.effective_user.id
    screen = session.get("screen", "admin_dashboard")

    if text == "الرئيسية":
        await show_main_menu(update, "الصفحة الرئيسية")
        return

    if screen == "admin_dashboard":
        if text == "إضافة محتوى":
            set_session(uid, screen="admin_add_category", action="add", page=0)
            await reply(update, "اختر القسم للإضافة", admin_category_menu("add"))
            return
        if text == "حذف محتوى":
            set_session(uid, screen="admin_del_category", action="del", page=0)
            await reply(update, "اختر القسم للحذف", admin_category_menu("del"))
            return
        if text == "إضافة شيخ جديد":
            set_session(uid, screen="admin_add_sheikh_name", page=0)
            await reply(update, "اكتب اسم الشيخ الجديد. يمكنك كتابة أكثر من اسم في سطر واحد أو عدة أسطر.")
            return
        if text == "حذف شيخ":
            set_session(uid, screen="admin_remove_sheikh_name", page=0)
            await reply(update, "اكتب اسم الشيخ المراد حذفه. يمكنك كتابة أكثر من اسم في سطر واحد أو عدة أسطر.")
            return
        if text == "الإحصائيات":
            stats = storage.stats(payload)
            await reply(
                update,
                "الإحصائيات\n"
                f"كرومات: {stats['chroma']}\n"
                f"تصاميم: {stats['designs']}\n"
                f"مناظر طبيعية: {stats['nature']}",
                admin_dashboard(),
            )
            return

    if screen == "admin_add_category":
        if text in {"كرومات", "تصاميم"}:
            category = "chroma" if text == "كرومات" else "designs"
            set_session(uid, category=category, screen="admin_add_type", page=0, action="add")
            await reply(update, "اختر النوع", admin_type_menu("add", category))
            return
        if text == "مناظر طبيعية":
            set_session(uid, category="nature", screen="admin_upload_nature", mode="upload_nature", page=0)
            await reply(update, "أرسل الصور أو الفيديوهات أو الملفات الآن. اضغط تم عند الانتهاء.", upload_menu())
            return

    if screen == "admin_add_type":
        if text in {"سور", "شيوخ"}:
            category = str(session.get("category", "chroma"))
            content_type = "surahs" if text == "سور" else "sheikhs"
            set_session(uid, content_type=content_type, screen="admin_add_targets", page=0, subtarget_name=None, target_name=None)
            if content_type == "surahs":
                await show_targets_screen(update, session, payload, "اختر السورة", SURAHS, "admin_add_targets", category, content_type)
            else:
                await show_targets_screen(update, session, payload, "اختر الشيخ", current_targets("sheikhs", payload), "admin_add_targets", category, content_type)
            return

    if screen == "admin_add_targets":
        content_type = str(session.get("content_type", "surahs"))
        category = str(session.get("category", "chroma"))
        targets = list(session.get("targets", SURAHS if content_type == "surahs" else current_targets("sheikhs", payload)))
        page = int(session.get("page", 0))
        page_size = payload["settings"]["page_size"]

        if text == "السابق":
            session["page"] = max(0, page - 1)
            if content_type == "surahs":
                await show_targets_screen(update, session, payload, "اختر السورة", SURAHS, "admin_add_targets", category, content_type)
            else:
                await show_targets_screen(update, session, payload, "اختر الشيخ", current_targets("sheikhs", payload), "admin_add_targets", category, content_type)
            return
        if text == "التالي":
            max_page = max(0, (len(targets) - 1) // page_size)
            session["page"] = min(max_page, page + 1)
            if content_type == "surahs":
                await show_targets_screen(update, session, payload, "اختر السورة", SURAHS, "admin_add_targets", category, content_type)
            else:
                await show_targets_screen(update, session, payload, "اختر الشيخ", current_targets("sheikhs", payload), "admin_add_targets", category, content_type)
            return
        if text in targets:
            if content_type == "surahs":
                set_session(uid, target_name=text, subtarget_name=None, screen="admin_upload_target", mode="upload", return_screen="admin_add_targets")
                await reply(update, f"أرسل المحتوى الآن لـ {text}. يمكنك إرسال صورة أو فيديو أو ملف أكثر من مرة.", upload_menu())
                return
            set_session(uid, target_name=text, subtarget_name=None, screen="admin_add_sheikh_mode", page=0)
            await reply(update, "اختر طريقة الإضافة", sheikh_mode_menu())
            return

    if screen == "admin_add_sheikh_mode":
        category = str(session.get("category", "chroma"))
        sheikh = str(session.get("target_name", ""))
        if text == "سور":
            set_session(uid, screen="admin_add_sheikh_surah", page=0, return_screen="admin_add_sheikh_mode")
            await show_targets_screen(update, session, payload, f"{sheikh} - اختر السورة", SURAHS, "admin_add_sheikh_surah", category, "sheikhs", extra={"target_name": sheikh})
            return
        if text == "عشوائي":
            set_session(uid, subtarget_name="عشوائي", screen="admin_upload_target", mode="upload", return_screen="admin_add_sheikh_mode")
            await reply(update, f"أرسل المحتوى الآن لـ {sheikh} / عشوائي. يمكنك إرسال صورة أو فيديو أو ملف أكثر من مرة.", upload_menu())
            return

    if screen == "admin_add_sheikh_surah":
        category = str(session.get("category", "chroma"))
        sheikh = str(session.get("target_name", ""))
        page = int(session.get("page", 0))
        page_size = payload["settings"]["page_size"]

        if text == "السابق":
            session["page"] = max(0, page - 1)
            await show_targets_screen(update, session, payload, f"{sheikh} - اختر السورة", SURAHS, "admin_add_sheikh_surah", category, "sheikhs", extra={"target_name": sheikh})
            return
        if text == "التالي":
            max_page = max(0, (len(SURAHS) - 1) // page_size)
            session["page"] = min(max_page, page + 1)
            await show_targets_screen(update, session, payload, f"{sheikh} - اختر السورة", SURAHS, "admin_add_sheikh_surah", category, "sheikhs", extra={"target_name": sheikh})
            return
        if text in SURAHS:
            set_session(uid, subtarget_name=text, screen="admin_upload_target", mode="upload", return_screen="admin_add_sheikh_surah")
            await reply(update, f"أرسل المحتوى الآن لـ {sheikh} / {text}. يمكنك إرسال صورة أو فيديو أو ملف أكثر من مرة.", upload_menu())
            return

    if screen in {"admin_upload_target", "admin_upload_nature"}:
        if text == "إلغاء":
            previous = str(session.get("return_screen", "admin_dashboard"))
            if previous == "admin_add_sheikh_surah":
                sheikh = str(session.get("target_name", ""))
                set_session(uid, screen="admin_add_sheikh_mode", page=0)
                await reply(update, "اختر طريقة الإضافة", sheikh_mode_menu())
                return
            if previous == "admin_add_sheikh_mode":
                sheikh = str(session.get("target_name", ""))
                set_session(uid, screen="admin_add_sheikh_mode", page=0)
                await reply(update, "اختر طريقة الإضافة", sheikh_mode_menu())
                return
            if previous == "admin_add_targets":
                action = str(session.get("action", "add"))
                category = str(session.get("category", "chroma"))
                set_session(uid, screen="admin_add_type", page=0)
                await reply(update, "اختر النوع", admin_type_menu(action, category))
                return
            set_session(uid, screen="admin_dashboard", page=0)
            await reply(update, "تم الإلغاء", admin_dashboard())
            return
        if text == "تم":
            previous = str(session.get("return_screen", "admin_dashboard"))
            if previous == "admin_add_sheikh_surah":
                sheikh = str(session.get("target_name", ""))
                set_session(uid, screen="admin_add_sheikh_mode", page=0)
                await reply(update, "تم حفظ المحتوى", sheikh_mode_menu())
                return
            if previous == "admin_add_sheikh_mode":
                set_session(uid, screen="admin_add_sheikh_mode", page=0)
                await reply(update, "تم حفظ المحتوى", sheikh_mode_menu())
                return
            if previous == "admin_add_targets":
                action = str(session.get("action", "add"))
                category = str(session.get("category", "chroma"))
                set_session(uid, screen="admin_add_type", page=0)
                await reply(update, "تم حفظ المحتوى", admin_type_menu(action, category))
                return
            set_session(uid, screen="admin_dashboard", page=0)
            await reply(update, "تم حفظ المحتوى", admin_dashboard())
            return
        await reply(update, "أرسل صورة أو فيديو أو ملف، أو اضغط تم", upload_menu())
        return

    if screen == "admin_del_category":
        if text in {"كرومات", "تصاميم"}:
            category = "chroma" if text == "كرومات" else "designs"
            set_session(uid, category=category, screen="admin_del_type", page=0, action="del")
            await reply(update, "اختر النوع", admin_type_menu("del", category))
            return
        if text == "مناظر طبيعية":
            items = payload["categories"]["nature"]
            if not items:
                set_session(uid, screen="admin_dashboard", page=0)
                await reply(update, "لا يوجد محتوى للحذف", admin_dashboard())
                return
            set_session(uid, category="nature", content_type=None, target_name=None, subtarget_name=None, screen="admin_del_nature_items", page=0)
            markup, page, total_pages, _indices = items_menu(len(items), 0, payload["settings"]["item_page_size"])
            session["page"] = page
            await reply(update, page_text("المناظر الطبيعية", page, total_pages), markup)
            return

    if screen == "admin_del_type":
        if text in {"سور", "شيوخ"}:
            category = str(session.get("category", "chroma"))
            content_type = "surahs" if text == "سور" else "sheikhs"
            set_session(uid, content_type=content_type, screen="admin_del_targets", page=0, subtarget_name=None, target_name=None)
            if content_type == "surahs":
                targets = available_surahs_for_category(payload, category)
                if not targets:
                    set_session(uid, screen="admin_dashboard", page=0)
                    await reply(update, "لا يوجد محتوى للحذف", admin_dashboard())
                    return
                await show_targets_screen(update, session, payload, "اختر السورة للحذف", targets, "admin_del_targets", category, content_type)
            else:
                targets = available_sheikhs_for_category(payload, category)
                if not targets:
                    set_session(uid, screen="admin_dashboard", page=0)
                    await reply(update, "لا يوجد محتوى للحذف", admin_dashboard())
                    return
                await show_targets_screen(update, session, payload, "اختر الشيخ للحذف", targets, "admin_del_targets", category, content_type)
            return

    if screen == "admin_del_targets":
        content_type = str(session.get("content_type", "surahs"))
        category = str(session.get("category", "chroma"))
        targets = list(session.get("targets", []))
        page = int(session.get("page", 0))
        page_size = payload["settings"]["page_size"]

        if text == "السابق":
            session["page"] = max(0, page - 1)
            title = "اختر السورة للحذف" if content_type == "surahs" else "اختر الشيخ للحذف"
            await show_targets_screen(update, session, payload, title, targets, "admin_del_targets", category, content_type)
            return
        if text == "التالي":
            max_page = max(0, (len(targets) - 1) // page_size)
            session["page"] = min(max_page, page + 1)
            title = "اختر السورة للحذف" if content_type == "surahs" else "اختر الشيخ للحذف"
            await show_targets_screen(update, session, payload, title, targets, "admin_del_targets", category, content_type)
            return
        if text in targets:
            if content_type == "surahs":
                items = current_items(payload, category, "surahs", text)
                if not items:
                    set_session(uid, screen="admin_dashboard", page=0)
                    await reply(update, "لا يوجد عناصر للحذف", admin_dashboard())
                    return
                set_session(uid, target_name=text, subtarget_name=None, screen="admin_del_items", page=0)
                markup, page, total_pages, _indices = items_menu(len(items), 0, payload["settings"]["item_page_size"])
                session["page"] = page
                await reply(update, page_text(f"حذف {text}", page, total_pages), markup)
                return
            set_session(uid, target_name=text, subtarget_name=None, screen="admin_del_sheikh_surah", page=0)
            surahs = storage.get_surah_targets_for_sheikh(payload, category, text)
            if not surahs:
                set_session(uid, screen="admin_dashboard", page=0)
                await reply(update, "لا يوجد محتوى للحذف", admin_dashboard())
                return
            await show_targets_screen(update, session, payload, f"{text} - اختر السورة للحذف", surahs, "admin_del_sheikh_surah", category, "sheikhs", extra={"target_name": text})
            return

    if screen == "admin_del_sheikh_surah":
        category = str(session.get("category", "chroma"))
        sheikh = str(session.get("target_name", ""))
        surahs = list(session.get("targets", storage.get_surah_targets_for_sheikh(payload, category, sheikh)))
        page = int(session.get("page", 0))
        page_size = payload["settings"]["page_size"]

        if text == "السابق":
            session["page"] = max(0, page - 1)
            await show_targets_screen(update, session, payload, f"{sheikh} - اختر السورة للحذف", surahs, "admin_del_sheikh_surah", category, "sheikhs", extra={"target_name": sheikh})
            return
        if text == "التالي":
            max_page = max(0, (len(surahs) - 1) // page_size)
            session["page"] = min(max_page, page + 1)
            await show_targets_screen(update, session, payload, f"{sheikh} - اختر السورة للحذف", surahs, "admin_del_sheikh_surah", category, "sheikhs", extra={"target_name": sheikh})
            return
        if text in surahs:
            items = current_items(payload, category, "sheikhs", sheikh, text)
            if not items:
                set_session(uid, screen="admin_dashboard", page=0)
                await reply(update, "لا يوجد عناصر للحذف", admin_dashboard())
                return
            set_session(uid, target_name=sheikh, subtarget_name=text, screen="admin_del_items", page=0)
            markup, page, total_pages, _indices = items_menu(len(items), 0, payload["settings"]["item_page_size"])
            session["page"] = page
            await reply(update, page_text(f"حذف {sheikh} / {text}", page, total_pages), markup)
            return

    if screen == "admin_del_items":
        category = str(session.get("category", "chroma"))
        content_type = session.get("content_type")
        target_name = session.get("target_name")
        subtarget_name = session.get("subtarget_name")
        items = current_items(payload, category, content_type, target_name, subtarget_name)
        page_size = payload["settings"]["item_page_size"]
        page = int(session.get("page", 0))

        if text == "السابق":
            session["page"] = max(0, page - 1)
            markup, page, total_pages, _indices = items_menu(len(items), session["page"], page_size)
            session["page"] = page
            title = f"حذف {target_name}" if content_type == "surahs" else f"حذف {target_name} / {subtarget_name}"
            await reply(update, page_text(title, page, total_pages), markup)
            return
        if text == "التالي":
            max_page = max(0, (max(1, len(items)) - 1) // page_size)
            session["page"] = min(max_page, page + 1)
            markup, page, total_pages, _indices = items_menu(len(items), session["page"], page_size)
            session["page"] = page
            title = f"حذف {target_name}" if content_type == "surahs" else f"حذف {target_name} / {subtarget_name}"
            await reply(update, page_text(title, page, total_pages), markup)
            return
        if text == "حذف الكل":
            set_session(uid, screen="admin_clear_confirm", return_screen="admin_del_items")
            await reply(update, "هل تريد حذف كل العناصر؟", clear_confirm_menu())
            return
        m = re.match(r"^حذف (\d+)$", text)
        if m:
            item_index = int(m.group(1)) - 1
            if storage.remove_item(payload, category, content_type, target_name, item_index, subtarget_name):
                storage.save(payload)
                items = current_items(payload, category, content_type, target_name, subtarget_name)
                markup, page, total_pages, _indices = items_menu(len(items), page, page_size)
                session["page"] = page
                title = f"حذف {target_name}" if content_type == "surahs" else f"حذف {target_name} / {subtarget_name}"
                await reply(update, "تم حذف العنصر", markup)
            else:
                await reply(update, "العنصر غير موجود", admin_dashboard())
                set_session(uid, screen="admin_dashboard", page=0)
            return

    if screen == "admin_del_nature_items":
        items = payload["categories"]["nature"]
        page_size = payload["settings"]["item_page_size"]
        page = int(session.get("page", 0))

        if text == "السابق":
            session["page"] = max(0, page - 1)
            markup, page, total_pages, _indices = items_menu(len(items), session["page"], page_size)
            session["page"] = page
            await reply(update, page_text("المناظر الطبيعية", page, total_pages), markup)
            return
        if text == "التالي":
            max_page = max(0, (max(1, len(items)) - 1) // page_size)
            session["page"] = min(max_page, page + 1)
            markup, page, total_pages, _indices = items_menu(len(items), session["page"], page_size)
            session["page"] = page
            await reply(update, page_text("المناظر الطبيعية", page, total_pages), markup)
            return
        if text == "حذف الكل":
            set_session(uid, screen="admin_clear_confirm", return_screen="admin_del_nature_items")
            await reply(update, "هل تريد حذف كل العناصر؟", clear_confirm_menu())
            return
        m = re.match(r"^حذف (\d+)$", text)
        if m:
            item_index = int(m.group(1)) - 1
            if storage.remove_item(payload, "nature", None, None, item_index):
                storage.save(payload)
                items = payload["categories"]["nature"]
                markup, page, total_pages, _indices = items_menu(len(items), page, page_size)
                session["page"] = page
                await reply(update, "تم حذف العنصر", markup)
            else:
                await reply(update, "العنصر غير موجود", admin_dashboard())
                set_session(uid, screen="admin_dashboard", page=0)
            return

    if screen == "admin_clear_confirm":
        if text == "نعم، احذف الكل":
            category = str(session.get("category", "chroma"))
            content_type = session.get("content_type")
            target_name = session.get("target_name")
            subtarget_name = session.get("subtarget_name")
            if category == "nature":
                storage.clear_target(payload, "nature", None, None)
            else:
                storage.clear_target(payload, category, content_type, target_name, subtarget_name)
            storage.save(payload)
            set_session(uid, screen="admin_dashboard", page=0)
            await reply(update, "تم حذف الكل", admin_dashboard())
            return
        if text == "إلغاء":
            previous = str(session.get("return_screen", "admin_dashboard"))
            if previous == "admin_del_items":
                category = str(session.get("category", "chroma"))
                content_type = session.get("content_type")
                target_name = session.get("target_name")
                subtarget_name = session.get("subtarget_name")
                items = current_items(payload, category, content_type, target_name, subtarget_name)
                markup, page, total_pages, _indices = items_menu(len(items), int(session.get("page", 0)), payload["settings"]["item_page_size"])
                set_session(uid, screen="admin_del_items", page=page)
                await reply(update, "تم الإلغاء", markup)
                return
            if previous == "admin_del_nature_items":
                items = payload["categories"]["nature"]
                markup, page, total_pages, _indices = items_menu(len(items), int(session.get("page", 0)), payload["settings"]["item_page_size"])
                set_session(uid, screen="admin_del_nature_items", page=page)
                await reply(update, "تم الإلغاء", markup)
                return
            set_session(uid, screen="admin_dashboard", page=0)
            await reply(update, "تم الإلغاء", admin_dashboard())
            return

    if screen == "admin_add_sheikh_name":
        names = [n.strip() for n in re.split(r"[\n,؛]+", text) if n.strip()]
        if not names:
            await reply(update, "اكتب اسمًا واحدًا على الأقل")
            return
        added = storage.add_sheikh_names(payload, names)
        storage.save(payload)
        set_session(uid, screen="admin_dashboard", page=0)
        if added:
            await reply(update, "تم إضافة الشيوخ التالية أسماؤهم:\n" + "\n".join(added), admin_dashboard())
        else:
            await reply(update, "كل الأسماء موجودة بالفعل", admin_dashboard())
        return

    if screen == "admin_remove_sheikh_name":
        names = [n.strip() for n in re.split(r"[\n,؛]+", text) if n.strip()]
        if not names:
            await reply(update, "اكتب اسمًا واحدًا على الأقل")
            return
        removed = storage.remove_sheikh_names(payload, names)
        storage.save(payload)
        set_session(uid, screen="admin_dashboard", page=0)
        if removed:
            await reply(update, "تم حذف الشيوخ التالية أسماؤهم:\n" + "\n".join(removed), admin_dashboard())
        else:
            await reply(update, "لم يتم العثور على الأسماء", admin_dashboard())
        return

    await reply(update, "اختر من القائمة", admin_dashboard())


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

    if text == "الرئيسية":
        await handle_home(update, session)
        return
    if text == "رجوع":
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
        await msg.reply_text("أرسل صورة أو فيديو أو ملف", reply_markup=upload_menu())
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
            str(session.get("subtarget_name")) if session.get("subtarget_name") else None,
        )

    storage.save(data)
    await msg.reply_text("تم الحفظ، أرسل المزيد أو اضغط تم", reply_markup=upload_menu())


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
