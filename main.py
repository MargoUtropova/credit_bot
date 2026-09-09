import asyncio
import logging

from aiogram import Bot, Dispatcher
from config.config import Config, load_config
from handlers import user, other
from keyboards.set_menu import set_main_menu
from services.notifications import payment_reminder

# функция конфигурирования и запуска бота
async def main() -> None:
    # загружаем конфиг в переменную
    config: Config = load_config()

    # задаем базовую конфигурацию логирования
    logging.basicConfig(
        # level=logging.getLevelName(level=config.log.level), # .getLevelName deprecated
        # level=config.log.level,
        level=logging.WARNING,
        format=config.log.format,
    )
    # Инициализируем бот и диспетчер
    bot = Bot(token=config.bot.token)
    asyncio.create_task(
    payment_reminder(bot)
        )
    dp = Dispatcher()

    # Регистриуем роутеры в диспетчере
    dp.include_router(user.router)
    dp.include_router(other.router)

    # регистируем главное меню
    dp.startup.register(set_main_menu)

     # Пропускаем накопившиеся апдейты и запускаем polling
    await bot.delete_webhook(drop_pending_updates=True)

    await dp.start_polling(bot)


asyncio.run(main())
