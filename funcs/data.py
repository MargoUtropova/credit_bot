import os
from datetime import date, timedelta

import pandas as pd

from lexicon.lexicon import CARD_FIELDS_LONG, CARD_INFO_NAMES, USERS_COLUMNS
from funcs.formatting import _build_card_report, _format_date, _format_money, _is_empty, _is_paid


CREDIT_INFO_FILE = r"credit_info/credit_info.csv"
USERS_FILE = r"credit_info/users.csv"


# ----------------------------------------------------------------------
# Работа с CSV
# ----------------------------------------------------------------------

def _load_credit_info() -> pd.DataFrame:
    """Загрузить credit_info.csv и привести его к ожидаемой структуре."""
    if not os.path.exists(CREDIT_INFO_FILE):
        return pd.DataFrame(columns=CARD_INFO_NAMES.keys())

    df = pd.read_csv(CREDIT_INFO_FILE, encoding="utf-8")

    for column in CARD_INFO_NAMES:
        if column not in df.columns:
            df[column] = ""

    return df[CARD_INFO_NAMES.keys()]


def _save_credit_info(df: pd.DataFrame) -> None:
    """Сохранить таблицу кредитных карт."""
    os.makedirs(os.path.dirname(CREDIT_INFO_FILE), exist_ok=True)
    df.to_csv(CREDIT_INFO_FILE, index=False, encoding="utf-8")


def _load_users() -> pd.DataFrame:
    """Загрузить users.csv и привести его к ожидаемой структуре."""
    if not os.path.exists(USERS_FILE):
        return pd.DataFrame(columns=USERS_COLUMNS)

    df = pd.read_csv(USERS_FILE, encoding="utf-8")

    for column in USERS_COLUMNS:
        if column not in df.columns:
            df[column] = ""

    return df[USERS_COLUMNS]


def _save_users(df: pd.DataFrame) -> None:
    """Сохранить таблицу пользователей."""
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    df.to_csv(USERS_FILE, index=False, encoding="utf-8")


# ----------------------------------------------------------------------
# Пользователи
# ----------------------------------------------------------------------

def register_user(nickname: str, chat_id: int) -> None:
    """Зарегистрировать пользователя или обновить его nickname."""
    users = _load_users()
    chat_id_str = str(chat_id)

    mask = (
        users["telegram_chat_id"].astype(str).str.strip()
        == chat_id_str
    )

    if mask.any():
        index = users.index[mask][0]
        users.at[index, "nickname"] = nickname
    else:
        users.loc[len(users)] = {
            "nickname": nickname,
            "telegram_chat_id": chat_id,
        }

    _save_users(users)


def get_users() -> list[int]:
    """Получить telegram_chat_id всех зарегистрированных пользователей."""
    users = _load_users()
    result = []

    for value in users["telegram_chat_id"]:
        if _is_empty(value):
            continue

        try:
            result.append(int(float(value)))
        except (ValueError, TypeError):
            continue

    return result


def _get_username(chat_id: int) -> str:
    """Найти nickname пользователя по telegram_chat_id."""
    users = _load_users()

    mask = (
        users["telegram_chat_id"].astype(str).str.strip()
        == str(chat_id).strip()
    )
    matched = users.loc[mask]

    if matched.empty:
        return "Пользователь"

    nickname = matched.iloc[0]["nickname"]
    if _is_empty(nickname):
        return "Пользователь"

    return str(nickname).strip()


# ----------------------------------------------------------------------
# Поиск и принадлежность карты
# ----------------------------------------------------------------------

def get_card_row_index(card_name: str) -> int | None:
    """Найти карту глобально по уникальному card_name."""
    df = _load_credit_info()
    card_name = card_name.strip().casefold()
    mask = (
        df["card_name"].fillna("").astype(str).str.strip() == card_name
    )
    matched = df.index[mask]

    if len(matched) == 0:
        return None

    return int(matched[0])


def get_user_card_row_index(chat_id: int, card_name: str) -> int | None:
    """Найти карту только среди карт указанного пользователя."""
    df = _load_credit_info()

    mask = (
        df["telegram_chat_id"].astype(str).str.strip()
        == str(chat_id).strip()
    ) & (
        df["card_name"].fillna("").astype(str).str.strip()
        == card_name.strip()
    )

    matched = df.index[mask]

    if len(matched) == 0:
        return None

    return int(matched[0])


# ----------------------------------------------------------------------
# Создание / удаление карт
# ----------------------------------------------------------------------

def create_empty_card(chat_id: int) -> int:
    """Создать пустую строку новой карты и вернуть её индекс."""
    df = _load_credit_info()

    new_row = {column: "" for column in CARD_FIELDS_LONG}
    new_row["paid"] = False
    new_row["telegram_chat_id"] = chat_id

    df.loc[len(df)] = new_row
    _save_credit_info(df)

    return int(df.index[-1])


def delete_card_row(chat_id: int, row_index: int) -> bool:
    """Удалить строку карты при прерывании заполнения пользователем во время FSM"""
    df = _load_credit_info()

    if row_index not in df.index:
        return False

    row_chat_id = str(df.at[row_index, "telegram_chat_id"]).strip()
    if row_chat_id != str(chat_id).strip():
        return False

    df = df.drop(index=row_index).reset_index(drop=True)
    _save_credit_info(df)
    return True

# Удаление карты из файла принудительно польз-лем
def delete_card(
    chat_id: int,
    card_name: str,
    # file_path: str = CREDIT_INFO_FILE,
) -> bool:
    """Удаляет карту пользователя из CSV.

    Карта определяется одновременно по card_name и telegram_chat_id.

    Возвращает:
        True — карта найдена и удалена.
        False — карта не найдена.
    """

    df = _load_credit_info()

    mask = (
        df["telegram_chat_id"].astype(str).str.strip()
        == str(chat_id).strip()
    ) & (
        df["card_name"].astype(str).str.strip()
        == str(card_name).strip()
    )

    if not mask.any():
        return False

    df = df.loc[~mask].copy() # все, что не совпадает по фильтру, удаляется

    _save_credit_info(df)

    return True

# ----------------------------------------------------------------------
# Изменение полей
# ----------------------------------------------------------------------

def update_card_field(
    chat_id: int,
    row_index: int,
    field: str,
    value,
) -> bool:
    """
    Немедленно изменить поле карты и сохранить CSV.

    telegram_chat_id и updated через эту функцию менять нельзя.
    При фактическом изменении grace_till paid сбрасывается в False.
    """
    editable_fields = {
        field_name
        for field_name in CARD_INFO_NAMES
        if field_name not in {"telegram_chat_id", "updated"}
    }

    if field not in editable_fields:
        return False

    df = _load_credit_info()

    if row_index not in df.index:
        return False

    row_chat_id = str(df.at[row_index, "telegram_chat_id"]).strip()
    if row_chat_id != str(chat_id).strip():
        return False

    if field == "grace_till":
        old_value = df.at[row_index, "grace_till"]

        old_normalized = "" if _is_empty(old_value) else str(old_value).strip()
        new_normalized = "" if _is_empty(value) else str(value).strip()

        if old_normalized != new_normalized:
            df.at[row_index, "grace_till"] = value
            df.at[row_index, "paid"] = False
        # Если значение реально не изменилось, paid сохраняем.
    else:
        df.at[row_index, field] = value

    _save_credit_info(df)
    return True


def update_card_timestamp(chat_id: int, row_index: int) -> bool:
    """Обновить поле updated сегодняшней датой."""
    df = _load_credit_info()

    if row_index not in df.index:
        return False

    row_chat_id = str(df.at[row_index, "telegram_chat_id"]).strip()
    if row_chat_id != str(chat_id).strip():
        return False

    df.at[row_index, "updated"] = date.today().isoformat()
    _save_credit_info(df)
    return True


# ----------------------------------------------------------------------
# Информация о карте
# ----------------------------------------------------------------------

def get_detailed_card_info(chat_id: int, card_name: str) -> str | None:
    """
    Получить подробную информацию о карте.

    chat_id сохраняется в сигнатуре для совместимости с handler'ом.
    Поиск здесь глобальный, потому что один callback card: используется
    и для «Мои карты», и для «Все карты».
    """
    row_index = get_card_row_index(card_name)

    if row_index is None:
        return None

    df = _load_credit_info()
    return _build_card_report(df.loc[row_index])


# ----------------------------------------------------------------------
# Общая сумма долга
# ----------------------------------------------------------------------

def total_debt(chat_id: int) -> float:
    """Посчитать общую сумму долга только текущего пользователя."""
    df = _load_credit_info()

    user_cards = df[
        df["telegram_chat_id"].astype(str).str.strip()
        == str(chat_id).strip()
    ]

    if user_cards.empty:
        return 0.0

    debts = pd.to_numeric(user_cards["debt"], errors="coerce").fillna(0)
    return float(debts.sum())


# ----------------------------------------------------------------------
# Оплата карты
# ----------------------------------------------------------------------

def mark_card_as_paid(chat_id: int, card_name: str) -> bool:
    """Отметить собственную карту как оплаченную."""
    row_index = get_user_card_row_index(chat_id, card_name)

    if row_index is None:
        return False

    df = _load_credit_info()
    df.at[row_index, "paid"] = True
    df.at[row_index, "updated"] = date.today().isoformat()

    _save_credit_info(df)
    return True


# ----------------------------------------------------------------------
# Общий помощник для платежей
# ----------------------------------------------------------------------

def _build_payment_item(row: pd.Series) -> dict | None:
    """Сформировать единый объект платежа для ручного и автоматического вывода."""
    if _is_paid(row["paid"]) or _is_empty(row["pay_until"]):
        return None

    try:
        pay_until_date = pd.to_datetime(
            str(row["pay_until"]).strip(),
            format="%Y-%m-%d",
            errors="raise",
        ).date()
    except (ValueError, TypeError):
        return None

    try:
        chat_id = int(float(row["telegram_chat_id"]))
    except (ValueError, TypeError):
        chat_id = row["telegram_chat_id"]

    nickname = _get_username(chat_id)
    card_name = (
        "—"
        if _is_empty(row["card_name"])
        else str(row["card_name"]).strip()
    )

    text = (
        f"<b>{nickname}</b>\n"
        f"💳 {card_name}\n"
        f"Оплатить до: {_format_date(row['pay_until'])}\n"
        f"Минимальный платеж: {_format_money(row['min_pay'])}\n"
        f"Долг: {_format_money(row['debt'])}"
    )

    return {
        "chat_id": chat_id,
        "nickname": nickname,
        "card_name": card_name,
        "date": pay_until_date,
        "text": text,
    }


def get_payments_for_reminder() -> list[dict]:
    """
    Получить неоплаченные платежи за период сегодня + 2 дня
    по всем картам всех пользователей.
    """
    df = _load_credit_info()

    if df.empty:
        return []

    today = date.today()
    last_day = today + timedelta(days=2)
    payments = []

    for _, row in df.iterrows():
        payment = _build_payment_item(row)

        if payment is None:
            continue

        if payment["date"] < today or payment["date"] > last_day:
            continue

        payments.append(payment)

    payments.sort(key=lambda item: item["date"])
    return payments


def get_all_unpaid_payments() -> list[dict]:
    """
    Получить все будущие неоплаченные платежи по всем пользователям.

    Просроченные платежи не включаются.
    """
    df = _load_credit_info()

    if df.empty:
        return []

    today = date.today()
    payments = []

    for _, row in df.iterrows():
        payment = _build_payment_item(row)

        if payment is None or payment["date"] < today:
            continue

        payments.append(payment)

    payments.sort(key=lambda item: item["date"])
    return payments
