
import asyncio
from datetime import datetime, timedelta

from aiogram import Bot

from funcs.funcs import (
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
) -> None:
    """
    Отправляет пользователю напоминания о ближайших платежах.

    Получает список платежей через функцию
    get_payments_for_reminder().

    Для каждого подходящего платежа отправляется отдельное
    сообщение с информацией:

        - карта;
        - сумма минимального платежа;
        - дата, до которой необходимо оплатить.

    К сообщению прикрепляется клавиатура с кнопками:

        «Оплачено»
        «Изменить»
        «Назад в меню»

    Кнопка «Оплачено» позволяет сразу отметить карту
    оплаченной без запуска FSM.

    Параметры:
        bot:
            Объект Telegram-бота.

        chat_id:
            Telegram ID пользователя.

    Возвращает:
        None.
    """
    reminders = get_payments_for_reminder(
        chat_id
    )

    for payment in reminders:

        text = (
            "⚠️ Напоминание о платеже\n\n"
            f"Карта: {payment['card_name']}\n"
            f"Сумма платежа: "
            f"{payment['min_pay']} руб.\n"
            f"Оплатить до: "
            f"<b>{payment['pay_until']}</b>"
        )

        await bot.send_message(
            chat_id=chat_id,
            text=text,
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
    Запускает постоянный цикл ежедневной проверки платежей.

    Проверка выполняется каждый день в 10:00.

    Если бот был запущен:
        - до 10:00 — первая проверка произойдёт в 10:00;
        - после 10:00 — первая проверка выполняется сразу.

    После проверки следующая проверка назначается
    на 10:00 следующего дня.

    Для каждого зарегистрированного пользователя
    вызывается send_payment_reminders().

    Функция предназначена для запуска как отдельная
    asyncio-задача при старте бота.

    Например:

        asyncio.create_task(
            payment_reminder(bot)
        )

    Параметры:
        bot:
            Объект Telegram-бота.

    Функция работает бесконечно, пока не будет отменена
    или пока не завершится работа приложения.
    """
    while True:
        now = datetime.now()

        # ------------------------------------------------------------------
        # Определяем время следующей проверки.
        # ------------------------------------------------------------------

        if now.hour >= 10:
            # Если сейчас уже 10:00 или позже,
            # сегодняшняя проверка выполняется сразу.
            users = get_users()

            for user in users:
                chat_id = user["telegram_chat_id"]

                await send_payment_reminders(
                    bot=bot,
                    chat_id=chat_id,
                )

            # Следующая проверка — завтра в 10:00.
            next_run = (
                now + timedelta(days=1)
            ).replace(
                hour=10,
                minute=0,
                second=0,
                microsecond=0,
            )

        else:
            # Если бот запущен до 10:00,
            # ждём сегодняшних 10:00.
            next_run = now.replace(
                hour=10,
                minute=0,
                second=0,
                microsecond=0,
            )

        # ------------------------------------------------------------------
        # Засыпаем до следующей проверки.
        # ------------------------------------------------------------------

        seconds_until_run = (
            next_run - now
        ).total_seconds()

        await asyncio.sleep(
            seconds_until_run
        )
