from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from lexicon.lexicon import LEXICON_RU
from keyboards.keyboards import menu_keyboard, get_cards_keyboard, get_paid_keyboard, back_button
from funcs.funcs import get_upcoming_payments, get_detailed_card_info, total_debt, mark_card_as_paid

router = Router()

@router.message(CommandStart())
async def process_start(message: Message):
    """При старте предлагаем главное меню."""
    await message.answer(
        text=LEXICON_RU['start'],
        reply_markup=menu_keyboard
    )
# ------------ handler для команды меню от старта до возврата в меню
@router.message(Command("menu"))
@router.message(F.text.strip() == "Назад в меню")
async def menu_handler(message: Message):
    await message.answer(
        "Выберите нужное действие:",
        reply_markup=menu_keyboard
    )

@router.callback_query(F.data == "menu")
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
    report = get_upcoming_payments()
    await message.answer(text=report)

@router.callback_query(F.data == "check_payments")
async def process_payments_callback(callback: CallbackQuery):
    report = get_upcoming_payments()

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

    cards_keyboard = get_cards_keyboard()

    if isinstance(event, Message):
        await event.answer(
            text="Выберите карту из списка ниже:",
            reply_markup=cards_keyboard
        )

    elif isinstance(event, CallbackQuery):
        await event.message.answer(
            text="Выберите карту из списка ниже:",
            reply_markup=cards_keyboard
        )
        await event.answer()

# ---------  handler при выборе конкретной карты-----
@router.callback_query(F.data.startswith("card:"))
async def process_card_detail(callback: CallbackQuery):

    card_name = callback.data.split(":", 1)[1]

    report = get_detailed_card_info(card_name)

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

    report = total_debt()

    if isinstance(event, Message):
        await event.answer(text=report, reply_markup=back_button)

    elif isinstance(event, CallbackQuery):
        await event.message.answer(text=report, reply_markup=back_button)
        await event.answer()

# ---------- handler чтобы пометить карту как оплаченную
# text="Оплачено",
# callback_data="paid"
@router.callback_query(F.data.startswith("paid:"))
async def process_paid(callback: CallbackQuery):

    card_name = callback.data.split(":", 1)[1]

    report = mark_card_as_paid(card_name)

    await callback.message.answer(text=report)

    await callback.answer()
