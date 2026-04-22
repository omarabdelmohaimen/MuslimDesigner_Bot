import asyncio
from aiogram import Bot, Dispatcher
import config
from database.engine import init_db
from handlers import common, user, admin
async def main():
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher()
    await init_db()
    dp.include_router(common.router)
    dp.include_router(admin.router)
    dp.include_router(user.router)
    await dp.start_polling(bot)
if __name__ == '__main__': asyncio.run(main())