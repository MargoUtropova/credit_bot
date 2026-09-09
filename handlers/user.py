from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from lexicon.lexicon import LEXICON_RU
from keyboards.keyboards import menu_keyboard, get_cards_keyboard, get_paid_keyboard, back_button
from funcs.funcs import get_upcoming_payments, get_detailed_card_info, total_debt, mark_card_as_paid

router = Router()

@router.message(CommandStart()) # сюда вставить запись chat_id при запуске бота
async def process_start(message: Message):
    """При старте предлагаем главное меню."""
    chat_id = message.chat.id
    nickname = message.from_user.username
    # здесь реализовать запись chat_id и nickname в users.csv
    await message.answer(
        text=LEXICON_RU['start'],
        reply_markup=menu_keyboard
    )
# ------------ handler для команды меню от старта до возврата в меню
@router.message(Command("menu"))
@router.message(F.text.strip() == "Назад в меню")
async def menu_handler(message: Message): # меню для всех одинаковое
    await message.answer(
        "Выберите нужное действие:",
        reply_markup=menu_keyboard
    )

@router.callback_query(F.data == "menu") # меню для всех одинаковое
async def process_menu_callback(callback: CallbackQuery):
    await callback.message.answer(
        "Выберите нужное действие:",
                reply_markup=menu_keyboard
            )
    # Убираем "крутилку" с кнопки
    await callback.answer()

# --------- handler для проверки ближайших платежей--------

@router.message(Command("check_payments"))
async def process_payments(message:Message):
    chat_id = message.chat.id
    report = get_upcoming_payments(chat_id)
    await message.answer(text=report)

@router.callback_query(F.data == "check_payments")
async def process_payments_callback(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    report = get_upcoming_payments(chat_id)

    await callback.message.answer(
        text=report,
        reply_markup=back_button
    )
    # Убираем "крутилку" с кнопки
    await callback.answer()

# ---------  handler для вывода и выбора списка карт ----------
@router.message(Command("cards"))
@router.callback_query(F.data == "cards")
async def process_cards(event: Message | CallbackQuery):

    if isinstance(event, Message):
        chat_id = event.chat.id
        await event.answer(
            text="Выберите карту из списка ниже:",
            reply_markup=get_cards_keyboard(chat_id)
        )

    elif isinstance(event, CallbackQuery):
        chat_id = event.message.chat.id
        await event.message.answer(
            text="Выберите карту из списка ниже:",
            reply_markup=get_cards_keyboard(chat_id)
        )
        await event.answer()

# ---------  handler при выборе конкретной карты-----
@router.callback_query(F.data.startswith("card:"))
async def process_card_detail(callback: CallbackQuery):

    card_name = callback.data.split(":", 1)[1]
    chat_id = callback.message.chat.id
    report = get_detailed_card_info(chat_id,card_name)

    await callback.message.answer(
        text=report,
        reply_markup=get_paid_keyboard(card_name),
        # parse_mode="Markdown"
    )

    await callback.answer()

# ---------  handler при вызове общего долга
@router.message(Command("total_debt"))
@router.callback_query(F.data == "total_debt")
async def get_total_debt(event: Message | CallbackQuery):
    """ возвращает общий долг по всем картам пользователя"""
    if isinstance(event, Message):
        chat_id = event.chat.id
        report = total_debt(chat_id)
        await event.answer(text=report, reply_markup=back_button)

    elif isinstance(event, CallbackQuery):
        chat_id = event.message.chat.id
        report = total_debt(chat_id)
        await event.message.answer(text=report, reply_markup=back_button)
        await event.answer()

# ---------- handler чтобы пометить карту как оплаченную
# text="Оплачено",
# callback_data="paid"
@router.callback_query(F.data.startswith("paid:"))
async def process_paid(callback: CallbackQuery):
    """помечает карту как оплаченную"""
    card_name = callback.data.split(":", 1)[1]
    chat_id = callback.message.chat.id
    report = mark_card_as_paid(chat_id,card_name)

    await callback.message.answer(text=report)

    await callback.answer()
