import os
import re
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from supabase import create_client, Client
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0") or 0)
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

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

if not BOT_TOKEN or not ADMIN_ID or not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise RuntimeError("Missing env vars: BOT_TOKEN, ADMIN_ID, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY")

sb: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
state: Dict[int, Dict[str, Any]] = {}

# ---------- DB bootstrap ----------

def seed_surahs_if_needed() -> None:
    try:
        first = sb.table("surahs").select("id").limit(1).execute().data or []
    except Exception as exc:
        raise RuntimeError("Supabase tables are missing. Run supabase_schema.sql first.") from exc
    if first:
        return
    payload = [{"id": sid, "name": name} for name, sid in SURAH_LIST]
    sb.table("surahs").insert(payload).execute()

def _fetch(table: str, select: str = "*", **filters):
    q = sb.table(table).select(select)
    for k, v in filters.items():
        if v is None:
            continue
        q = q.eq(k, v)
    return q.execute().data or []

def _fetch_one(table: str, select: str = "*", **filters):
    rows = _fetch(table, select, **filters)
    return rows[0] if rows else None

def _insert(table: str, payload: Dict[str, Any]) -> None:
    sb.table(table).insert(payload).execute()

# ---------- keyboards ----------

def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [["كرومات", "تصاميم"], ["مناظر طبيعية", "بحث في السور"]],
        resize_keyboard=True,
        input_field_placeholder="اختر من القائمة",
    )

def admin_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [["إضافة محتوى", "إضافة شيخ"], ["حذف شيخ", "إحصائيات"], ["رجوع"]],
        resize_keyboard=True,
        input_field_placeholder="لوحة التحكم",
    )

def upload_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([["إنهاء"], ["رجوع"]], resize_keyboard=True)

def section_inline(section: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("سور", callback_data=f"browse|{section}|surah|0")],
        [InlineKeyboardButton("شيوخ", callback_data=f"browse|{section}|sheikh|0")],
        [InlineKeyboardButton("عشوائي", callback_data=f"browse|{section}|random|0")],
        [InlineKeyboardButton("رجوع", callback_data="back|home")],
    ])

def admin_sections_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("كرومات", callback_data="admin|section|chroma")],
        [InlineKeyboardButton("تصاميم", callback_data="admin|section|designs")],
        [InlineKeyboardButton("مناظر طبيعية", callback_data="admin|section|nature")],
        [InlineKeyboardButton("رجوع", callback_data="back|admin")],
    ])

def admin_type_inline(section: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("سور", callback_data=f"admin|type|{section}|surah")],
        [InlineKeyboardButton("شيوخ", callback_data=f"admin|type|{section}|sheikh")],
        [InlineKeyboardButton("عشوائي", callback_data=f"admin|type|{section}|random")],
        [InlineKeyboardButton("رجوع", callback_data="back|admin_sections")],
    ])

def make_paged_keyboard(items: List[Dict[str, Any]], item_prefix: str, page_prefix: str, page: int, back_cb: str, per_page: int = 9) -> InlineKeyboardMarkup:
    start = page * per_page
    end = start + per_page
    page_items = items[start:end]
    rows = []
    for item in page_items:
        rows.append([InlineKeyboardButton(item["label"], callback_data=f"sel|{item_prefix}|{item['id']}")])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("السابق", callback_data=f"page|{page_prefix}|{page-1}"))
    if end < len(items):
        nav.append(InlineKeyboardButton("التالي", callback_data=f"page|{page_prefix}|{page+1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton("رجوع", callback_data=back_cb)])
    return InlineKeyboardMarkup(rows)

# ---------- item queries ----------

def all_surah_items() -> List[Dict[str, Any]]:
    rows = _fetch("surahs", "id,name")
    return [{"id": r["id"], "label": f"{r['id']}. {r['name']}"} for r in rows]

def all_sheikh_items() -> List[Dict[str, Any]]:
    rows = _fetch("sheikhs", "id,name")
    return [{"id": r["id"], "label": r["name"]} for r in rows]

def available_surah_items(section: str) -> List[Dict[str, Any]]:
    media = _fetch("media", "surah_id", section=section, category="surah")
    ids = sorted({m["surah_id"] for m in media if m.get("surah_id") is not None})
    rows = _fetch("surahs", "id,name")
    lookup = {r["id"]: r["name"] for r in rows}
    return [{"id": sid, "label": f"{sid}. {lookup[sid]}"} for sid in ids if sid in lookup]

def available_sheikh_items(section: str) -> List[Dict[str, Any]]:
    media = _fetch("media", "sheikh_id", section=section, category="sheikh")
    ids = sorted({m["sheikh_id"] for m in media if m.get("sheikh_id") is not None})
    rows = _fetch("sheikhs", "id,name")
    lookup = {r["id"]: r["name"] for r in rows}
    return [{"id": sid, "label": lookup[sid]} for sid in ids if sid in lookup]

def get_media(section: str, category: str, item_id: Optional[int] = None) -> List[Dict[str, Any]]:
    q = sb.table("media").select("file_id,file_kind")
    q = q.eq("section", section).eq("category", category)
    if category == "surah" and item_id is not None:
        q = q.eq("surah_id", item_id)
    elif category == "sheikh" and item_id is not None:
        q = q.eq("sheikh_id", item_id)
    return q.order("id").execute().data or []

def add_media(section: str, category: str, file_id: str, file_kind: str, item_id: Optional[int] = None) -> None:
    payload: Dict[str, Any] = {
        "section": section,
        "category": category,
        "file_id": file_id,
        "file_kind": file_kind,
        "caption": None,
    }
    if category == "surah":
        payload["surah_id"] = item_id
    elif category == "sheikh":
        payload["sheikh_id"] = item_id
    _insert("media", payload)

def delete_sheikh(sheikh_id: int) -> None:
    sb.table("media").delete().eq("sheikh_id", sheikh_id).execute()
    sb.table("sheikhs").delete().eq("id", sheikh_id).execute()

# ---------- sending media ----------

async def send_item_media(message, media_row: Dict[str, Any], caption: Optional[str] = None):
    kind = media_row["file_kind"]
    file_id = media_row["file_id"]
    if kind == "photo":
        await message.reply_photo(file_id, caption=caption)
    elif kind == "video":
        await message.reply_video(file_id, caption=caption)
    elif kind == "document":
        await message.reply_document(file_id, caption=caption)
    else:
        await message.reply_text(caption or "نوع ملف غير مدعوم")

# ---------- commands ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state.pop(update.effective_user.id, None)
    await update.message.reply_text("أهلا بك", reply_markup=main_menu())

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    state[ADMIN_ID] = {"mode": "admin_home"}
    await update.message.reply_text("لوحة التحكم", reply_markup=admin_menu())

# ---------- text router ----------

async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = (update.message.text or "").strip()

    if text == "كرومات":
        await update.message.reply_text("اختر", reply_markup=section_inline("chroma"))
        return
    if text == "تصاميم":
        await update.message.reply_text("اختر", reply_markup=section_inline("designs"))
        return
    if text == "مناظر طبيعية":
        rows = get_media("nature", "nature")
        if not rows:
            await update.message.reply_text("لا يوجد محتوى بعد")
            return
        for row in rows:
            await send_item_media(update.message, row, "مناظر طبيعية")
        return
    if text == "بحث في السور":
        state[uid] = {"mode": "search_surah"}
        await update.message.reply_text("اكتب اسم السورة أو جزء منه")
        return

    s = state.get(uid, {})

    if uid == ADMIN_ID and text == "رجوع":
        state[uid] = {"mode": "admin_home"}
        await update.message.reply_text("لوحة التحكم", reply_markup=admin_menu())
        return

    if uid == ADMIN_ID and text == "إضافة محتوى":
        state[uid] = {"mode": "admin_add_content"}
        await update.message.reply_text("اختر القسم", reply_markup=admin_sections_inline())
        return

    if uid == ADMIN_ID and text == "إضافة شيخ":
        state[uid] = {"mode": "admin_add_sheikh_name"}
        await update.message.reply_text("اكتب اسم الشيخ أو عدة أسماء في سطور منفصلة", reply_markup=ReplyKeyboardRemove())
        return

    if uid == ADMIN_ID and text == "حذف شيخ":
        rows = all_sheikh_items()
        if not rows:
            await update.message.reply_text("لا يوجد شيوخ")
            return
        await update.message.reply_text("اختر الشيخ للحذف", reply_markup=make_paged_keyboard(rows, "delete_sheikh", "delete_sheikh", 0, "back|admin"))
        return

    if uid == ADMIN_ID and text == "إحصائيات":
        media_count = len(_fetch("media", "id"))
        sheikh_count = len(_fetch("sheikhs", "id"))
        surah_count = len(available_surah_items("chroma")) + len(available_surah_items("designs"))
        await update.message.reply_text(
            f"""إحصائيات\nالمحتوى: {media_count}\nالشيوخ: {sheikh_count}\nالسور المستخدمة: {surah_count}"""
        )
        return

    if uid == ADMIN_ID and s.get("mode") == "admin_add_sheikh_name":
        names = [n.strip() for n in re.split(r"[\n,]+", text) if n.strip()]
        added = 0
        for name in names:
            try:
                _insert("sheikhs", {"name": name})
                added += 1
            except Exception:
                pass
        state[uid] = {"mode": "admin_home"}
        await update.message.reply_text(f"تمت الإضافة: {added}", reply_markup=admin_menu())
        return

    if s.get("mode") == "search_surah":
        query = text.lower()
        rows = _fetch("surahs", "id,name")
        available = set(item["id"] for item in available_surah_items("chroma") + available_surah_items("designs"))
        matches = [{"id": r["id"], "label": f"{r['id']}. {r['name']}"} for r in rows if r["id"] in available and query in r["name"].lower()]
        if not matches:
            await update.message.reply_text("لا توجد نتائج")
            return
        await update.message.reply_text("النتائج", reply_markup=make_paged_keyboard(matches, "search_pick", "search_pick", 0, "back|home"))
        return

    if uid == ADMIN_ID and text in {"إنهاء", "رجوع"}:
        state[uid] = {"mode": "admin_home"}
        await update.message.reply_text("لوحة التحكم", reply_markup=admin_menu())
        return

# ---------- upload router ----------

async def on_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != ADMIN_ID:
        return
    s = state.get(uid, {})
    if s.get("mode") not in {"admin_upload", "admin_upload_nature", "admin_upload_random"}:
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

    if not file_id:
        return

    if s["mode"] == "admin_upload_nature":
        add_media("nature", "nature", file_id, file_kind)
    elif s["mode"] == "admin_upload_random":
        add_media(s["section"], "random", file_id, file_kind)
    else:
        add_media(s["section"], s["category"], file_id, file_kind, s.get("item_id"))

    await msg.reply_text("تم الحفظ", reply_markup=upload_menu())

# ---------- callbacks ----------

async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    data = q.data or ""

    if data == "back|home":
        state.pop(uid, None)
        await q.message.reply_text("أهلا بك", reply_markup=main_menu())
        return

    if data == "back|admin":
        state[uid] = {"mode": "admin_home"}
        await q.message.reply_text("لوحة التحكم", reply_markup=admin_menu())
        return

    if data == "back|admin_sections":
        state[uid] = {"mode": "admin_add_content"}
        await q.edit_message_text("اختر القسم", reply_markup=admin_sections_inline())
        return

    if data.startswith("page|"):
        _, view, section, category, page_s = data.split("|")
        page = int(page_s)

        if view == "browse":
            if category == "surah":
                items = available_surah_items(section)
            elif category == "sheikh":
                items = available_sheikh_items(section)
            else:
                items = [{"id": 0, "label": "عشوائي"}] if get_media(section, "random") else []
            if not items:
                await q.edit_message_text("لا يوجد محتوى متاح")
                return
            await q.edit_message_text("اختر", reply_markup=make_paged_keyboard(items, f"sel|browse|{section}|{category}", f"browse|{section}|{category}", page, f"browse|{section}|{category}|0"))
            return

        if view == "adminpick":
            if category == "surah":
                items = all_surah_items()
            elif category == "sheikh":
                items = all_sheikh_items()
            else:
                items = []
            if not items:
                await q.edit_message_text("لا توجد عناصر")
                return
            await q.edit_message_text("اختر", reply_markup=make_paged_keyboard(items, f"sel|admin|{section}|{category}", f"adminpick|{section}|{category}", page, "back|admin_sections"))
            return

        if view == "delete_sheikh":
            items = all_sheikh_items()
            if not items:
                await q.edit_message_text("لا يوجد شيوخ")
                return
            await q.edit_message_text("اختر الشيخ للحذف", reply_markup=make_paged_keyboard(items, "delete_sheikh", "delete_sheikh", page, "back|admin"))
            return

        if view == "search_pick":
            # search uses available surahs only; same as browse selection
            items = [{"id": sid, "label": f"{sid}. {name}"} for name, sid in SURAH_LIST]
            await q.edit_message_text("اختر", reply_markup=make_paged_keyboard(items, "search_pick", "search_pick", page, "back|home"))
            return

    if data.startswith("browse|"):
        _, section, category, page_s = data.split("|")
        page = int(page_s)
        if category == "surah":
            items = available_surah_items(section)
        elif category == "sheikh":
            items = available_sheikh_items(section)
        else:
            items = [{"id": 0, "label": "عشوائي"}] if get_media(section, "random") else []
        if not items:
            await q.edit_message_text("لا يوجد محتوى متاح")
            return
        await q.edit_message_text("اختر", reply_markup=make_paged_keyboard(items, f"sel|browse|{section}|{category}", f"browse|{section}|{category}", page, f"back|home"))
        return

    if data.startswith("admin|section|"):
        section = data.split("|")[-1]
        s = state.setdefault(uid, {})
        s["mode"] = "admin_add_content"
        s["section"] = section
        if section == "nature":
            s["mode"] = "admin_upload_nature"
            await q.edit_message_text("أرسل الملفات الآن", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="back|admin")]]))
            return
        await q.edit_message_text("اختر النوع", reply_markup=admin_type_inline(section))
        return

    if data.startswith("admin|type|"):
        _, _, section, category = data.split("|")
        s = state.setdefault(uid, {})
        s["section"] = section
        s["category"] = category
        if category == "random":
            s["mode"] = "admin_upload_random"
            await q.edit_message_text("أرسل الملفات الآن", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="back|admin_sections")]]))
            return

        s["mode"] = "admin_pick_item"
        if category == "surah":
            items = all_surah_items()
        else:
            items = all_sheikh_items()
        if not items:
            if category == "sheikh":
                await q.edit_message_text("لا يوجد شيوخ. أضف شيخًا أولًا", reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("إضافة شيخ جديد", callback_data="admin|add_sheikh_new")],
                    [InlineKeyboardButton("رجوع", callback_data="back|admin_sections")],
                ]))
                return
            await q.edit_message_text("لا توجد عناصر")
            return
        await q.edit_message_text("اختر", reply_markup=make_paged_keyboard(items, f"sel|admin|{section}|{category}", f"adminpick|{section}|{category}", 0, "back|admin_sections"))
        return

    if data == "admin|add_sheikh_new":
        state[uid] = {"mode": "admin_add_sheikh_name"}
        await q.message.reply_text("اكتب اسم الشيخ أو عدة أسماء في سطور منفصلة", reply_markup=ReplyKeyboardRemove())
        return

    if data.startswith("sel|"):
        _, target, section, category, item_id_s = data.split("|")
        item_id = int(item_id_s)

        if target == "browse":
            media = get_media(section, category, item_id if item_id else None)
            if not media:
                await q.edit_message_text("لا يوجد محتوى")
                return
            if category == "surah":
                name = _fetch_one("surahs", "name", id=item_id)["name"]
            elif category == "sheikh":
                name = _fetch_one("sheikhs", "name", id=item_id)["name"]
            else:
                name = "عشوائي"
            await q.edit_message_text(f"المحتوى: {name}")
            for row in media:
                await send_item_media(q.message, row, name)
            return

        if target == "admin":
            s = state.setdefault(uid, {})
            s["mode"] = "admin_upload"
            s["section"] = section
            s["category"] = category
            s["item_id"] = item_id
            label = ""
            if category == "surah":
                label = (_fetch_one("surahs", "name", id=item_id) or {}).get("name", "")
            else:
                label = (_fetch_one("sheikhs", "name", id=item_id) or {}).get("name", "")
            await q.edit_message_text(f"أرسل الوسائط الآن لـ {label}", reply_markup=upload_menu())
            return

    if data.startswith("delete_sheikh"):
        # callback structure: delete_sheikh:<id> OR page|delete_sheikh|... handled above
        parts = data.split(":")
        if len(parts) == 2:
            sheikh_id = int(parts[1])
            delete_sheikh(sheikh_id)
            state[uid] = {"mode": "admin_home"}
            await q.message.reply_text("تم الحذف", reply_markup=admin_menu())
            return

def register(app: Application):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL, on_media))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

def main():
    seed_surahs_if_needed()
    app = Application.builder().token(BOT_TOKEN).build()
    register(app)
    app.run_polling()

if __name__ == "__main__":
    main()
