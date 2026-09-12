import pandas as pd
from lexicon.lexicon import CARD_INFO_NAMES


def _is_empty(value) -> bool:
    """Проверить, является ли значение пустым."""
    if value is None:
        return True

    try:
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        pass

    return str(value).strip() == ""


def _is_paid(value) -> bool:
    """Нормализовать значение paid из CSV к bool."""
    if isinstance(value, bool):
        return value

    if _is_empty(value):
        return False

    return str(value).strip().lower() in {
        "true",
        "1",
        "yes",
        "да",
        "оплачено",
    }


def _format_date(value) -> str:
    """Показать дату пользователю в формате ДД.ММ.ГГГГ."""
    if _is_empty(value):
        return "—"

    try:
        return pd.to_datetime(
            str(value).strip(),
            format="%Y-%m-%d",
            errors="raise",
        ).strftime("%d.%m.%Y")
    except (ValueError, TypeError):
        return str(value).strip()


def _format_money(value) -> str:
    """Показать денежное значение в читаемом виде."""
    if _is_empty(value):
        return "—"

    try:
        number = float(value)

        if number.is_integer():
            return f"{int(number):,}".replace(",", " ")

        return f"{number:,.2f}".replace(",", " ").replace(".", ",")
    except (ValueError, TypeError):
        return str(value).strip()


def _format_current_value(field: str, value) -> str:
    """Подготовить текущее значение поля для показа пользователю."""

    if field == "paid":
        if isinstance(value, str):
            is_paid = value.strip().lower() in {
                "true",
                "1",
                "yes",
                "да",
                "оплачено",
            }
        else:
            is_paid = bool(value)

        return "✅ Оплачено" if is_paid else "❌ Не оплачено"

    if _is_empty(value):
        return "не заполнено"

    return str(value).strip()


def _get_field_prompt(field: str, value) -> str:
    """Сформировать сообщение с текущим значением поля."""

    field_title = CARD_INFO_NAMES[field]
    current_value = _format_current_value(field, value)

    return (
        f"<b>{field_title}</b>\n\n"
        f"Текущее значение: <code>{current_value}</code>\n\n"
        f"Выберите действие:"
    )


def _build_card_report(row: pd.Series) -> str:
    """Сформировать подробную информацию о карте."""
    try:
        chat_id = int(float(row["telegram_chat_id"]))
    except (ValueError, TypeError):
        chat_id = row["telegram_chat_id"]

    # Импорт внутри функции исключает циклический импорт data -> formatting.
    from .data import _get_username

    nickname = _get_username(chat_id)

    card_name = (
        "—"
        if _is_empty(row["card_name"])
        else str(row["card_name"]).strip()
    )

    text = (
        f"<b>{nickname}</b>\n\n"
        f"💳 <b>{card_name}</b>\n\n"
        f"Грейс-период: {_format_date(row['grace_till'])}\n"
        f"Дата выписки: {_format_date(row['check_date'])}\n"
        f"Минимальный платеж: {_format_money(row['min_pay'])}\n"
        f"Оплатить до: {_format_date(row['pay_until'])}\n"
        f"Долг: {_format_money(row['debt'])}\n"
        f"Кредитный лимит: {_format_money(row['limit'])}\n"
    )

    # Дополнительные поля показываем только если они реально есть в схеме.
    if "bic" in row.index:
        bic = "—" if _is_empty(row["bic"]) else str(row["bic"]).strip()
        text += f"БИК: {bic}\n"

    if "account" in row.index:
        account = "—" if _is_empty(row["account"]) else str(row["account"]).strip()
        text += f"Счёт: {account}\n"

    text += f"Статус: {'✅ Оплачено' if _is_paid(row['paid']) else '❌ Не оплачено'}"

    return text
