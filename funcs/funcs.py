import os
from datetime import date

import pandas as pd
import traceback
from lexicon.lexicon import (CARD_FIELDS_LONG, CARD_FIELDS_NAMES,
                               CARD_FIELDS_SHORT, USERS_COLUMNS)
CREDIT_INFO_FILE = r"credit_info/credit_info.csv"
USERS_FILE = r"credit_info/users.csv"

# ----------------------------------------------------------------------
# Работа с credit_info.csv
# ----------------------------------------------------------------------

def _load_credit_info() -> pd.DataFrame:
    """Загрузить credit_info.csv и привести его к ожидаемой структуре."""

    if not os.path.exists(CREDIT_INFO_FILE):
        return pd.DataFrame(columns=CARD_FIELDS_NAMES.keys())

    df = pd.read_csv(CREDIT_INFO_FILE, encoding="utf-8")

    # Если каких-то колонок нет — создаём их.
    for column in CARD_FIELDS_NAMES:
        if column not in df.columns:
            df[column] = ""

    # Оставляем колонки в согласованном порядке.
    return df[CARD_FIELDS_LONG]


def _save_credit_info(df: pd.DataFrame) -> None:
    """Сохранить таблицу кредитных карт."""

    os.makedirs(os.path.dirname(CREDIT_INFO_FILE), exist_ok=True)
    df.to_csv(
        CREDIT_INFO_FILE,
        index=False,
        encoding="utf-8",
    )


# ----------------------------------------------------------------------
# Работа с users.csv
# ----------------------------------------------------------------------

def _load_users() -> pd.DataFrame:
    """Загрузить users.csv и привести его к ожидаемой структуре."""

    if not os.path.exists(USERS_FILE):
        return pd.DataFrame(columns=USERS_COLUMNS)

    df = pd.read_csv(USERS_FILE, encoding="utf-8")

    for column in USERS_COLUMNS:
        if column not in df.columns:
            df[column] = ""

    # ВАЖНО: nickname идёт первым, telegram_chat_id вторым.
    return df[USERS_COLUMNS]


def _save_users(df: pd.DataFrame) -> None:
    """Сохранить таблицу пользователей."""

    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    df.to_csv(
        USERS_FILE,
        index=False,
        encoding="utf-8",
    )


# ----------------------------------------------------------------------
# Вспомогательные функции
# ----------------------------------------------------------------------

def _is_empty(value) -> bool:
    """Проверить, является ли значение пустым."""

    return pd.isna(value) or str(value).strip() == ""


def _format_date(value) -> str:
    """Привести дату к формату ДД.ММ.ГГГГ."""

    if _is_empty(value):
        return "—"

    try:
        parsed_date = pd.to_datetime(
            str(value).strip(),
            format="%Y-%m-%d",
            errors="raise",
        )
        return parsed_date.strftime("%d.%m.%Y")

    except (ValueError, TypeError):
        return str(value).strip()


def _format_money(value) -> str:
    """Привести денежное значение к читаемому виду."""

    if _is_empty(value):
        return "—"

    try:
        number = float(value)

        if number.is_integer():
            return f"{int(number):,}".replace(",", " ")

        return f"{number:,.2f}".replace(",", " ").replace(".", ",")

    except (ValueError, TypeError):
        return str(value).strip()


# ----------------------------------------------------------------------
# Пользователи
# ----------------------------------------------------------------------

def register_user(nickname: str, chat_id: int) -> None:
    """
    Зарегистрировать пользователя.

    Если telegram_chat_id уже существует, обновляем nickname.
    """

    users = _load_users()

    chat_id_str = str(chat_id)

    mask = (
        users["telegram_chat_id"]
        .astype(str)
        .str.strip()
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
    """
    Получить telegram_chat_id всех зарегистрированных пользователей.

    Используется для глобальной рассылки уведомлений.
    """

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
    """
    Найти nickname пользователя по telegram_chat_id.

    Если пользователь не найден, возвращается запасное значение.
    """

    users = _load_users()

    mask = (
        users["telegram_chat_id"]
        .astype(str)
        .str.strip()
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
# Создание / удаление карт
# ----------------------------------------------------------------------

def create_empty_card(chat_id: int) -> int:
    """
    Немедленно создать пустую строку новой карты.

    Возвращает индекс созданной строки.

    Это нужно для FSM: если добавление будет прервано,
    строку можно будет полностью удалить.
    """

    df = _load_credit_info()

    new_row = {
        "grace_till": "",
        "check_date": "",
        "min_pay": "",
        "pay_until": "",
        "debt": "",
        "limit": "",
        "updated": "",
        "paid": False,
        "card_name": "",
        "telegram_chat_id": chat_id,
    }

    df.loc[len(df)] = new_row

    _save_credit_info(df)

    return df.index[-1]


def delete_card_row(chat_id: int, row_index: int) -> bool:
    """
    Удалить строку карты.

    Удаление разрешено только если строка принадлежит текущему пользователю.
    """

    df = _load_credit_info()

    if row_index not in df.index:
        return False

    row_chat_id = str(df.at[row_index, "telegram_chat_id"]).strip()

    if row_chat_id != str(chat_id).strip():
        return False

    df = df.drop(index=row_index).reset_index(drop=True)

    _save_credit_info(df)

    return True


# ----------------------------------------------------------------------
# Поиск карт
# ----------------------------------------------------------------------

def get_card_row_index(card_name: str):
    """
    Найти индекс запрошеной карты .
    """

    df = _load_credit_info()

    mask = (
        df["card_name"].fillna("").astype(str).str.strip() == card_name.strip()
    )

    matched = df.index[mask]

    if len(matched) == 0:
        return None

    return matched[0]


# ----------------------------------------------------------------------
# Изменение полей карты
# ----------------------------------------------------------------------

def update_card_field(
    chat_id: int,
    row_index: int,
    field: str,
    value,
) -> bool:
    """
    Немедленно изменить поле карты и сохранить CSV.

    telegram_chat_id изменить через эту функцию нельзя.

    При фактическом изменении grace_till автоматически устанавливается
    paid=False.
    """

    allowed_fields = {field_name for field_name, _ in CARD_FIELDS_NAMES.items()}

    if field not in allowed_fields:
        return False

    df = _load_credit_info()

    if row_index not in df.index:
        return False

    # Проверяем владельца карты.
    row_chat_id = str(df.at[row_index, "telegram_chat_id"]).strip()

    if row_chat_id != str(chat_id).strip():
        return False

    # Для grace_till проверяем, действительно ли значение изменилось.
    if field == "grace_till":
        old_value = df.at[row_index, "grace_till"]

        old_empty = _is_empty(old_value)
        new_empty = _is_empty(value)

        old_normalized = "" if old_empty else str(old_value).strip()
        new_normalized = "" if new_empty else str(value).strip()

        if old_normalized != new_normalized:
            df.at[row_index, "grace_till"] = value

            # Изменение грейс-периода означает, что старый статус оплаты
            # больше нельзя считать актуальным.
            df.at[row_index, "paid"] = False

        _save_credit_info(df)
        return True

    df.at[row_index, field] = value

    _save_credit_info(df)

    return True


def update_card_timestamp(chat_id: int, row_index: int) -> bool:
    """
    Обновить поле updated сегодняшней датой.

    Это поле пользователь вручную не редактирует.
    """

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
# Формирование информации о карте
# ----------------------------------------------------------------------

def _build_card_report(row: pd.Series) -> str:
    """
    Сформировать подробную информацию о карте.

    Первая строка — nickname владельца.
    """

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

    grace_till = _format_date(row["grace_till"])
    check_date = _format_date(row["check_date"])
    pay_until = _format_date(row["pay_until"])

    min_pay = _format_money(row["min_pay"])
    debt = _format_money(row["debt"])
    limit = _format_money(row["limit"])

    paid = row["paid"]

    if isinstance(paid, str):
        paid_normalized = paid.strip().lower()

        is_paid = paid_normalized in {
            "true",
            "1",
            "yes",
            "да",
            "оплачено",
        }
    else:
        is_paid = bool(paid)

    paid_text = "✅ Оплачено" if is_paid else "❌ Не оплачено"

    return (
        f"<b>{nickname}</b>\n\n"
        f"💳 <b>{card_name}</b>\n\n"
        f"Грейс-период: {grace_till}\n"
        f"Дата выписки: {check_date}\n"
        f"Минимальный платеж: {min_pay}\n"
        f"Оплатить до: {pay_until}\n"
        f"Долг: {debt}\n"
        f"Кредитный лимит: {limit}\n"
        f"Статус: {paid_text}"
    )


def get_detailed_card_info(chat_id: int, card_name: str):
    """
    Получить подробную информацию о карте.
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
    """
    Посчитать общую сумму долга только текущего пользователя.
    """

    df = _load_credit_info()

    user_cards = df[
        df["telegram_chat_id"]
        .astype(str)
        .str.strip()
        == str(chat_id).strip()
    ]

    if user_cards.empty:
        return 0.0

    debts = pd.to_numeric(
        user_cards["debt"],
        errors="coerce",
    ).fillna(0)

    return float(debts.sum())


# ----------------------------------------------------------------------
# Оплата карты
# ----------------------------------------------------------------------

def mark_card_as_paid(chat_id: int, card_name: str) -> bool:
    """
    Отметить собственную карту как оплаченную.
    """

    row_index = get_card_row_index(card_name)

    if row_index is None:
        return False

    df = _load_credit_info()

    df.at[row_index, "paid"] = True
    df.at[row_index, "updated"] = date.today().isoformat()

    _save_credit_info(df)

    return True


# ----------------------------------------------------------------------
# Ближайшие платежи
# ----------------------------------------------------------------------

def get_payments_for_reminder() -> list[dict]:
    """
    Получить ближайшие неоплаченные платежи по всем картам за период сегодня +2 дня.

    В результат намеренно не входит фильтр по telegram_chat_id.
    Платежи сортируются по дате pay_until.
    В начале каждого уведомления указывается username владельца.
    """


def get_all_unpaid_payments() -> list[dict]:
    """
    Получить все неоплаченные платежи по всем картам всех пользователей.
    В результат входят все карты, у которых:
        - paid == False;
        - указана корректная дата pay_until.
    Ограничения по дате нет. Платежи сортируются по дате pay_until.
    В начале каждого уведомления указывается username владельца.
    """
    df = _load_credit_info()

    if df.empty:
        return []

    today = date.today()
    payments = []

    for _, row in df.iterrows():

        # Поле paid всегда логического типа True/False.
        if row["paid"] == True:
            continue
        # если уже оплачено или не указана дата платежа, то пропускаем
        if _is_empty(row["pay_until"]):
            continue

        try:
            pay_until_date = pd.to_datetime(
                str(row["pay_until"]).strip(),
                format="%Y-%m-%d",
                errors="raise",
            ).date()
        except (ValueError, TypeError):
            continue

        # Просроченные платежи не включаем.
        if pay_until_date < today:
            continue

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

        payments.append(
            {
                "chat_id": chat_id,
                "nickname": nickname,
                "card_name": card_name,
                "date": pay_until_date,
                "text": (
                    f"<b>{nickname}</b>\n"
                    f"💳 {card_name}\n"
                    f"Оплатить до: "
                    f"{_format_date(row['pay_until'])}\n"
                    f"Минимальный платеж: "
                    f"{_format_money(row['min_pay'])}\n"
                    f"Долг: "
                    f"{_format_money(row['debt'])}"
                ),
            }
        )

    payments.sort(key=lambda item: item["date"])

    return payments
