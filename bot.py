import os
import re
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

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

def headers() -> Dict[str, str]:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

def api_request(method: str, table: str, params: Optional[Dict[str, str]] = None, json_body: Any = None, return_rep: bool = False):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    h = headers()
    if return_rep:
        h["Prefer"] = "return=representation"
    resp = requests.request(method, url, headers=h, params=params, json=json_body, timeout=30)
    resp.raise_for_status()
    if resp.text.strip():
        return resp.json()
    return None

def select_rows(table: str, columns: str = "*", filters: Optional[List[tuple]] = None, order: Optional[str] = None, limit: Optional[int] = None):
    params: Dict[str, str] = {"select": columns}
    if filters:
        for col, op, value in filters:
            params[col] = f"{op}.{value}"
    if order:
        params["order"] = order
    if limit is not None:
        params["limit"] = str(limit)
    return api_request("GET", table, params=params) or []

def insert_rows(table: str, payload: Any):
    return api_request("POST", table, json_body=payload)

def delete_rows(table: str, filters: List[tuple]):
    params: Dict[str, str] = {}
    for col, op, value in filters:
        params[col] = f"{op}.{value}"
    return api_request("DELETE", table, params=params)

def seed_surahs_if_needed():
    if select_rows("surahs", "id", limit=1):
        return
    insert_rows("surahs", [{"id": sid, "name": name} for name, sid in SURAH_LIST])

def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([["كرومات", "تصاميم"], ["مناظر طبيعية", "بحث في السور"]], resize_keyboard=True, input_field_placeholder="اختر من القائمة")

def admin_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([["إضافة محتوى", "إضافة شيخ"], ["حذف شيخ", "إحصائيات"], ["رجوع"]], resize_keyboard=True)

def upload_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([["إنهاء"], ["رجوع"]], resize_keyboard=True)

def inline_sections() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("كرومات", callback_data="admin_section|chroma")],
        [InlineKeyboardButton("تصاميم", callback_data="admin_section|designs")],
        [InlineKeyboardButton("مناظر طبيعية", callback_data="admin_section|nature")],
        [InlineKeyboardButton("رجوع", callback_data="back_admin")],
    ])

def inline_types(section: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("سور", callback_data=f"admin_type|{section}|surah")],
        [InlineKeyboardButton("شيوخ", callback_data=f"admin_type|{section}|sheikh")],
        [InlineKeyboardButton("عشوائي", callback_data=f"admin_type|{section}|random")],
        [InlineKeyboardButton("رجوع", callback_data="back_admin_sections")],
    ])

def paginated_kb(items: List[Dict[str, Any]], cb_prefix: str, page: int, back_cb: str, per_page: int = 9) -> InlineKeyboardMarkup:
    start = page * per_page
    end = start + per_page
    rows = []
    for item in items[start:end]:
        rows.append([InlineKeyboardButton(item["label"], callback_data=f"{cb_prefix}|{item['id']}")])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("السابق", callback_data=f"{cb_prefix}_page|{page-1}"))
    if end < len(items):
        nav.append(InlineKeyboardButton("التالي", callback_data=f"{cb_prefix}_page|{page+1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton("رجوع", callback_data=back_cb)])
    return InlineKeyboardMarkup(rows)

def all_surahs() -> List[Dict[str, Any]]:
    return [{"id": r["id"], "label": f"{r['id']}. {r['name']}"} for r in select_rows("surahs", "id,name", order="id.asc")]

def all_sheikhs() -> List[Dict[str, Any]]:
    return [{"id": r["id"], "label": r["name"]} for r in select_rows("sheikhs", "id,name", order="name.asc")]

def available_surahs(section: str) -> List[Dict[str, Any]]:
    media = select_rows("media", "surah_id", filters=[("section", "eq", section), ("category", "eq", "surah")], order="surah_id.asc")
    ids = sorted({r["surah_id"] for r in media if r.get("surah_id") is not None})
    lookup = {r["id"]: r["name"] for r in select_rows("surahs", "id,name", order="id.asc")}
    return [{"id": sid, "label": f"{sid}. {lookup[sid]}"} for sid in ids if sid in lookup]

def available_sheikhs(section: str) -> List[Dict[str, Any]]:
    media = select_rows("media", "sheikh_id", filters=[("section", "eq", section), ("category", "eq", "sheikh")], order="sheikh_id.asc")
    ids = sorted({r["sheikh_id"] for r in media if r.get("sheikh_id") is not None})
    lookup = {r["id"]: r["name"] for r in select_rows("sheikhs", "id,name", order="name.asc")}
    return [{"id": sid, "label": lookup[sid]} for sid in ids if sid in lookup]

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state.pop(update.effective_user.id, None)
    await update.message.reply_text("أهلا بك", reply_markup=main_menu())

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    state[ADMIN_ID] = {"mode": "admin_home"}
    await update.message.reply_text("لوحة التحكم", reply_markup=admin_menu())

async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = (update.message.text or "").strip()
    s = state.get(uid, {})

    if text == "كرومات":
        await update.message.reply_text("اختر", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("سور", callback_data="browse|chroma|surah|0")],
            [InlineKeyboardButton("شيوخ", callback_data="browse|chroma|sheikh|0")],
            [InlineKeyboardButton("عشوائي", callback_data="browse|chroma|random|0")],
            [InlineKeyboardButton("رجوع", callback_data="back_home")],
        ]))
        return

    if text == "تصاميم":
        await update.message.reply_text("اختر", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("سور", callback_data="browse|designs|surah|0")],
            [InlineKeyboardButton("شيوخ", callback_data="browse|designs|sheikh|0")],
            [InlineKeyboardButton("عشوائي", callback_data="browse|designs|random|0")],
            [InlineKeyboardButton("رجوع", callback_data="back_home")],
        ]))
        return

    if text == "مناظر طبيعية":
        rows = select_rows("media", "file_id,file_kind", filters=[("section", "eq", "nature"), ("category", "eq", "nature")], order="id.asc")
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

    if uid == ADMIN_ID and text == "رجوع":
        state[uid] = {"mode": "admin_home"}
        await update.message.reply_text("لوحة التحكم", reply_markup=admin_menu())
        return

    if uid == ADMIN_ID and text == "إضافة محتوى":
        state[uid] = {"mode": "pick_section"}
        await update.message.reply_text("اختر القسم", reply_markup=inline_sections())
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
        await update.message.reply_text("اختر الشيخ للحذف", reply_markup=paginated_kb(rows, "delete_sheikh", 0, "back_admin"))
        return

    if uid == ADMIN_ID and text == "إحصائيات":
        await update.message.reply_text(f"إحصائيات\nالمحتوى: {len(select_rows('media', 'id'))}\nالشيوخ: {len(select_rows('sheikhs', 'id'))}")
        return

    if uid == ADMIN_ID and s.get("mode") == "add_sheikh":
        names = [n.strip() for n in re.split(r"[\n,]+", text) if n.strip()]
        existing = {r["name"] for r in select_rows("sheikhs", "name", order="name.asc")}
        added = 0
        for name in names:
            if name in existing:
                continue
            try:
                insert_rows("sheikhs", {"name": name})
                added += 1
            except Exception:
                pass
        state[uid] = {"mode": "admin_home"}
        await update.message.reply_text(f"تمت الإضافة: {added}", reply_markup=admin_menu())
        return

    if s.get("mode") == "search_surah":
        query = text.lower()
        used_ids = {r["surah_id"] for r in select_rows("media", "surah_id", filters=[("category", "eq", "surah")]) if r.get("surah_id") is not None}
        matches = [{"id": sid, "label": f"{sid}. {name}"} for name, sid in SURAH_LIST if sid in used_ids and query in name.lower()]
        if not matches:
            await update.message.reply_text("لا توجد نتائج")
        else:
            await update.message.reply_text("النتائج", reply_markup=paginated_kb(matches, "pick_search_surah", 0, "back_home"))
        return

    if uid == ADMIN_ID and text in {"إنهاء", "رجوع"} and s.get("mode", "").startswith("upload"):
        state[uid] = {"mode": "admin_home"}
        await update.message.reply_text("لوحة التحكم", reply_markup=admin_menu())
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
        file_id, file_kind = msg.photo[-1].file_id, "photo"
    elif msg.video:
        file_id, file_kind = msg.video.file_id, "video"
    elif msg.document:
        file_id, file_kind = msg.document.file_id, "document"
    else:
        return

    if s["mode"] == "upload_nature":
        add_media("nature", "nature", file_id, file_kind)
    elif s["mode"] == "upload_random":
        add_media(s["section"], "random", file_id, file_kind)
    else:
        add_media(s["section"], s["category"], file_id, file_kind, s.get("item_id"))

    await msg.reply_text("تم الحفظ", reply_markup=upload_menu())

async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    data = q.data or ""

    if data == "back_home":
        state.pop(uid, None)
        await q.message.reply_text("أهلا بك", reply_markup=main_menu())
        return

    if data == "back_admin":
        state[uid] = {"mode": "admin_home"}
        await q.message.reply_text("لوحة التحكم", reply_markup=admin_menu())
        return

    if data == "back_admin_sections":
        state[uid] = {"mode": "pick_section"}
        await q.edit_message_text("اختر القسم", reply_markup=inline_sections())
        return

    if data == "add_new_sheikh":
        state[uid] = {"mode": "add_sheikh"}
        await q.message.reply_text("اكتب اسم الشيخ أو عدة أسماء في سطور منفصلة", reply_markup=ReplyKeyboardRemove())
        return

    if data.startswith("admin_section|"):
        section = data.split("|", 1)[1]
        state[uid] = {"mode": "pick_type", "section": section}
        if section == "nature":
            state[uid]["mode"] = "upload_nature"
            await q.edit_message_text("أرسل الملفات الآن", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="back_admin")]]))
        else:
            await q.edit_message_text("اختر النوع", reply_markup=inline_types(section))
        return

    if data.startswith("admin_type|"):
        _, section, category = data.split("|")
        s = state.setdefault(uid, {})
        s["section"] = section
        s["category"] = category
        if category == "random":
            s["mode"] = "upload_random"
            await q.edit_message_text("أرسل الملفات الآن", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="back_admin_sections")]]))
            return
        items = all_surahs() if category == "surah" else all_sheikhs()
        if category == "sheikh" and not items:
            await q.edit_message_text("لا يوجد شيوخ. أضف شيخًا أولًا", reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("إضافة شيخ جديد", callback_data="add_new_sheikh")],
                [InlineKeyboardButton("رجوع", callback_data="back_admin_sections")],
            ]))
            return
        await q.edit_message_text("اختر", reply_markup=paginated_kb(items, f"admin_pick|{section}|{category}", 0, "back_admin_sections"))
        return

    if data.startswith("admin_pick|"):
        _, section, category, item_id = data.split("|")
        item_id = int(item_id)
        s = state.setdefault(uid, {})
        s["mode"] = "upload"
        s["section"] = section
        s["category"] = category
        s["item_id"] = item_id

        label = ""
        if category == "surah":
            row = select_rows("surahs", "name", filters=[("id", "eq", item_id)], limit=1)
            label = row[0]["name"] if row else ""
        else:
            row = select_rows("sheikhs", "name", filters=[("id", "eq", item_id)], limit=1)
            label = row[0]["name"] if row else ""
        await q.edit_message_text(f"أرسل الوسائط الآن لـ {label}", reply_markup=upload_menu())
        return

    if data.startswith("browse|"):
        _, section, category, _page = data.split("|")
        if category == "surah":
            items = available_surahs(section)
        elif category == "sheikh":
            items = available_sheikhs(section)
        else:
            rows = get_media(section, "random")
            if not rows:
                await q.edit_message_text("لا يوجد محتوى متاح")
                return
            await q.edit_message_text("المحتوى العشوائي")
            for row in rows:
                await send_media(q.message, row, "عشوائي")
            return
        if not items:
            await q.edit_message_text("لا يوجد محتوى متاح")
            return
        await q.edit_message_text("اختر", reply_markup=paginated_kb(items, f"pick|{section}|{category}", 0, "back_home"))
        return

    if data.startswith("pick_search_surah"):
        parts = data.split("|")
        if len(parts) == 2:
            sid = int(parts[1])
            rows = get_media("chroma", "surah", sid) + get_media("designs", "surah", sid)
            if not rows:
                await q.edit_message_text("لا يوجد محتوى")
                return
            name = next((n for n, i in SURAH_LIST if i == sid), "سورة")
            await q.edit_message_text(f"المحتوى: {name}")
            for row in rows:
                await send_media(q.message, row, name)
        return

    if data.startswith("pick|"):
        _, section, category, item_id = data.split("|")
        item_id = int(item_id)
        media = get_media(section, category, item_id if item_id else None)
        if not media:
            await q.edit_message_text("لا يوجد محتوى")
            return
        if category == "surah":
            row = select_rows("surahs", "name", filters=[("id", "eq", item_id)], limit=1)
            label = row[0]["name"] if row else "سورة"
        elif category == "sheikh":
            row = select_rows("sheikhs", "name", filters=[("id", "eq", item_id)], limit=1)
            label = row[0]["name"] if row else "شيخ"
        else:
            label = "عشوائي"
        await q.edit_message_text(f"المحتوى: {label}")
        for row in media:
            await send_media(q.message, row, label)
        return

    if data.startswith("delete_sheikh_page|"):
        page = int(data.split("|")[1])
        rows = all_sheikhs()
        await q.edit_message_text("اختر الشيخ للحذف", reply_markup=paginated_kb(rows, "delete_sheikh", page, "back_admin"))
        return

    if data.startswith("delete_sheikh|"):
        sid = int(data.split("|")[1])
        delete_sheikh(sid)
        state[uid] = {"mode": "admin_home"}
        await q.message.reply_text("تم الحذف", reply_markup=admin_menu())
        return

async def main():
    seed_surahs_if_needed()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL, on_media))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.run_polling()

if __name__ == "__main__":
    main()
