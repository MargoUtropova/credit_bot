# ==================== БЫЛО ====================
# hello_button, bye_button = KeyboardButton(text='Привет, давай!'), KeyboardButton(text='Не хочу, покеда!')
# greeting_kb = ReplyKeyboardMarkup(keyboard=[[hello_button, bye_button]], resize_keyboard=True, one_time_keyboard=True)
# stone, scissors, paper = KeyboardButton(text='⛰️'), KeyboardButton(text='✂️'), KeyboardButton(text='🧻')
# keyboard = ReplyKeyboardMarkup(keyboard=[[stone, scissors, paper]], resize_keyboard=True, one_time_keyboard=True)
# yes, no = KeyboardButton(text='Да'), KeyboardButton(text='Нет')
# new_game_kb = ReplyKeyboardMarkup(keyboard=[[yes, no]], resize_keyboard=True, one_time_keyboard=True)

# ==================== СТАЛО ====================
import pandas as pd
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from lexicon.lexicon import LEXICON_COMMANDS_RU

# Главное меню после /start

menu_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text=value,
                callback_data=key
            )
        ]
        for key, value in LEXICON_COMMANDS_RU.items()
        if key not in ('start', 'menu')
    ]
)
back_button =InlineKeyboardMarkup(
    inline_keyboard = [[
                InlineKeyboardButton(
            text="Назад в меню",
            callback_data="menu")
        ]]
)

def get_paid_keyboard(card_name: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Оплачено",
                    callback_data=f"paid:{card_name}"
                ),
                InlineKeyboardButton(
                    text="Назад в меню",
                    callback_data="menu"
                )
            ]
        ]
    )
def get_cards_keyboard(
    file_path: str = r"credit_info\credit_info.csv"
) -> InlineKeyboardMarkup:

    df = pd.read_csv(file_path, encoding="utf-8")

    keyboard = [
        [
            InlineKeyboardButton(
                text=row['card_name'],
                callback_data=f"card:{row['card_name']}"
            )
        ]
        for _, row in df.iterrows()
    ]
    keyboard.append([InlineKeyboardButton(
                text="Назад в меню",
                callback_data="menu"
            )])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
