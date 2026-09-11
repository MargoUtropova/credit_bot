import asyncio
import logging

from aiogram import Bot, Dispatcher

from config.config import Config, load_config
from handlers import other, user
from keyboards.set_menu import set_main_menu
from services.notifications import payment_reminder


async def main() -> None:
    """Основная функция запуска Telegram-бота."""

    # Загружаем конфигурацию.
    config: Config = load_config()

    # Настраиваем логирование.
    # Уровень берётся из конфигурационного файла.
    log_level = getattr(
        logging,
        config.log.level.upper(),
        logging.WARNING,
    )

    logging.basicConfig(
        level=log_level,
        format=config.log.format,
    )

    # Создаём объект бота и диспетчер.
    async with Bot(token=config.bot.token) as bot:
        dp = Dispatcher()

        # Регистрируем роутеры обработчиков.
        dp.include_router(user.router)
        dp.include_router(other.router)

        # Устанавливаем команды главного меню при запуске бота.
        dp.startup.register(set_main_menu)

        # Запускаем фоновую задачу для ежедневной проверки платежей.
        reminder_task = asyncio.create_task(
            payment_reminder(bot)
        )

        try:
            # Удаляем webhook и пропускаем накопившиеся обновления.
            await bot.delete_webhook(drop_pending_updates=True)

            # Запускаем получение новых обновлений через polling.
            await dp.start_polling(bot)

        finally:
            # После остановки polling корректно завершаем
            # бесконечную фоновую задачу напоминаний.
            reminder_task.cancel()

            try:
                await reminder_task
            except asyncio.CancelledError:
                pass


if __name__ == "__main__":
    asyncio.run(main())
