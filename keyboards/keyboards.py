
import pandas as pd

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from funcs.data import _load_credit_info
from lexicon.lexicon import LEXICON_COMMANDS_RU


# ---------------------------------------------------------------------------
# Главное меню
# ---------------------------------------------------------------------------

# Команды start и menu не показываем как кнопки главного меню.
# /start используется для запуска бота, а возврат в меню реализован
# отдельной кнопкой «Назад в меню».
menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text=description),
        ]
        for command, description in LEXICON_COMMANDS_RU.items()
        if command not in {"start", "menu"}
    ],
    resize_keyboard=True,
)


# ---------------------------------------------------------------------------
# Общая inline-кнопка возврата в главное меню
# ---------------------------------------------------------------------------

def _get_back_button() -> InlineKeyboardButton:
    """Создаёт inline-кнопку «Назад в меню»."""

    return InlineKeyboardButton(
        text="Назад в меню",
        callback_data="menu",
    )


# back_button = InlineKeyboardMarkup(
#     inline_keyboard=[
#         [_get_back_button()],
#     ]
# )


# ---------------------------------------------------------------------------
# Клавиатура после просмотра информации о карте
# ---------------------------------------------------------------------------

def get_paid_keyboard(card_name: str) -> InlineKeyboardMarkup:
    """Создаёт клавиатуру для выбранной карты.

    Кнопки:
    - «Оплачено» — быстро отмечает карту как оплаченную;
    - «Изменить» — запускает FSM редактирования;
    - «Назад в меню» — возвращает в главное меню.
    """

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Оплачено",
                    callback_data=f"paid:{card_name}",
                )
            ,

                InlineKeyboardButton(
                    text="Изменить",
                    callback_data=f"edit:{card_name}",
                )
            ,

                _get_back_button(),
        ]
        ]
    )


# ---------------------------------------------------------------------------
# Список карт
# ---------------------------------------------------------------------------

def get_cards_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    """Создаёт inline-клавиатуру со списком карт пользователя.

    Для каждой карты создаётся отдельная кнопка.

    Названия карт уникальны, поэтому card_name используется
    непосредственно в callback_data.

    редактировать можно только свои карты
    """

    df = _load_credit_info()

    user_cards = df[
        df["telegram_chat_id"].astype(str).str.strip()
        == str(chat_id).strip()
    ]

    keyboard = []

    for _, row in user_cards.iterrows():
        raw_card_name = row["card_name"]

        # Не показываем пустые названия карт и NaN.
        if pd.isna(raw_card_name):
            continue

        card_name = str(raw_card_name).strip()

        if not card_name:
            continue

        keyboard.append(
            [
                InlineKeyboardButton(
                    text=card_name,
                    callback_data=f"card:{card_name}",
                )
            ]
        )
     # Режим редактирования списка.
    keyboard.append(
        [
            InlineKeyboardButton(
                text="🗑 Редактировать список",
                callback_data="edit_cards_list",
            )
        ]
    )
    keyboard.append(
        [
            _get_back_button(),
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=keyboard,
    )

# ---------клава без фильтра по пользователю ---
def get_all_cards_keyboard() -> InlineKeyboardMarkup:
    """Создаёт inline-клавиатуру со списком карт пользователя.

    Для каждой карты создаётся отдельная кнопка.

    Названия карт уникальны, поэтому card_name используется
    непосредственно в callback_data.

    редактировать общий список нельзя
    """

    user_cards = _load_credit_info()

    keyboard = []

    for _, row in user_cards.iterrows():
        raw_card_name = row["card_name"]

        # Не показываем пустые названия карт и NaN.
        if pd.isna(raw_card_name):
            continue

        card_name = str(raw_card_name).strip()

        if not card_name:
            continue

        keyboard.append(
            [
                InlineKeyboardButton(
                    text=card_name,
                    callback_data=f"card:{card_name}",
                )
            ]
        )

    keyboard.append(
        [
            _get_back_button(),
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=keyboard,
    )

# ---------------------------------------------------------------------------
# Клавиатура редактирования обычного поля
# ---------------------------------------------------------------------------

def get_edit_field_keyboard(field: str) -> InlineKeyboardMarkup:
    """Создаёт клавиатуру для обычного поля FSM.

    Кнопки:
    - «Изменить» — пользователь вводит новое значение;
    - «Далее» — оставить текущее значение и перейти дальше;
    - «Назад в меню» — выйти из редактирования.
    """

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Изменить",
                    callback_data=f"field_edit:{field}",
                ),
                InlineKeyboardButton(
                    text="Далее",
                    callback_data=f"field_next:{field}",
                ),
                _get_back_button(),
            ],
        ]
    )


# ---------------------------------------------------------------------------
# Клавиатура редактирования статуса оплаты
# ---------------------------------------------------------------------------

def get_paid_edit_keyboard() -> InlineKeyboardMarkup:
    """Создаёт клавиатуру для поля `paid`.

    Пользователь может:
    - установить «Оплачено»;
    - установить «Не оплачено»;
    - оставить текущее значение и перейти дальше.
    """

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Оплачено",
                    callback_data="set_paid:true",
                )
            ,

                InlineKeyboardButton(
                    text="❌ Не оплачено",
                    callback_data="set_paid:false",
                )]
            ,

                [InlineKeyboardButton(
                    text="Далее",
                    callback_data="field_next:paid",
                )
            ,

                _get_back_button(),
            ]
        ]
    )

# ---------------------------------------------------
#  клавиатура удаления карты из списка
# та же клава со списком "мои карты", но для удаления
# ---------------------------------------------------
def get_cards_delete_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    """Создаёт клавиатуру для выбора карты, которую нужно удалить."""

    df = _load_credit_info()

    user_cards = df[
        df["telegram_chat_id"].astype(str).str.strip()
        == str(chat_id).strip()]

    keyboard = []

    for _, row in user_cards.iterrows():
        raw_card_name = row["card_name"]

        if pd.isna(raw_card_name):
            continue

        card_name = str(raw_card_name).strip()

        if not card_name:
            continue

        keyboard.append([
                InlineKeyboardButton(
                    text=f"🗑 {card_name}",
                    callback_data=f"delete_card:{card_name}",)])

    keyboard.append([_get_back_button()])

    return InlineKeyboardMarkup(
        inline_keyboard=keyboard,
    )
def get_delete_card_keyboard(
            # chat_id: int,#нужен ли он или берется из хэндлера итак?
                         card_name: str) -> InlineKeyboardMarkup:
    """ создает клаву ДА/НЕТ для подтверждения удаления"""
    keyboard = [
        [InlineKeyboardButton(text="ДА", callback_data= f"confirm_delete:{card_name}"),
        # InlineKeyboardButton(text="НЕТ"), #будет просто возврат в меню
        _get_back_button()]
    ]
    return InlineKeyboardMarkup(
            inline_keyboard=keyboard,
        )