from aiogram import Router, types
from aiogram.filters import Command
from keyboards.inline import main_menu
from database.engine import async_session
from database.models import User
router = Router()
@router.message(Command('start'))
async def cmd_start(m: types.Message):
    async with async_session() as s:
        if not await s.get(User, m.from_user.id):
            s.add(User(id=m.from_user.id, username=m.from_user.username))
            await s.commit()
    await m.answer('مرحباً بك في بوت محتوى القرآن الكريم 🌙', reply_markup=main_menu())