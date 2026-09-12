
import asyncio
from datetime import datetime, timedelta

from aiogram import Bot

from funcs.data import (
    get_payments_for_reminder,
    get_users,
)
from keyboards.keyboards import get_paid_keyboard



# ============================================================================
# Отправка напоминаний одному пользователю
# ============================================================================

async def send_payment_reminders(
    bot: Bot,
    chat_id: int,
    reminders: list[dict],
) -> None:
    """
    Отправляет одному пользователю напоминания
    по всем картам.
    """

    for payment in reminders:
        await bot.send_message(
            chat_id=chat_id,
            text=payment["text"],
            reply_markup=get_paid_keyboard(
                payment["card_name"]
            ),
            parse_mode="HTML",
        )

# ============================================================================
# Ежедневная проверка платежей
# ============================================================================

async def payment_reminder(
    bot: Bot,
) -> None:
    """
    payment_reminder()
        ├── get_users() → список пользователей
        ├── get_payments_for_reminder() → общий список уведомлений
        └── async def send_payment_reminders → отправляет каждый текст каждому пользователю

    Запускает постоянный цикл ежедневной проверки платежей.

    Проверка выполняется каждый день в 10:00.
    Если бот запущен после 10:00, первая проверка выполняется сразу.
    """

    while True:
        now = datetime.now()

        if now.hour >= 10:
            users = get_users()
            reminders = get_payments_for_reminder()
            # отправляет уведомления каждому польз-лю из списка
            for chat_id in users:
                await send_payment_reminders(
                    bot=bot,
                    chat_id=chat_id,
                    reminders=reminders,
                )

            next_run = (
                now + timedelta(days=1)
            ).replace(
                hour=10,
                minute=0,
                second=0,
                microsecond=0,
            )

        else:
            next_run = now.replace(
                hour=10,
                minute=0,
                second=0,
                microsecond=0,
            )

        seconds_until_run = (
            next_run - now
        ).total_seconds()

        await asyncio.sleep(seconds_until_run)