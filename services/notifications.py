import asyncio
from datetime import datetime, timedelta

from aiogram import Bot

from funcs.funcs import get_payments_for_reminder


async def send_payment_reminders(bot: Bot, chat_id: int):
    """Принимает объект бота и ID чата.
    Получает список ближайших платежей и отправляет по ним уведомления.
    Ничего не возвращает.
    """
    reminders = get_payments_for_reminder(chat_id)

    for payment in reminders:

        text = (
            "⚠️ Напоминание о платеже\n\n"
            f"Карта: {payment['card_name']}\n"
            f"Сумма платежа: {payment['min_pay']} руб.\n"
            f"Оплатить до: {payment['pay_until']}"
        )

        await bot.send_message(
            chat_id=chat_id,
            text=text
        )


async def payment_reminder(bot: Bot, chat_id: int):
    """Принимает объект бота и ID чата.
    Запускает цикл проверки платежей: проверяет сразу после запуска,
    если сейчас после 10:00, и затем каждый день в 10:00.
    Ничего не возвращает.
    """
    while True:

        now = datetime.now()

        if now.hour >= 10:
            await send_payment_reminders(bot, chat_id)

            next_run = (now + timedelta(days=1)).replace(
                hour=10,
                minute=0,
                second=0,
                microsecond=0
            )

        else:
            next_run = now.replace(
                hour=10,
                minute=0,
                second=0,
                microsecond=0
            )

        seconds_until_run = (next_run - now).total_seconds()

        await asyncio.sleep(seconds_until_run)