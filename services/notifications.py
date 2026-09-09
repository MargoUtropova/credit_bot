import asyncio
from datetime import datetime, timedelta

from aiogram import Bot

from funcs.funcs import get_payments_for_reminder, get_users
from keyboards.keyboards import get_paid_keyboard

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
            f"Оплатить до: <b>{payment['pay_until']}</b>"
        )

        await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=get_paid_keyboard(payment['card_name']),
            parse_mode="HTML"
        )


async def payment_reminder(bot: Bot):
    """Проверяет платежи пользователей каждый день в 10:00.
    Если бот запущен после 10:00, проверка выполняется сразу.
    """
    while True:
        now = datetime.now()

        if now.hour >= 10:
            users = get_users()

            for user in users:
                chat_id = user["telegram_chat_id"]

                await send_payment_reminders(
                    bot,
                    chat_id
                )

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