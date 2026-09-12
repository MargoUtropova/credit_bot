from datetime import datetime


def _validate_card_name(value: str) -> bool:
    """Проверить формат НазваниеБанка_1234."""
    value = value.strip()

    if not value or "_" not in value:
        return False

    bank_name, last_four = value.rsplit("_", 1)

    if not bank_name.strip():
        return False

    return len(last_four) == 4 and last_four.isdigit()


def normalize_date(value: str) -> str:
    """Проверить дату ДД.ММ.ГГГГ и сохранить её в CSV как YYYY-MM-DD."""
    return datetime.strptime(value.strip(), "%d.%m.%Y").strftime("%Y-%m-%d")


def normalize_money(value: str) -> float:
    """Проверить неотрицательную денежную сумму."""
    normalized = value.replace(" ", "").replace(",", ".")
    number = float(normalized)

    if number < 0:
        raise ValueError

    return number


def normalize_text(value: str) -> str:
    """Очистить обычное текстовое значение."""
    return value.strip()
