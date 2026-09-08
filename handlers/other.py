from aiogram import Router
from aiogram.types import Message
from lexicon.lexicon import LEXICON_RU

router = Router()

@router.message()
async def process_unknown_message(message: Message):
    """Ловит любой некорректный текстовый ввод, отправленный мимо кнопок."""
    error_text = LEXICON_RU.get('error', 'Неизвестная команда. Пожалуйста, используйте кнопки меню.')
    await message.reply(text=error_text)
