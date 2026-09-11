from dataclasses import dataclass

from environs import Env


@dataclass
class TgBot:
    """Настройки Telegram-бота."""

    token: str  # Токен для доступа к Telegram Bot API


@dataclass
class LogSettings:
    """Настройки логирования."""

    level: str
    format: str


@dataclass
class Config:
    """Основная конфигурация приложения."""

    bot: TgBot
    log: LogSettings


def load_config(path: str | None = None) -> Config:
    """Загружает настройки из файла .env.

    Args:
        path: Необязательный путь к файлу с переменными окружения.
              Если путь не указан, environs ищет .env автоматически.

    Returns:
        Объект Config с настройками бота и логирования.
    """

    env = Env()

    # Если путь не указан, environs ищет файл .env
    # в текущей директории и родительских директориях.
    if path is None:
        env.read_env()
    else:
        env.read_env(path)

    return Config(
        bot=TgBot(
            token=env("BOT_TOKEN"),
        ),
        log=LogSettings(
            level=env("LOG_LEVEL"),
            format=env("LOG_FORMAT"),
        ),
    )