# Reply Keyboard Bot

كل التنقل في هذا الإصدار عبر Reply Keyboard فقط.
لا يوجد Inline Keyboard نهائيًا.

## التشغيل
1. أنشئ مشروع Supabase
2. شغّل `supabase_schema.sql`
3. انسخ `.env.example` إلى `.env`
4. ثبت الحزم:
   pip install -r requirements.txt
5. شغّل:
   python bot.py

## المميزات
- Main menu كامل Reply Keyboard
- Admin menu كامل Reply Keyboard
- بحث في السور
- إضافة شيوخ
- حذف شيوخ
- عرض المحتوى المتاح فقط
- ترتيب السور حسب رقمها
- تخزين دائم في Supabase عبر REST

## ملاحظة
هذا الإصدار يزيل كل Inline Keyboard ويستبدلها بتفاعل نصّي عبر Reply Keyboard.
