"""
/start command handler — shows the main menu.
"""
from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery

from bot.database import db
from bot.keyboards import UserKeyboards
from bot.config import config

router = Router()

WELCOME_TEXT = (
    "🕌 <b>أهلاً وسهلاً في بوت القرآن الكريم</b> 🕌\n\n"
    "يمكنك تصفح وتحميل ملفات القرآن الكريم المتنوعة.\n"
    "اختر تصنيفاً من القائمة أدناه للبدء:"
)


async def send_main_menu(target, text: str = WELCOME_TEXT):
    """Send the main menu to a message or callback."""
    categories = await db.get_categories()
    kb = UserKeyboards.main_menu(categories)

    if isinstance(target, Message):
        await target.answer(text, reply_markup=kb, parse_mode="HTML")
    elif isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await target.answer()


@router.message(CommandStart())
async def cmd_start(message: Message):
    await send_main_menu(message)


@router.message(Command("menu"))
async def cmd_menu(message: Message):
    await send_main_menu(message)


@router.callback_query(F.data == "home")
async def cb_home(callback: CallbackQuery):
    await send_main_menu(callback)


@router.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "📖 <b>مساعدة - بوت القرآن الكريم</b>\n\n"
        "الأوامر المتاحة:\n"
        "/start — الصفحة الرئيسية\n"
        "/menu  — القائمة الرئيسية\n"
        "/help  — هذه الرسالة\n\n"
        "التنقل عبر القائمة:\n"
        "• اضغط على أي زر للدخول إلى التصنيف\n"
        "• استخدم زر 🔙 للعودة للخلف\n"
        "• استخدم زر 🏠 للعودة للقائمة الرئيسية\n"
        "• اضغط على الملف لمعاينته\n"
        "• اضغط ⬇️ تحميل لتنزيل الملف\n\n"
        "📌 المحتوى مقسم إلى ثلاثة أقسام:\n"
        "🎬 كروما — خلفيات الكروما القرآنية\n"
        "🎨 تصاميم — التصاميم القرآنية\n"
        "🌿 مناظر طبيعية — خلفيات طبيعية\n"
    )
    await message.answer(text, parse_mode="HTML")
