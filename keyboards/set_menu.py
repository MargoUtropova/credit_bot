
from aiogram import Bot
from aiogram.types import BotCommand

from lexicon.lexicon import LEXICON_COMMANDS_RU


async def set_main_menu(bot: Bot) -> None:
    """Устанавливает команды бота в меню Telegram.

    Названия команд и их описания берутся из LEXICON_COMMANDS_RU.
    Например:
        "cards": "Показать список всех моих карт"

    превратится в команду /cards с указанным описанием.
    """

    main_menu = [
        BotCommand(
            command=command,
            description=description,
        )
        for command, description in LEXICON_COMMANDS_RU.items()
    ]

    await bot.set_my_commands(main_menu)
