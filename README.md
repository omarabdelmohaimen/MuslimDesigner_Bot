# Quran Media Bot (Supabase REST)

## المميزات
- بدون مكتبة supabase Python
- تخزين دائم عبر Supabase
- `/admin` للأدمن فقط
- بحث في السور
- إضافة شيوخ وحذفهم
- المحتوى المعروض للمستخدم يكون فقط الموجود فعلًا

## التشغيل
1. أنشئ مشروع Supabase
2. افتح SQL Editor وشغّل `supabase_schema.sql`
3. انسخ `.env.example` إلى `.env`
4. املأ القيم:
   - BOT_TOKEN
   - ADMIN_ID
   - SUPABASE_URL
   - SUPABASE_SERVICE_ROLE_KEY
5. ثبّت المتطلبات:
   `pip install -r requirements.txt`
6. شغّل:
   `python bot.py`

## ملاحظة
- استخدم Python 3.11
- المخزن هنا خفيف لأننا نحفظ file_id فقط
