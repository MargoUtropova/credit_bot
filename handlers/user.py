
from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    Message,
    ReplyKeyboardRemove,
)
from lexicon.lexicon import CARD_INFO_NAMES, CARD_FIELDS_LONG
from funcs.data import (
    create_empty_card,
    delete_card_row,
    get_card_row_index,
    get_user_card_row_index,
    get_detailed_card_info,
    get_all_unpaid_payments,
    mark_card_as_paid,
    register_user,
    total_debt,
    update_card_field,
    update_card_timestamp,
    _load_credit_info,
    delete_card
)
from funcs.validation import (
    normalize_date,
    normalize_money,
    normalize_text,
    _validate_card_name,
)
from funcs.formatting import (
    _get_field_prompt,
    _is_empty
                              )
from keyboards.keyboards import (
    get_all_cards_keyboard,
    get_cards_keyboard,
    get_edit_field_keyboard,
    get_paid_edit_keyboard,
    get_paid_keyboard,
    menu_keyboard, get_cards_delete_keyboard,
    get_delete_card_keyboard
)
from lexicon.lexicon import LEXICON_RU
from states.states import CardForm


router = Router()


# CARD_FIELDS_LONG содержит поля CSV. Для FSM берём только те,
# которые действительно вводит пользователь.
EDITABLE_CARD_FIELDS = tuple(
    field
    for field in CARD_FIELDS_LONG
    if field not in {"updated", "telegram_chat_id"}
)




# ----------------------------------------------------------------------
# Вспомогательные функции
# ----------------------------------------------------------------------

def _get_current_field(data: dict):
    """Получить имя текущего поля FSM."""

    field_index = data.get("field_index", 0)

    if field_index < 0 or field_index >= len(EDITABLE_CARD_FIELDS):
        return None

    return EDITABLE_CARD_FIELDS[field_index]


async def show_current_field(
    message: Message,
    state: FSMContext,
) -> None:
    """
    Показать пользователю текущее поле.

    Для paid используются специальные кнопки.
    """

    data = await state.get_data()

    row_index = data.get("row_index")
    field_index = data.get("field_index", 0)

    if row_index is None:
        await state.clear()
        await message.answer(
            "Не удалось определить карту.",
            reply_markup=menu_keyboard,
        )
        return
    field = _get_current_field(data)
    if field is None:
        await finish_card_form(message, state)
        return

    # Загружаем актуальные данные через общую функцию работы с credit_info.csv.
    df = _load_credit_info()

    if row_index not in df.index:
        await state.clear()
        await message.answer(
            "Карта не найдена.",
            reply_markup=menu_keyboard,
        )
        return

    value = df.at[row_index, field]

    text = _get_field_prompt(field, value)

    if field == "paid":
        await message.answer(
            text,
            reply_markup=get_paid_edit_keyboard(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            text,
            reply_markup=get_edit_field_keyboard(field),
            parse_mode="HTML"
        )


async def finish_card_form(
    message: Message,
    state: FSMContext,
) -> None:
    """Завершить добавление или редактирование карты."""

    data = await state.get_data()

    row_index = data.get("row_index")
    mode = data.get("mode")

    if row_index is not None:
        update_card_timestamp(
            chat_id=message.chat.id,
            row_index=row_index,
        )

    await state.clear()

    if mode == "add":
        text = "✅ Карта добавлена."
    else:
        text = "✅ Данные изменены."

    await message.answer(
        text,
        reply_markup=menu_keyboard,
    )


async def cancel_card_form(
    message: Message,
    state: FSMContext,
) -> None:
    """
    Только очистить FSM и, если это новая карта, удалить её строку.

    Сообщение здесь НЕ отправляется.
    """

    data = await state.get_data()

    mode = data.get("mode")
    row_index = data.get("row_index")

    if mode == "add" and row_index is not None:
        delete_card_row(
            chat_id=message.chat.id,
            row_index=row_index,
        )

    await state.clear()


# ----------------------------------------------------------------------
# /start
# ----------------------------------------------------------------------

@router.message(Command("start"))
async def start_handler(
    message: Message,
    state: FSMContext,
):
    """
    Запуск бота.

    Регистрация пользователя выполняется здесь.
    """

    # Если /start пришёл во время добавления карты,
    # новую строку удаляем.
    data = await state.get_data()

    if data.get("mode") is not None:
        await cancel_card_form(message, state)

    nickname = message.from_user.username

    if not nickname:
        nickname = message.from_user.full_name

    register_user(
        nickname=nickname,
        chat_id=message.chat.id,
    )

    await message.answer(
        LEXICON_RU["start"],
        reply_markup=menu_keyboard,
    )


# ----------------------------------------------------------------------
# Меню
# ----------------------------------------------------------------------

@router.message(Command("menu"))
@router.message(F.text == "Назад в меню")
async def menu_handler(
    message: Message,
    state: FSMContext,
):
    """Вернуться в главное меню."""

    data = await state.get_data()

    if data.get("mode") is not None:
        await cancel_card_form(message, state)
    else:
        await state.clear()

    await message.answer(
        "Выберите нужное действие:",
        reply_markup=menu_keyboard,
    )


@router.callback_query(F.data == "menu")
async def process_menu_callback(
    callback: CallbackQuery,
    state: FSMContext,
):
    """Обработать inline-кнопку «Назад в меню»."""

    data = await state.get_data()

    if data.get("mode") is not None:
        await cancel_card_form(callback.message, state)
    else:
        await state.clear()

    await callback.message.answer(
        "Выберите нужное действие:",
        reply_markup=menu_keyboard,
    )

    await callback.answer()


# ----------------------------------------------------------------------
# Мои карты
# ----------------------------------------------------------------------

@router.message(
    StateFilter(None),
    Command("cards"),
)
@router.message(
    StateFilter(None),
    F.text == "Показать мои карты",
)
async def cards_handler(message: Message):
    """Показать карты только текущего пользователя."""

    await message.answer(
        "Выберите карту:",
        reply_markup=get_cards_keyboard(
            chat_id=message.chat.id,
        ),
    )


@router.callback_query(F.data.startswith("card:"))
async def process_card_callback(
    callback: CallbackQuery,
):
    """Показать информацию о выбранной карте из списка своих или всех карт."""

    card_name = callback.data.split(":", 1)[1]

    text = get_detailed_card_info(
        chat_id=callback.message.chat.id,
        card_name=card_name,
    )

    if text is None:
        await callback.answer(
            "Карта не найдена.",
            show_alert=True,
        )
        return

    await callback.message.answer(
        text,
        reply_markup=get_paid_keyboard(card_name),
        parse_mode="HTML"
    )

    await callback.answer()


# ----------------------------------------------------------------------
# Все карты
# ----------------------------------------------------------------------

@router.message(
    StateFilter(None),
    Command("all_cards"),
)
@router.message(
    StateFilter(None),
    F.text == "Просмотр всех карт",
)
async def all_cards_handler(message: Message):
    """Показать все карты всех пользователей."""

    await message.answer(
        "Выберите карту:",
        reply_markup=get_all_cards_keyboard(),
    )

# ----------------------------------------------------------------------
# Оплата
# ----------------------------------------------------------------------

@router.callback_query(F.data.startswith("paid:"))
async def process_paid_callback(
    callback: CallbackQuery,
):
    """Отметить собственную карту как оплаченную."""

    card_name = callback.data.split(":", 1)[1]

    success = mark_card_as_paid(
        chat_id=callback.message.chat.id,
        card_name=card_name,
    )

    if not success:
        await callback.answer(
            "Карта не найдена.",
            show_alert=True,
        )
        return

    await callback.message.answer(
        LEXICON_RU["paid"],
    )

    await callback.answer()


# ----------------------------------------------------------------------
# Добавление карты
# ----------------------------------------------------------------------

@router.message(
    StateFilter(None),
    Command("add_card"),
)
@router.message(
    StateFilter(None),
    F.text == "Добавить информацию о карте",
)
async def add_card_handler(
    message: Message,
    state: FSMContext,
):
    """
    Начать добавление новой карты.

    Строка создаётся сразу.
    """

    row_index = create_empty_card(
        chat_id=message.chat.id,
    )

    await state.update_data(
        mode="add",
        row_index=row_index,
        field_index=0,
    )

    await state.set_state(CardForm.editing)

    await message.answer(
        "➕ Добавляем новую карту.\n\n"
        "Формат названия карты:\n"
        "<code>НазваниеБанка_1234</code>\n\n"
        "Например: <code>Tinkoff_1234</code>",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML"
    )

    await show_current_field(message, state)


# ----------------------------------------------------------------------
# Редактирование существующей карты
# ----------------------------------------------------------------------

@router.callback_query(F.data.startswith("edit:"))
async def process_edit_callback(
    callback: CallbackQuery,
    state: FSMContext,
):
    """Начать редактирование существующей карты."""

    card_name = callback.data.split(":", 1)[1]

    row_index = get_user_card_row_index(
        chat_id=callback.message.chat.id,
        card_name=card_name,
    )

    if row_index is None:
        await callback.answer(
            "Карта не найдена.",
            show_alert=True,
        )
        return

    await state.update_data(
        mode="edit",
        row_index=row_index,
        field_index=0,
    )

    await state.set_state(CardForm.editing)

    await callback.message.answer(
        "✏️ Редактирование карты.",
        reply_markup=ReplyKeyboardRemove(),
    )

    await show_current_field(
        callback.message,
        state,
    )

    await callback.answer()


# ----------------------------------------------------------------------
# Кнопка «Изменить» у поля
# ----------------------------------------------------------------------

@router.callback_query(
    CardForm.editing,
    F.data.startswith("field_edit:"),
)
async def process_field_edit_callback(
    callback: CallbackQuery,
    state: FSMContext,
):
    """Перейти к вводу нового значения поля."""

    field = callback.data.split(":", 1)[1]

    data = await state.get_data()

    current_field = _get_current_field(data)

    if current_field != field:
        await callback.answer(
            "Это поле сейчас не редактируется.",
            show_alert=True,
        )
        return

    await state.set_state(CardForm.waiting_for_value)

    field_title = CARD_INFO_NAMES[field]

    if field == "card_name":
        text = (
            f"<b>{field_title}</b>\n\n"
            "Введите название карты в формате:\n"
            "<code>НазваниеБанка_1234</code>\n\n"
            "Например: <code>Tinkoff_1234</code>"
        )

    elif field in {"grace_till", "check_date", "pay_until"}:
        text = (
            f"<b>{field_title}</b>\n\n"
            "Введите дату в формате:\n"
            "<code>ДД.ММ.ГГГГ</code>"
        )

    elif field in {"min_pay", "debt", "limit"}:
        text = (
            f"<b>{field_title}</b>\n\n"
            "Введите сумму числом."
        )

    elif field == "paid":
        text = (
            "<b>Оплачено</b>\n\n"
            "Выберите нужный статус кнопками ниже."

        )

    else:
        text = f"Введите новое значение для поля «{field_title}»."

    await callback.message.answer(text, parse_mode="HTML")

    await callback.answer()


# ----------------------------------------------------------------------
# Кнопка «Далее»
# ----------------------------------------------------------------------

@router.callback_query(
    CardForm.editing,
    F.data.startswith("field_next:"),
)
async def process_field_next_callback(
    callback: CallbackQuery,
    state: FSMContext,
):
    """Пропустить текущее поле и перейти к следующему."""

    field = callback.data.split(":", 1)[1]

    data = await state.get_data()

    current_field = _get_current_field(data)

    if current_field != field:
        await callback.answer(
            "Это поле сейчас не редактируется.",
            show_alert=True,
        )
        return

    # Для новой карты название обязательно.
    if (
        data.get("mode") == "add"
        and field == "card_name"
    ):
        df = _load_credit_info()

        row_index = data.get("row_index")

        if row_index in df.index:
            current_name = df.at[row_index, "card_name"]

            if _is_empty(current_name):
                await callback.answer(
                    "Название карты обязательно.",
                    show_alert=True,
                )
                return

            if not _validate_card_name(str(current_name)):
                await callback.answer(
                    "Используйте формат НазваниеБанка_1234.",
                    show_alert=True,
                )
                return

    await move_to_next_field(
        callback.message,
        state,
    )

    await callback.answer()


async def move_to_next_field(
    message: Message,
    state: FSMContext,
) -> None:
    """Перейти к следующему полю."""

    data = await state.get_data()

    next_index = data.get("field_index", 0) + 1

    await state.update_data(
        field_index=next_index,
    )

    await state.set_state(CardForm.editing)

    await show_current_field(
        message,
        state,
    )


# ----------------------------------------------------------------------
# Изменение paid кнопками
# ----------------------------------------------------------------------

@router.callback_query(
    CardForm.editing,
    F.data.startswith("set_paid:"),
)
async def process_set_paid_callback(
    callback: CallbackQuery,
    state: FSMContext,
):
    """Установить статус оплачено / не оплачено."""

    data = await state.get_data()

    current_field = _get_current_field(data)

    if current_field != "paid":
        await callback.answer(
            "Сейчас редактируется другое поле.",
            show_alert=True,
        )
        return

    value = callback.data.split(":", 1)[1] == "true"

    row_index = data.get("row_index")

    success = update_card_field(
        chat_id=callback.message.chat.id,
        row_index=row_index,
        field="paid",
        value=value,
    )

    if not success:
        await callback.answer(
            "Не удалось сохранить значение.",
            show_alert=True,
        )
        return

    await callback.message.answer(
        "Значение сохранено."
    )

    await move_to_next_field(
        callback.message,
        state,
    )

    await callback.answer()


# ----------------------------------------------------------------------
# Ввод нового значения поля
# ----------------------------------------------------------------------

@router.message(CardForm.waiting_for_value)
async def receive_new_field_value(
    message: Message,
    state: FSMContext,
):
    """Получить новое значение поля от пользователя."""

    value = (message.text or "").strip()

    # Команды не должны записываться в данные карты.
    if value.startswith("/"):
        await message.answer(
            "Сейчас идёт редактирование карты.\n"
            "Чтобы выйти, используйте /menu."
        )
        return


    data = await state.get_data()

    row_index = data.get("row_index")
    field = _get_current_field(data)

    if row_index is None or field is None:
        await state.clear()

        await message.answer(
            "Редактирование прервано",
            reply_markup=menu_keyboard,
        )
        return

    # --------------------------------------------------------------
    # Название карты
    # --------------------------------------------------------------

    if field == "card_name":
        if not value:
            await message.answer(
                "Название карты обязательно.\n\n"
                "Используйте формат:\n"
                "<code>НазваниеБанка_1234</code>",
                parse_mode="HTML"
            )
            return

        if not _validate_card_name(value):
            await message.answer(
                "Неверный формат названия карты.\n\n"
                "Используйте:\n"
                "<code>НазваниеБанка_1234</code>\n\n"
                "Например:\n"
                "<code>Tinkoff_1234</code>",
                parse_mode="HTML"
            )
            return

        # Проверяем уникальность названия среди всех карт.
        existing_index = get_card_row_index(value)

        if (
            existing_index is not None
            and existing_index != row_index
        ):
            await message.answer(
                "Карта с таким названием уже существует.\n"
                "Введите другое название."
            )
            return

        converted_value = normalize_text(value)

    # --------------------------------------------------------------
    # Даты
    # --------------------------------------------------------------

    elif field in {
        "grace_till",
        "check_date",
        "pay_until",
    }:
        try:
            converted_value = normalize_date(value)

        except ValueError:
            await message.answer(
                "Неверный формат даты.\n"
                "Введите дату в формате <code>ДД.ММ.ГГГГ</code>.",
                parse_mode="HTML"
            )
            return

    # --------------------------------------------------------------
    # Денежные значения
    # --------------------------------------------------------------

    elif field in {
        "min_pay",
        "debt",
        "limit",
    }:
        try:
            converted_value = normalize_money(value)
        except ValueError:
            await message.answer(
                "Введите корректную сумму числом.\n"
                "Например: <code>1500</code> или <code>1500.50</code>.",
                parse_mode="HTML"
            )
            return

    # --------------------------------------------------------------
    # Остальные поля
    # --------------------------------------------------------------

    else:
        converted_value = normalize_text(value)

    # --------------------------------------------------------------
    # Немедленно сохраняем изменение
    # --------------------------------------------------------------

    success = update_card_field(
        chat_id=message.chat.id,
        row_index=row_index,
        field=field,
        value=converted_value,
    )

    if not success:
        await message.answer(
            "Не удалось сохранить значение."
        )
        return

    await message.answer(
        "✅ Значение сохранено."
    )

    # После сохранения переходим дальше.
    await move_to_next_field(
        message,
        state,
    )


# ----------------------------------------------------------------------
# Ближайшие платежи
# ----------------------------------------------------------------------

@router.message(
    StateFilter(None),
    Command("check_payments"),
)
@router.message(
    StateFilter(None),
    F.text == "Ближайшие платежи",
)
async def check_payments_handler(message: Message):
    """
    Показать ближайшие платежи по ВСЕМ картам всех пользователей.
    """

    payments = get_all_unpaid_payments()
    if not payments:
        await message.answer(
            "Неоплаченных платежей нет."
        )
        return

    text = (
        "📅 <b>Неоплаченные платежи</b>\n\n"
        + "\n\n".join(
            payment["text"]
            for payment in payments
        )
    )

    await message.answer(text, parse_mode="HTML")


# ----------------------------------------------------------------------
# Общая сумма долга
# ----------------------------------------------------------------------

@router.message(
    StateFilter(None),
    Command("total_debt"),
)
@router.message(
    StateFilter(None),
    F.text == "Показать общую сумму долга по кредитам",
)
async def total_debt_handler(message: Message):
    """Показать общую сумму долга текущего пользователя."""

    debt = total_debt(
        chat_id=message.chat.id,
    )

    if debt.is_integer():
        debt_text = f"{int(debt):,}".replace(",", " ")
    else:
        debt_text = (
            f"{debt:,.2f}"
            .replace(",", " ")
            .replace(".", ",")
        )

    await message.answer(
        f"💰 Общая сумма долга: <b>{debt_text}</b>",
        parse_mode="HTML"
    )


# ----------------
# УДАЛЕНИЕ КАРТЫ
# --------------------------
@router.callback_query(F.data == "edit_cards_list")
async def edit_cards_list_handler(callback: CallbackQuery):
    """Переходит в режим удаления карт."""

    await callback.message.edit_text(
        "Выберите карту, которую хотите удалить:",
        # выводится список карт для выбора к удалению
        reply_markup=get_cards_delete_keyboard(
            callback.from_user.id,
        ),
    )

    await callback.answer()


@router.callback_query(F.data.startswith("delete_card:"))
async def delete_card_handler(callback: CallbackQuery):
    """Запрашивает подтверждение удаления карты."""

    card_name = callback.data.split(":", 1)[1]

    keyboard = get_delete_card_keyboard(card_name)
    # выводится клава из вариантов "Да/Назад в меню"
    await callback.message.edit_text(
        f"Удалить карту «{card_name}»?",
        reply_markup=keyboard,
    )

    await callback.answer()

@router.callback_query(F.data.startswith("confirm_delete:"))
async def confirm_delete_card_handler(callback: CallbackQuery):
    """Удаляет выбранную карту после подтверждения."""

    card_name = callback.data.split(":", 1)[1]

    deleted = delete_card(
        chat_id=callback.from_user.id,
        card_name=card_name,
    )

    if deleted:
        text = f"Карта «{card_name}» удалена."
    else:
        text = f"Карта «{card_name}» не найдена."

    await callback.message.edit_text(
        text,
        reply_markup=get_cards_keyboard(
            callback.from_user.id,
        ),
    )

    await callback.answer()