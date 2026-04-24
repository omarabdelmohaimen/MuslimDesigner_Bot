import os
import re
import math
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0") or 0)
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

SURAH_LIST = [
    ("الفاتحة", 1), ("البقرة", 2), ("آل عمران", 3), ("النساء", 4), ("المائدة", 5), ("الأنعام", 6),
    ("الأعراف", 7), ("الأنفال", 8), ("التوبة", 9), ("يونس", 10), ("هود", 11), ("يوسف", 12),
    ("الرعد", 13), ("إبراهيم", 14), ("الحجر", 15), ("النحل", 16), ("الإسراء", 17), ("الكهف", 18),
    ("مريم", 19), ("طه", 20), ("الأنبياء", 21), ("الحج", 22), ("المؤمنون", 23), ("النور", 24),
    ("الفرقان", 25), ("الشعراء", 26), ("النمل", 27), ("القصص", 28), ("العنكبوت", 29), ("الروم", 30),
    ("لقمان", 31), ("السجدة", 32), ("الأحزاب", 33), ("سبأ", 34), ("فاطر", 35), ("يس", 36),
    ("الصافات", 37), ("ص", 38), ("الزمر", 39), ("غافر", 40), ("فصلت", 41), ("الشورى", 42),
    ("الزخرف", 43), ("الدخان", 44), ("الجاثية", 45), ("الأحقاف", 46), ("محمد", 47), ("الفتح", 48),
    ("الحجرات", 49), ("ق", 50), ("الذاريات", 51), ("الطور", 52), ("النجم", 53), ("القمر", 54),
    ("الرحمن", 55), ("الواقعة", 56), ("الحديد", 57), ("المجادلة", 58), ("الحشر", 59), ("الممتحنة", 60),
    ("الصف", 61), ("الجمعة", 62), ("المنافقون", 63), ("التغابن", 64), ("الطلاق", 65), ("التحريم", 66),
    ("الملك", 67), ("القلم", 68), ("الحاقة", 69), ("المعارج", 70), ("نوح", 71), ("الجن", 72),
    ("المزمل", 73), ("المدثر", 74), ("القيامة", 75), ("الإنسان", 76), ("المرسلات", 77), ("النبأ", 78),
    ("النازعات", 79), ("عبس", 80), ("التكوير", 81), ("الانفطار", 82), ("المطففين", 83), ("الانشقاق", 84),
    ("البروج", 85), ("الطارق", 86), ("الأعلى", 87), ("الغاشية", 88), ("الفجر", 89), ("البلد", 90),
    ("الشمس", 91), ("الليل", 92), ("الضحى", 93), ("الشرح", 94), ("التين", 95), ("العلق", 96),
    ("القدر", 97), ("البينة", 98), ("الزلزلة", 99), ("العاديات", 100), ("القارعة", 101), ("التكاثر", 102),
    ("العصر", 103), ("الهمزة", 104), ("الفيل", 105), ("قريش", 106), ("الماعون", 107), ("الكوثر", 108),
    ("الكافرون", 109), ("النصر", 110), ("المسد", 111), ("الإخلاص", 112), ("الفلق", 113), ("الناس", 114),
]

if not BOT_TOKEN or not ADMIN_ID or not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Missing env vars: BOT_TOKEN, ADMIN_ID, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY")

state: Dict[int, Dict[str, Any]] = {}
PAGE_SIZE = 10

# -------------------- Supabase REST helpers --------------------

def headers() -> Dict[str, str]:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

def request(method: str, table: str, params: Optional[Dict[str, str]] = None, json_body: Any = None, prefer: Optional[str] = None):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    h = headers()
    if prefer:
        h["Prefer"] = prefer
    r = requests.request(method, url, headers=h, params=params, json=json_body, timeout=30)
    r.raise_for_status()
    if r.text.strip():
        return r.json()
    return None

def select_rows(table: str, columns: str = "*", filters: Optional[List[Tuple[str, str, Any]]] = None, order: Optional[str] = None, limit: Optional[int] = None):
    params: Dict[str, str] = {"select": columns}
    if filters:
        for col, op, value in filters:
            params[col] = f"{op}.{value}"
    if order:
        params["order"] = order
    if limit is not None:
        params["limit"] = str(limit)
    return request("GET", table, params=params) or []

def insert_rows(table: str, payload: Any):
    return request("POST", table, json_body=payload, prefer="return=minimal")

def delete_rows(table: str, filters: List[Tuple[str, str, Any]]):
    params: Dict[str, str] = {}
    for col, op, value in filters:
        params[col] = f"{op}.{value}"
    return request("DELETE", table, params=params, prefer="return=minimal")

def seed_surahs_if_needed():
    rows = select_rows("surahs", "id", limit=1)
    if rows:
        return
    insert_rows("surahs", [{"id": sid, "name": name} for name, sid in SURAH_LIST])

# -------------------- UI helpers --------------------

def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [["كرومات", "تصاميم"], ["مناظر طبيعية", "بحث في السور"], ["مساعدة"]],
        resize_keyboard=True,
        input_field_placeholder="اختر من القائمة",
    )

def admin_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [["إضافة محتوى", "إضافة شيخ"], ["حذف شيخ", "إحصائيات"], ["رجوع"]],
        resize_keyboard=True,
        input_field_placeholder="لوحة التحكم",
    )

def section_menu(section: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [["سور", "شيوخ"], ["عشوائي", "رجوع"]],
        resize_keyboard=True,
        input_field_placeholder=f"{section}",
    )

def upload_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([["إنهاء"], ["رجوع"]], resize_keyboard=True)

def paged_list_text(items: List[str], title: str, page: int, prefix: str) -> str:
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    chunk = items[start:end]
    total_pages = max(1, math.ceil(len(items) / PAGE_SIZE))
    lines = [title, ""]
    for i, item in enumerate(chunk, start=start + 1):
        lines.append(f"{i}. {item}")
    lines.append("")
    lines.append(f"الصفحة {page + 1} من {total_pages}")
    lines.append("اكتب: التالي / السابق / رجوع")
    lines.append("أو اكتب رقم العنصر مباشرة")
    return "\n".join(lines)

def current_page_items(key: str) -> List[Dict[str, Any]]:
    return state.get(ADMIN_ID if key.startswith("admin") else 0, {}).get("items", [])

def available_surahs(section: str) -> List[Tuple[int, str]]:
    used = select_rows("media", "surah_id", filters=[("section", "eq", section), ("category", "eq", "surah")], order="surah_id.asc")
    ids = {r["surah_id"] for r in used if r.get("surah_id") is not None}
    return [(sid, name) for name, sid in SURAH_LIST if sid in ids]

def available_sheikhs(section: str) -> List[Tuple[int, str]]:
    used = select_rows("media", "sheikh_id", filters=[("section", "eq", section), ("category", "eq", "sheikh")], order="sheikh_id.asc")
    ids = {r["sheikh_id"] for r in used if r.get("sheikh_id") is not None}
    rows = select_rows("sheikhs", "id,name", order="name.asc")
    return [(r["id"], r["name"]) for r in rows if r["id"] in ids]

def all_surahs() -> List[Tuple[int, str]]:
    return SURAH_LIST

def all_sheikhs() -> List[Tuple[int, str]]:
    rows = select_rows("sheikhs", "id,name", order="name.asc")
    return [(r["id"], r["name"]) for r in rows]

def get_media(section: str, category: str, item_id: Optional[int] = None):
    filters = [("section", "eq", section), ("category", "eq", category)]
    if category == "surah" and item_id is not None:
        filters.append(("surah_id", "eq", item_id))
    elif category == "sheikh" and item_id is not None:
        filters.append(("sheikh_id", "eq", item_id))
    return select_rows("media", "file_id,file_kind", filters=filters, order="id.asc")

def add_media(section: str, category: str, file_id: str, file_kind: str, item_id: Optional[int] = None):
    payload = {"section": section, "category": category, "file_id": file_id, "file_kind": file_kind, "caption": None}
    if category == "surah":
        payload["surah_id"] = item_id
    elif category == "sheikh":
        payload["sheikh_id"] = item_id
    insert_rows("media", payload)

def delete_sheikh(sheikh_id: int):
    delete_rows("media", [("sheikh_id", "eq", sheikh_id)])
    delete_rows("sheikhs", [("id", "eq", sheikh_id)])

async def send_media(message, row, caption=None):
    if row["file_kind"] == "photo":
        await message.reply_photo(row["file_id"], caption=caption or None)
    elif row["file_kind"] == "video":
        await message.reply_video(row["file_id"], caption=caption or None)
    elif row["file_kind"] == "document":
        await message.reply_document(row["file_id"], caption=caption or None)
    else:
        await message.reply_text(caption or "نوع ملف غير مدعوم")

def make_title(section: str) -> str:
    return {"chroma": "كرومات", "designs": "تصاميم", "nature": "مناظر طبيعية"}.get(section, section)

# -------------------- Commands --------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state.pop(update.effective_user.id, None)
    await update.message.reply_text("أهلا بك", reply_markup=main_menu())

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("غير مسموح")
        return
    state[ADMIN_ID] = {"mode": "admin_home"}
    await update.message.reply_text("لوحة التحكم", reply_markup=admin_menu())

# -------------------- Message router --------------------

async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = (update.message.text or "").strip()
    s = state.get(uid, {})

    if uid == ADMIN_ID and text == "رجوع":
        mode = s.get("mode", "")
        if mode in {"admin_add_content", "pick_section", "pick_type", "pick_item", "upload", "upload_nature", "upload_random"}:
            state[uid] = {"mode": "admin_home"}
            await update.message.reply_text("لوحة التحكم", reply_markup=admin_menu())
            return
        state[uid] = {"mode": "admin_home"}
        await update.message.reply_text("لوحة التحكم", reply_markup=admin_menu())
        return

    if text == "مساعدة":
        await update.message.reply_text(
            "اكتب اسم القسم ثم اختر بالترتيب.\n"
            "الأدمن يدخل /admin فقط."
        )
        return

    if text == "كرومات":
        state[uid] = {"mode": "browse_section", "section": "chroma"}
        await update.message.reply_text("اختر", reply_markup=section_menu("chroma"))
        return

    if text == "تصاميم":
        state[uid] = {"mode": "browse_section", "section": "designs"}
        await update.message.reply_text("اختر", reply_markup=section_menu("designs"))
        return

    if text == "مناظر طبيعية":
        rows = get_media("nature", "nature")
        if not rows:
            await update.message.reply_text("لا يوجد محتوى بعد")
            return
        for row in rows:
            await send_media(update.message, row, "مناظر طبيعية")
        return

    if text == "بحث في السور":
        state[uid] = {"mode": "search_surah"}
        await update.message.reply_text("اكتب اسم السورة أو جزء منه")
        return

    if uid == ADMIN_ID and text == "إضافة محتوى":
        state[uid] = {"mode": "pick_section"}
        await update.message.reply_text("اختر القسم", reply_markup=section_menu("admin"))
        return

    if uid == ADMIN_ID and text == "إضافة شيخ":
        state[uid] = {"mode": "add_sheikh"}
        await update.message.reply_text("اكتب اسم الشيخ أو عدة أسماء في سطور منفصلة", reply_markup=ReplyKeyboardRemove())
        return

    if uid == ADMIN_ID and text == "حذف شيخ":
        rows = all_sheikhs()
        if not rows:
            await update.message.reply_text("لا يوجد شيوخ")
            return
        state[uid] = {"mode": "delete_sheikh_list", "items": rows, "page": 0}
        await update.message.reply_text(paged_list_text([n for _, n in rows], "اختر الشيخ للحذف", 0, "delete"))
        return

    if uid == ADMIN_ID and text == "إحصائيات":
        media_count = len(select_rows("media", "id"))
        sheikh_count = len(select_rows("sheikhs", "id"))
        await update.message.reply_text(f"إحصائيات\nالمحتوى: {media_count}\nالشيوخ: {sheikh_count}")
        return

    # search mode
    if s.get("mode") == "search_surah":
        query = text.lower()
        used = {sid for sid, _ in available_surahs("chroma")} | {sid for sid, _ in available_surahs("designs")}
        matches = [(sid, name) for name, sid in SURAH_LIST if sid in used and query in name.lower()]
        if not matches:
            await update.message.reply_text("لا توجد نتائج")
            return
        state[uid] = {"mode": "search_results", "items": matches, "page": 0}
        await update.message.reply_text(paged_list_text([f"{sid}. {name}" for sid, name in matches], "نتائج البحث", 0, "search"))
        return

    # browsing by section
    if s.get("mode") == "browse_section":
        section = s.get("section")
        if text == "سور":
            items = available_surahs(section)
            if not items:
                await update.message.reply_text("لا يوجد محتوى متاح")
                return
            state[uid] = {"mode": "browse_list", "section": section, "category": "surah", "items": items, "page": 0}
            await update.message.reply_text(paged_list_text([f"{sid}. {name}" for sid, name in items], f"{make_title(section)} - سور", 0, "browse"))
            return

        if text == "شيوخ":
            items = available_sheikhs(section)
            if not items:
                await update.message.reply_text("لا يوجد شيوخ متاحون")
                return
            state[uid] = {"mode": "browse_list", "section": section, "category": "sheikh", "items": items, "page": 0}
            await update.message.reply_text(paged_list_text([name for _, name in items], f"{make_title(section)} - شيوخ", 0, "browse"))
            return

        if text == "عشوائي":
            rows = get_media(section, "random")
            if not rows:
                await update.message.reply_text("لا يوجد محتوى عشوائي")
                return
            for row in rows:
                await send_media(update.message, row, f"{make_title(section)} - عشوائي")
            return

    # admin menus
    if uid == ADMIN_ID and s.get("mode") == "pick_section":
        if text in {"كرومات", "تصاميم", "مناظر طبيعية"}:
            section = {"كرومات": "chroma", "تصاميم": "designs", "مناظر طبيعية": "nature"}[text]
            state[uid] = {"mode": "pick_type", "section": section}
            if section == "nature":
                state[uid] = {"mode": "upload_nature", "section": section}
                await update.message.reply_text("أرسل الملفات الآن", reply_markup=upload_menu())
                return
            await update.message.reply_text("اختر النوع", reply_markup=section_menu(section))
            return

    if uid == ADMIN_ID and s.get("mode") == "pick_type":
        section = s.get("section")
        if text == "سور":
            items = all_surahs()
            state[uid] = {"mode": "pick_item", "section": section, "category": "surah", "items": items, "page": 0}
            await update.message.reply_text(paged_list_text([f"{sid}. {name}" for sid, name in items], f"{make_title(section)} - سور", 0, "admin_surah"))
            return
        if text == "شيوخ":
            items = all_sheikhs()
            state[uid] = {"mode": "pick_item", "section": section, "category": "sheikh", "items": items, "page": 0}
            if not items:
                await update.message.reply_text("لا يوجد شيوخ. أضف شيخًا أولًا", reply_markup=admin_menu())
                return
            await update.message.reply_text(paged_list_text([name for _, name in items], f"{make_title(section)} - شيوخ", 0, "admin_sheikh"))
            return
        if text == "عشوائي":
            state[uid] = {"mode": "upload_random", "section": section}
            await update.message.reply_text("أرسل الملفات الآن", reply_markup=upload_menu())
            return

    # pagination words for any list mode
    if s.get("mode") in {"browse_list", "search_results", "pick_item", "delete_sheikh_list"}:
        items = s.get("items", [])
        page = int(s.get("page", 0))

        if text == "التالي":
            new_page = page + 1
            if new_page * PAGE_SIZE < len(items):
                s["page"] = new_page
                state[uid] = s
            await update.message.reply_text(paged_list_text([f"{a}. {b}" if isinstance(a, int) else a for a, b in items] if items and isinstance(items[0], tuple) else [str(x) for x in items], "القائمة", s["page"], "list"))
            return

        if text == "السابق":
            new_page = max(0, page - 1)
            s["page"] = new_page
            state[uid] = s
            await update.message.reply_text(paged_list_text([f"{a}. {b}" if isinstance(a, int) else a for a, b in items] if items and isinstance(items[0], tuple) else [str(x) for x in items], "القائمة", s["page"], "list"))
            return

        if text == "رجوع":
            state.pop(uid, None)
            if uid == ADMIN_ID and s.get("mode") != "browse_list":
                await update.message.reply_text("لوحة التحكم", reply_markup=admin_menu())
            else:
                await update.message.reply_text("أهلا بك", reply_markup=main_menu())
            return

        if text.isdigit():
            idx = int(text)
            if 1 <= idx <= len(items):
                chosen = items[idx - 1]
                if s.get("mode") in {"browse_list", "search_results"}:
                    sid, name = chosen
                    cats = []
                    if uid == ADMIN_ID:
                        cats = []
                    # gather media from both sections
                    media = get_media("chroma", "surah", sid) + get_media("designs", "surah", sid)
                    if not media:
                        await update.message.reply_text("لا يوجد محتوى")
                        return
                    await update.message.reply_text(f"المحتوى: {name}")
                    for row in media:
                        await send_media(update.message, row, name)
                    return

                if s.get("mode") == "pick_item":
                    section = s["section"]
                    category = s["category"]
                    item_id, name = chosen
                    state[uid] = {"mode": "upload", "section": section, "category": category, "item_id": item_id}
                    await update.message.reply_text(f"أرسل الوسائط الآن لـ {name}", reply_markup=upload_menu())
                    return

                if s.get("mode") == "delete_sheikh_list":
                    sheikh_id, name = chosen
                    delete_sheikh(sheikh_id)
                    state[uid] = {"mode": "admin_home"}
                    await update.message.reply_text("تم الحذف", reply_markup=admin_menu())
                    return

async def on_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != ADMIN_ID:
        return
    s = state.get(uid, {})
    if s.get("mode") not in {"upload", "upload_nature", "upload_random"}:
        return

    msg = update.effective_message
    file_id = None
    file_kind = None
    if msg.photo:
        file_id = msg.photo[-1].file_id
        file_kind = "photo"
    elif msg.video:
        file_id = msg.video.file_id
        file_kind = "video"
    elif msg.document:
        file_id = msg.document.file_id
        file_kind = "document"
    else:
        return

    if s["mode"] == "upload_nature":
        add_media("nature", "nature", file_id, file_kind)
    elif s["mode"] == "upload_random":
        add_media(s["section"], "random", file_id, file_kind)
    else:
        add_media(s["section"], s["category"], file_id, file_kind, s.get("item_id"))

    await msg.reply_text("تم الحفظ", reply_markup=upload_menu())

def register(app: Application):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL, on_media))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

def main():
    seed_surahs_if_needed()
    app = Application.builder().token(BOT_TOKEN).build()
    register(app)
    app.run_polling()

if __name__ == "__main__":
    main()
