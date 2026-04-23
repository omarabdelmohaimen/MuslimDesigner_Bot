# Quran Media Bot + Supabase

## الفكرة
البوت يخزن البيانات في Supabase Postgres، ويخزن file_id فقط للوسائط بدل رفع الملفات إلى تخزين خارجي.

## لماذا هذا مناسب؟
- Telegram file_ids can be treated as persistent.
- Supabase Free plan currently includes 500 MB database size quota and 1 GB storage quota.
- If you stay within quota, no extra charge applies.

## التشغيل
1. أنشئ مشروع Supabase.
2. افتح SQL Editor وشغّل `supabase_schema.sql`.
3. أنشئ بوت من BotFather.
4. انسخ `.env.example` إلى `.env` واملأ القيم.
5. ثبّت الحزم:
   `pip install -r requirements.txt`
6. شغّل:
   `python bot.py`

## ملاحظات مهمة
- استخدم Python 3.11.
- /admin يظهر فقط للأدمن.
- المحتوى لا يضيع بعد إعادة النشر لأن التخزين في Supabase.
