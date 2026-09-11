from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import pandas as pd

from funcs.funcs import (
    CARD_FIELDS,
    create_empty_card,
    delete_card_row,
    get_card_row_index,
    get_detailed_card_info,
    get_upcoming_payments,
    mark_card_as_paid,
    register_user,
    total_debt,
    update_card_field,
    update_card_timestamp,
)
from keyboards.keyboards import (
    back_button,
    get_cards_keyboard,
    get_edit_field_keyboard,
    get_paid_edit_keyboard,
    get_paid_keyboard,
    menu_keyboard,
)
from lexicon.lexicon import LEXICON_COMMANDS_RU, LEXICON_RU
from states.states import CardForm


router = Router()


# ---------------------------------------------------------------------------
# /start
# ---------------------------------------------------------------------------

@router.message(CommandStart())
async def process_start(message: Message):
    """Обрабатывает команду /start.

    Регистрирует пользователя в users.csv и показывает
    главное меню бота.
    """

    chat_id = message.chat.id
    nickname = message.from_user.username

    register_user(
        nickname=nickname,
        chat_id=chat_id,
    )

    await message.answer(
        text=LEXICON_RU["start"],
        reply_markup=menu_keyboard,
    )


# ---------------------------------------------------------------------------
# Отмена текущей операции с картой
# ---------------------------------------------------------------------------

async def cancel_card_form(
    message: Message,
    state: FSMContext,
):
    """Отменяет текущую операцию с картой.

    Если выполняется добавление новой карты, незавершённая
    строка удаляется из CSV.

    Если выполняется редактирование существующей карты,
    данные сохраняются.
    """

    data = await state.get_data()

    mode = data.get("mode")
    row_index = data.get("row_index")
    chat_id = message.chat.id

    if mode == "add" and row_index is not None:
        delete_card_row(
            chat_id=chat_id,
            row_index=row_index,
        )

    await state.clear()

    await message.answer(
        text="Действие отменено.",
        reply_markup=menu_keyboard,
    )


# ---------------------------------------------------------------------------
# Завершение добавления / редактирования
# ---------------------------------------------------------------------------

async def finish_card_form(
    message: Message,
    state: FSMContext,
):
    """Завершает добавление или редактирование карты.

    Перед завершением автоматически обновляет поле `updated`
    текущей датой.
    """

    data = await state.get_data()

    row_index = data["row_index"]
    mode = data["mode"]
    chat_id = message.chat.id

    update_card_timestamp(
        chat_id=chat_id,
        row_index=row_index,
    )

    await state.clear()

    if mode == "add":
        text = "✅ Карта добавлена."
    else:
        text = "✅ Данные изменены."

    await message.answer(
        text=text,
        reply_markup=back_button,
    )


# ---------------------------------------------------------------------------
# Главное меню
# ---------------------------------------------------------------------------

@router.message(Command("menu"))
@router.message(F.text == "Назад в меню")
async def menu_handler(
    message: Message,
    state: FSMContext,
):
    """Возвращает пользователя в главное меню.

    Если пользователь находится внутри FSM, текущая операция
    сначала отменяется.
    """

    data = await state.get_data()

    if data.get("mode") is not None:
        await cancel_card_form(
            message=message,
            state=state,
        )
        return

    await state.clear()

    await message.answer(
        text="Выберите нужное действие:",
        reply_markup=menu_keyboard,
    )


@router.callback_query(F.data == "menu")
async def process_menu_callback(
    callback: CallbackQuery,
    state: FSMContext,
):
    """Обрабатывает inline-кнопку «Назад в меню»."""

    await cancel_card_form(
        message=callback.message,
        state=state,
    )

    await callback.answer()


# ---------------------------------------------------------------------------
# Ближайшие платежи
# ---------------------------------------------------------------------------

@router.message(Command("check_payments"))
@router.message(
    F.text == LEXICON_COMMANDS_RU["check_payments"]
)
async def process_payments(message: Message):
    """Показывает ближайшие платежи пользователя."""

    chat_id = message.chat.id
    report = get_upcoming_payments(chat_id)

    await message.answer(
        text=report,
        reply_markup=back_button,
    )


@router.callback_query(F.data == "check_payments")
async def process_payments_callback(
    callback: CallbackQuery,
):
    """Показывает ближайшие платежи через inline-кнопку."""

    chat_id = callback.message.chat.id
    report = get_upcoming_payments(chat_id)

    await callback.message.answer(
        text=report,
        reply_markup=back_button,
        parse_mode="HTML",
    )

    await callback.answer()


# ---------------------------------------------------------------------------
# Список карт
# ---------------------------------------------------------------------------

@router.message(Command("cards"))
@router.message(
    F.text == LEXICON_COMMANDS_RU["cards"]
)
async def process_cards(message: Message):
    """Показывает список карт пользователя."""

    chat_id = message.chat.id

    await message.answer(
        text="Выберите карту из списка ниже:",
        reply_markup=get_cards_keyboard(chat_id),
    )


@router.callback_query(F.data == "cards")
async def process_cards_callback(
    callback: CallbackQuery,
):
    """Показывает список карт через inline-кнопку."""

    chat_id = callback.message.chat.id

    await callback.message.answer(
        text="Выберите карту из списка ниже:",
        reply_markup=get_cards_keyboard(chat_id),
    )

    await callback.answer()


# ---------------------------------------------------------------------------
# Информация о карте
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("card:"))
async def process_card_detail(
    callback: CallbackQuery,
):
    """Показывает подробную информацию о выбранной карте."""

    card_name = callback.data.split(":", 1)[1]
    chat_id = callback.message.chat.id

    report = get_detailed_card_info(
        chat_id,
        card_name,
    )

    await callback.message.answer(
        text=report,
        reply_markup=get_paid_keyboard(card_name),
    )

    await callback.answer()


# ---------------------------------------------------------------------------
# Общая сумма долга
# ---------------------------------------------------------------------------

@router.message(Command("total_debt"))
@router.message(
    F.text == LEXICON_COMMANDS_RU["total_debt"]
)
async def get_total_debt(message: Message):
    """Показывает общий долг пользователя."""

    chat_id = message.chat.id
    report = total_debt(chat_id)

    await message.answer(
        text=report,
        reply_markup=back_button,
    )


@router.callback_query(F.data == "total_debt")
async def get_total_debt_callback(
    callback: CallbackQuery,
):
    """Показывает общий долг через inline-кнопку."""

    chat_id = callback.message.chat.id
    report = total_debt(chat_id)

    await callback.message.answer(
        text=report,
        reply_markup=back_button,
    )

    await callback.answer()


# ---------------------------------------------------------------------------
# Быстрая отметка «Оплачено»
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("paid:"))
async def process_paid(callback: CallbackQuery):
    """Помечает выбранную карту как оплаченную."""

    card_name = callback.data.split(":", 1)[1]
    chat_id = callback.message.chat.id

    report = mark_card_as_paid(
        chat_id,
        card_name,
    )

    await callback.message.answer(
        text=report,
    )

    await callback.answer()


# ---------------------------------------------------------------------------
# Показ текущего поля FSM
# ---------------------------------------------------------------------------

async def show_current_field(
    message: Message,
    state: FSMContext,
):
    """Показывает текущее поле формы и его значение."""

    data = await state.get_data()

    row_index = data["row_index"]
    field_index = data["field_index"]

    field, friendly_name = CARD_FIELDS[field_index]

    df = pd.read_csv(
        r"credit_info/credit_info.csv",
        encoding="utf-8",
    )

    value = df.loc[row_index, field]

    # Форматирование дат.
    if field in [
        "grace_till",
        "check_date",
        "pay_until",
    ]:
        if pd.notna(value) and str(value).strip():
            try:
                value = pd.to_datetime(value).strftime(
                    "%d.%m.%Y"
                )
            except Exception:
                value = str(value)
        else:
            value = "—"

    # Форматирование статуса оплаты.
    elif field == "paid":
        if str(value).strip().lower() == "true":
            value = "✅ Оплачено"
        else:
            value = "❌ Не оплачено"

    # Пустые значения.
    elif pd.isna(value) or str(value).strip() == "":
        value = "—"

    text = (
        f"<b>{friendly_name}</b>\n\n"
        f"Текущее значение: {value}"
    )

    if field == "paid":
        keyboard = get_paid_edit_keyboard()
    else:
        keyboard = get_edit_field_keyboard(field)

    await message.answer(
        text=text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )


# ---------------------------------------------------------------------------
# Начало редактирования существующей карты
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("edit:"))
async def start_edit_card(
    callback: CallbackQuery,
    state: FSMContext,
):
    """Запускает FSM редактирования существующей карты."""

    card_name = callback.data.split(":", 1)[1]
    chat_id = callback.message.chat.id

    row_index = get_card_row_index(
        chat_id,
        card_name,
    )

    if row_index is None:
        await callback.message.answer(
            f"❌ Карта «{card_name}» не найдена."
        )
        await callback.answer()
        return

    await state.update_data(
        mode="edit",
        row_index=row_index,
        field_index=0,
    )

    await state.set_state(
        CardForm.editing
    )

    await show_current_field(
        callback.message,
        state,
    )

    await callback.answer()


# ---------------------------------------------------------------------------
# Переход к следующему полю
# ---------------------------------------------------------------------------

@router.callback_query(
    CardForm.editing,
    F.data.startswith("field_next:"),
)
async def next_field(
    callback: CallbackQuery,
    state: FSMContext,
):
    """Переходит к следующему полю формы."""

    data = await state.get_data()

    row_index = data["row_index"]
    field_index = data["field_index"]
    mode = data["mode"]

    field, _ = CARD_FIELDS[field_index]

    # При добавлении новой карты название обязательно.
    if mode == "add" and field == "card_name":
        df = pd.read_csv(
            r"credit_info/credit_info.csv",
            encoding="utf-8",
        )

        current_name = str(
            df.loc[row_index, "card_name"]
        ).strip()

        if not current_name:
            await callback.answer(
                "Сначала укажите название карты",
                show_alert=True,
            )
            return

    next_index = field_index + 1

    # Все поля пройдены — завершаем форму.
    if next_index >= len(CARD_FIELDS):
        await finish_card_form(
            message=callback.message,
            state=state,
        )

        await callback.answer()
        return

    await state.update_data(
        field_index=next_index,
    )

    await show_current_field(
        callback.message,
        state,
    )

    await callback.answer()


# ---------------------------------------------------------------------------
# Изменение значения поля
# ---------------------------------------------------------------------------

@router.callback_query(
    CardForm.editing,
    F.data.startswith("field_edit:"),
)
async def edit_field(
    callback: CallbackQuery,
    state: FSMContext,
):
    """Переводит FSM в состояние ожидания нового значения."""

    field = callback.data.split(":", 1)[1]

    await state.update_data(
        current_field=field,
    )

    await state.set_state(
        CardForm.waiting_for_value
    )

    field_names = dict(CARD_FIELDS)
    friendly_name = field_names[field]

    await callback.message.answer(
        f"Введите новое значение для поля "
        f"«{friendly_name}»:"
    )

    await callback.answer()


# ---------------------------------------------------------------------------
# Получение нового значения поля
# ---------------------------------------------------------------------------

@router.message(CardForm.waiting_for_value)
async def receive_new_field_value(
    message: Message,
    state: FSMContext,
):
    """Получает, проверяет и сохраняет новое значение поля."""

    data = await state.get_data()

    row_index = data["row_index"]
    field = data["current_field"]
    field_index = data["field_index"]
    chat_id = message.chat.id

    value = message.text.strip()

    # Обработка дат.
    if field in [
        "grace_till",
        "check_date",
        "pay_until",
    ]:
        try:
            parsed_date = pd.to_datetime(
                value,
                format="%d.%m.%Y",
            )

            value = parsed_date.strftime(
                "%Y-%m-%d"
            )

        except ValueError:
            await message.answer(
                "❌ Неверный формат даты.\n"
                "Введите дату в формате ДД.ММ.ГГГГ\n\n"
                "Например: 25.09.2026"
            )
            return

    # Обработка числовых полей.
    elif field in [
        "min_pay",
        "debt",
        "limit",
    ]:
        value = value.replace(" ", "")

        try:
            value = float(value)

            if value.is_integer():
                value = int(value)

        except ValueError:
            await message.answer(
                "❌ Нужно ввести число.\n\n"
                "Например: 45000"
            )
            return

    # Сохраняем новое значение.
    success = update_card_field(
        chat_id=chat_id,
        row_index=row_index,
        field=field,
        value=value,
    )

    if not success:
        await message.answer(
            "❌ Не удалось изменить данные."
        )

        await state.clear()
        return

    await state.set_state(
        CardForm.editing
    )

    next_index = field_index + 1

    # Если изменено последнее поле — завершаем форму.
    if next_index >= len(CARD_FIELDS):
        await finish_card_form(
            message=message,
            state=state,
        )
        return

    await state.update_data(
        field_index=next_index,
    )

    await show_current_field(
        message,
        state,
    )


# ---------------------------------------------------------------------------
# Изменение статуса оплаты
# ---------------------------------------------------------------------------

@router.callback_query(
    CardForm.editing,
    F.data.startswith("set_paid:"),
)
async def set_paid(
    callback: CallbackQuery,
    state: FSMContext,
):
    """Изменяет статус оплаты карты."""

    data = await state.get_data()

    row_index = data["row_index"]
    field_index = data["field_index"]
    chat_id = callback.message.chat.id

    paid_value = (
        callback.data.split(":", 1)[1] == "true"
    )

    success = update_card_field(
        chat_id=chat_id,
        row_index=row_index,
        field="paid",
        value=paid_value,
    )

    if not success:
        await callback.message.answer(
            "❌ Не удалось изменить статус оплаты."
        )

        await callback.answer()
        return

    next_index = field_index + 1

    # paid — последнее поле.
    if next_index >= len(CARD_FIELDS):
        await finish_card_form(
            message=callback.message,
            state=state,
        )

        await callback.answer()
        return

    await state.update_data(
        field_index=next_index,
    )

    await show_current_field(
        callback.message,
        state,
    )

    await callback.answer()


# ---------------------------------------------------------------------------
# Добавление новой карты
# ---------------------------------------------------------------------------

@router.message(Command("add_card"))
@router.message(
    F.text == LEXICON_COMMANDS_RU["add_card"]
)
async def add_card(
    message: Message,
    state: FSMContext,
):
    """Запускает FSM для добавления новой карты.

    Обработчик срабатывает:
    - по команде /add_card;
    - по кнопке «Добавить информацию о карте».

    Сначала создаётся пустая строка в CSV.
    При отмене незавершённая строка удаляется.
    """

    chat_id = message.chat.id

    row_index = create_empty_card(
        chat_id=chat_id,
    )

    await state.update_data(
        mode="add",
        row_index=row_index,
        field_index=0,
    )

    await state.set_state(
        CardForm.editing
    )

    await message.answer(
        "➕ Добавляем новую карту."
    )

    await show_current_field(
        message,
        state,
    )
