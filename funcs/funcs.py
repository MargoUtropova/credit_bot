import os
from datetime import date, timedelta

import pandas as pd

from lexicon.lexicon import card_info


# ============================================================================
# Поля, доступные для добавления и редактирования карты
# ============================================================================

"""
Поля, которые пользователь проходит последовательно
в FSM при добавлении или редактировании карты.

Формат элемента:

    (
        имя_столбца_в_CSV,
        название_для_пользователя
    )

Порядок полей здесь определяет порядок их показа
в handlers/user.py.

Поле `updated` намеренно отсутствует:
оно обновляется ботом автоматически после завершения формы.

Поле `telegram_chat_id` также отсутствует:
оно никогда не редактируется пользователем.
"""

CARD_FIELDS = [
    ("card_name", "Название карты"),
    ("grace_till", "Грейс-период до"),
    ("check_date", "Дата проверки"),
    ("min_pay", "Минимальный платеж"),
    ("pay_until", "Оплатить до"),
    ("debt", "Долг"),
    ("limit", "Лимит"),
    ("paid", "Статус оплаты"),
]


# ============================================================================
# Вспомогательные функции
# ============================================================================

def _is_paid(value) -> bool:
    """
    Приводит значение поля `paid` из CSV к типу bool.

    После чтения CSV значение может быть:
        True
        False
        "True"
        "False"
        "true"
        "false"
        1
        0

    Функция нужна, чтобы все остальные функции одинаково
    определяли статус оплаты.

    Возвращает:
        True — если карта оплачена;
        False — если карта не оплачена.
    """
    if isinstance(value, bool):
        return value

    if pd.isna(value):
        return False

    value = str(value).strip().lower()

    return value in {
        "true",
        "1",
        "yes",
        "да",
    }


def _format_date(value) -> str:
    """
    Форматирует дату из CSV для отображения пользователю.

    Внутри CSV дата обычно хранится в формате:

        YYYY-MM-DD

    Пользователю показывается:

        DD.MM.YYYY

    Если дата отсутствует или некорректна,
    возвращается символ «—».
    """
    if pd.isna(value) or str(value).strip() == "":
        return "—"

    try:
        return pd.to_datetime(value).strftime("%d.%m.%Y")
    except (ValueError, TypeError):
        return "—"


def _format_number(value) -> str:
    """
    Форматирует числовое значение для отображения пользователю.

    Например:

        45000.0 -> "45000"
        1250.50 -> "1250.5"

    Пустое значение отображается как «—».
    """
    if pd.isna(value) or str(value).strip() == "":
        return "—"

    try:
        number = float(value)

        if number.is_integer():
            return str(int(number))

        return str(number)

    except (ValueError, TypeError):
        return str(value)


def _chat_id_matches(value, chat_id: int) -> bool:
    """
    Проверяет принадлежность строки конкретному пользователю.

    Значение telegram_chat_id после чтения CSV может иметь
    тип int или str, поэтому оба значения приводятся к строке.

    Возвращает True, если ID совпадают.
    """
    return str(value).strip() == str(chat_id).strip()


# ============================================================================
# Работа с пользователями
# ============================================================================

def register_user(
    nickname: str | None,
    chat_id: int,
    file_path: str = r"credit_info/users.csv",
) -> None:
    """
    Регистрирует пользователя в users.csv.

    Если telegram_chat_id уже существует в таблице,
    новая строка не создаётся.

    Параметры:
        nickname:
            Username пользователя Telegram.

        chat_id:
            Telegram ID пользователя.

        file_path:
            Путь к файлу users.csv.
    """
    if os.path.exists(file_path):
        df = pd.read_csv(
            file_path,
            encoding="utf-8",
        )
    else:
        df = pd.DataFrame(
            columns=[
                "nickname",
                "telegram_chat_id",
            ]
        )

    existing_ids = (
        df["telegram_chat_id"]
        .astype(str)
        .tolist()
    )

    if str(chat_id) not in existing_ids:
        new_user = pd.DataFrame(
            [
                {
                    "nickname": nickname,
                    "telegram_chat_id": chat_id,
                }
            ]
        )

        df = pd.concat(
            [df, new_user],
            ignore_index=True,
        )

        df.to_csv(
            file_path,
            index=False,
            encoding="utf-8",
        )


def get_users(
    file_path: str = r"credit_info/users.csv",
) -> list[dict]:
    """
    Возвращает список зарегистрированных пользователей.

    Результат имеет формат:

        [
            {
                "nickname": "...",
                "telegram_chat_id": 123456789
            },
            ...
        ]

    Используется сервисами, которым необходимо
    получить список пользователей бота.
    """
    if not os.path.exists(file_path):
        return []

    df = pd.read_csv(
        file_path,
        encoding="utf-8",
    )

    return df.to_dict(
        orient="records"
    )


# ============================================================================
# Платежи
# ============================================================================

def get_upcoming_payments(
    chat_id: int,
    file_path: str = r"credit_info/credit_info.csv",
) -> str:
    """
    Показывает пользователю все неоплаченные минимальные платежи.

    Выбираются только карты текущего пользователя.

    В отчёт попадают карты, у которых:
        - paid == False;
        - указана дата `pay_until`.

    Формат сообщения:

        Необходимо оплатить:

        Банк: ...
        Сумма платежа: ... руб.
        Оплатить до: DD.MM.YYYY

    Если у пользователя нет неоплаченных платежей,
    возвращается сообщение:

        🎉 Отлично! Все минимальные платежи по картам внесены.

    Если у пользователя вообще нет карт,
    также возвращается сообщение об отсутствии платежей.
    """
    if not os.path.exists(file_path):
        return "❌ Файл с данными карт не найден."

    try:
        df = pd.read_csv(
            file_path,
            encoding="utf-8",
        )

        df = df[
            df["telegram_chat_id"].apply(
                lambda value: _chat_id_matches(value, chat_id)
            )
        ]

        unpaid_cards = []

        for _, row in df.iterrows():
            if _is_paid(row["paid"]):
                continue

            if (
                pd.isna(row["pay_until"])
                or str(row["pay_until"]).strip() == ""
            ):
                continue

            pay_until = _format_date(
                row["pay_until"]
            )

            unpaid_cards.append(
                (
                    f"Банк: {row['card_name']}\n"
                    f"Сумма платежа: "
                    f"{_format_number(row['min_pay'])} руб.\n"
                    f"Оплатить до: "
                    f"<b>{pay_until}</b>\n"
                    f"───────────────────\n"
                )
            )

        if not unpaid_cards:
            return (
                "🎉 Отлично! Все минимальные платежи "
                "по картам внесены."
            )

        return (
            "Необходимо оплатить:\n\n"
            + "".join(unpaid_cards)
        )

    except Exception:
        return "❌ Не удалось получить информацию о платежах."


# ============================================================================
# Информация по карте
# ============================================================================

def get_detailed_card_info(
    chat_id: int,
    card_name_btn: str,
    file_path: str = r"credit_info/credit_info.csv",
) -> str:
    """
    Возвращает подробную информацию по выбранной карте.

    Карта ищется по:
        1. telegram_chat_id пользователя;
        2. названию карты.

    Название карты сравнивается после удаления
    случайных пробелов в начале и конце.

    Порядок отображения полей определяется словарём
    `card_info` из lexicon.py.

    Даты:
        DD.MM.YYYY

    Статус оплаты:
        ✅ Да (Оплачено)
        ❌ Нет (Нужно оплатить)

    Пустые значения:
        —

    Возвращает:
        строку с информацией по карте.
    """
    if not os.path.exists(file_path):
        return "❌ Файл с данными карт не найден."

    try:
        df = pd.read_csv(
            file_path,
            encoding="utf-8",
        )

        df = df[
            df["telegram_chat_id"].apply(
                lambda value: _chat_id_matches(value, chat_id)
            )
        ]

        clean_btn = card_name_btn.strip()

        for _, row in df.iterrows():
            current_label = str(
                row["card_name"]
            ).strip()

            if current_label != clean_btn:
                continue

            result = (
                f"Информация по карте "
                f"{current_label}:\n\n"
            )

            # Порядок вывода определяется card_info.
            for key_column, friendly_name in card_info.items():

                if key_column not in df.columns:
                    continue

                value = row[key_column]

                # Даты.
                if key_column in {
                    "grace_till",
                    "check_date",
                    "pay_until",
                    "updated",
                }:
                    value = _format_date(value)

                # Статус оплаты.
                elif key_column == "paid":
                    if _is_paid(value):
                        value = "✅ Да (Оплачено)"
                    else:
                        value = "❌ Нет (Нужно оплатить)"

                # Числовые значения.
                elif key_column in {
                    "min_pay",
                    "debt",
                    "limit",
                }:
                    value = _format_number(value)

                # Остальные значения.
                elif pd.isna(value) or str(value).strip() == "":
                    value = "—"

                result += (
                    f"{friendly_name}: {value}\n"
                )

            return result

        return (
            f"❌ Карта «{clean_btn}» "
            "не найдена в таблице базы данных."
        )

    except Exception:
        return "❌ Не удалось получить информацию о карте."


# ============================================================================
# Общий долг
# ============================================================================

def total_debt(
    chat_id: int,
    file_path: str = r"credit_info/credit_info.csv",
) -> str:
    """
    Возвращает общую сумму долга пользователя.

    Суммируются значения поля `debt`
    только по картам текущего пользователя.

    Пустые и некорректные значения не учитываются.

    Пример результата:

        Общий долг по всем картам: 125000 рублей
    """
    if not os.path.exists(file_path):
        return "❌ Файл с данными карт не найден."

    try:
        df = pd.read_csv(
            file_path,
            encoding="utf-8",
        )

        df = df[
            df["telegram_chat_id"].apply(
                lambda value: _chat_id_matches(value, chat_id)
            )
        ]

        if df.empty:
            return "Общий долг по всем картам: 0 рублей."

        debt_values = pd.to_numeric(
            df["debt"],
            errors="coerce",
        ).fillna(0)

        total = debt_values.sum()

        if float(total).is_integer():
            total_text = str(int(total))
        else:
            total_text = str(total)

        return (
            f"Общий долг по всем картам: "
            f"{total_text} рублей."
        )

    except Exception:
        return "❌ Не удалось рассчитать общий долг."


# ============================================================================
# Быстрая отметка карты как оплаченной
# ============================================================================

def mark_card_as_paid(
    chat_id: int,
    card_name: str,
    file_path: str = r"credit_info/credit_info.csv",
) -> str:
    """
    Быстро отмечает выбранную карту как оплаченную.

    Используется кнопкой:

        Оплачено

    на экране подробной информации по карте.

    Изменяет:
        paid = True
        updated = текущая дата

    FSM при этом не запускается.

    Возвращает сообщение об успешном изменении
    или об отсутствии карты.
    """
    if not os.path.exists(file_path):
        return "❌ Файл с данными карт не найден."

    try:
        df = pd.read_csv(
            file_path,
            encoding="utf-8",
        )

        mask = (
            df["telegram_chat_id"].apply(
                lambda value: _chat_id_matches(value, chat_id)
            )
            & (
                df["card_name"]
                .astype(str)
                .str.strip()
                == card_name.strip()
            )
        )

        if not mask.any():
            return (
                f"❌ Карта «{card_name}» "
                "не найдена."
            )

        df.loc[mask, "paid"] = True

        df.loc[
            mask,
            "updated",
        ] = date.today().strftime(
            "%d.%m.%Y"
        )

        df.to_csv(
            file_path,
            index=False,
            encoding="utf-8",
        )

        return (
            f"✅ Карта «{card_name}» "
            "отмечена как оплаченная."
        )

    except Exception:
        return (
            "❌ Не удалось изменить "
            "статус оплаты."
        )


# ============================================================================
# Напоминания
# ============================================================================

def get_payments_for_reminder(
    chat_id: int,
    file_path: str = r"credit_info/credit_info.csv",
) -> list[dict]:
    """
    Возвращает карты, по которым минимальный платёж
    необходимо внести через 2 дня.

    Выбираются только карты текущего пользователя.

    Игнорируются:
        - уже оплаченные карты;
        - карты без даты `pay_until`.

    Формат результата:

        [
            {
                "card_name": "Т-Банк 1234",
                "min_pay": 5000,
                "pay_until": "12.09.2026"
            },
            ...
        ]

    Функция используется сервисом уведомлений.
    """
    if not os.path.exists(file_path):
        return []

    df = pd.read_csv(
        file_path,
        encoding="utf-8",
    )

    df = df[
        df["telegram_chat_id"].apply(
            lambda value: _chat_id_matches(value, chat_id)
        )
    ]

    today = date.today()
    reminder_date = today + timedelta(days=2)

    reminders = []

    for _, row in df.iterrows():

        # Оплаченные карты не напоминаем.
        if _is_paid(row["paid"]):
            continue

        # Карты без даты платежа пропускаем.
        if (
            pd.isna(row["pay_until"])
            or str(row["pay_until"]).strip() == ""
        ):
            continue

        try:
            pay_until = pd.to_datetime(
                row["pay_until"]
            ).date()
        except (ValueError, TypeError):
            continue

        if pay_until != reminder_date:
            continue

        reminders.append(
            {
                "card_name": str(
                    row["card_name"]
                ).strip(),
                "min_pay": row["min_pay"],
                "pay_until": pay_until.strftime(
                    "%d.%m.%Y"
                ),
            }
        )

    return reminders


# ============================================================================
# Создание новой карты
# ============================================================================

def create_empty_card(
    chat_id: int,
    file_path: str = r"credit_info/credit_info.csv",
) -> int:
    """
    Создаёт пустую строку новой карты.

    Строка создаётся сразу после команды /add_card.
    Затем её индекс сохраняется в FSM.

    Начальные значения:

        card_name = ""
        grace_till = ""
        check_date = ""
        min_pay = ""
        pay_until = ""
        debt = ""
        limit = ""
        updated = ""
        paid = False
        telegram_chat_id = chat_id

    Возвращает:
        индекс созданной строки.

    Если пользователь отменит добавление карты,
    handlers/user.py удалит эту строку через
    delete_card_row().
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(
            f"Файл не найден: {file_path}"
        )

    df = pd.read_csv(
        file_path,
        encoding="utf-8",
    )

    new_card = {
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

    df = pd.concat(
        [
            df,
            pd.DataFrame([new_card]),
        ],
        ignore_index=True,
    )

    df.to_csv(
        file_path,
        index=False,
        encoding="utf-8",
    )

    return int(df.index[-1])


# ============================================================================
# Поиск строки карты
# ============================================================================

def get_card_row_index(
    chat_id: int,
    card_name: str,
    file_path: str = r"credit_info/credit_info.csv",
) -> int | None:
    """
    Возвращает индекс строки выбранной карты.

    Карта ищется одновременно по:

        telegram_chat_id
        card_name

    Название карты сравнивается после удаления
    пробелов в начале и конце.

    Индекс строки используется в FSM редактирования.

    Это важно, потому что `card_name` можно изменить.
    После того как карта найдена, FSM работает именно
    с row_index, а не повторно ищет карту по названию.

    Возвращает:
        int — индекс найденной строки;
        None — если карта не найдена.
    """
    if not os.path.exists(file_path):
        return None

    df = pd.read_csv(
        file_path,
        encoding="utf-8",
    )

    mask = (
        df["telegram_chat_id"].apply(
            lambda value: _chat_id_matches(value, chat_id)
        )
        & (
            df["card_name"]
            .astype(str)
            .str.strip()
            == card_name.strip()
        )
    )

    indexes = df.index[mask].tolist()

    if not indexes:
        return None

    return int(indexes[0])


# ============================================================================
# Изменение одного поля карты
# ============================================================================

def update_card_field(
    chat_id: int,
    row_index: int,
    field: str,
    value,
    file_path: str = r"credit_info/credit_info.csv",
) -> bool:
    """
    Изменяет одно разрешённое поле конкретной карты.

    Разрешённые поля:

        card_name
        grace_till
        check_date
        min_pay
        pay_until
        debt
        limit
        paid

    Поля `updated` и `telegram_chat_id`
    через эту функцию изменить нельзя.

    Проверяется:
        1. существует ли указанная строка;
        2. принадлежит ли она текущему пользователю;
        3. разрешено ли изменение указанного поля.

    Особое правило:

        Если изменяется `grace_till`,
        автоматически устанавливается:

            paid = False

    При этом простое нажатие «Далее» на поле `grace_till`
    не вызывает эту функцию и поэтому не сбрасывает оплату.

    Возвращает:
        True — если изменение успешно сохранено;
        False — если изменить поле не удалось.
    """
    allowed_fields = {
        "card_name",
        "grace_till",
        "check_date",
        "min_pay",
        "pay_until",
        "debt",
        "limit",
        "paid",
    }

    if field not in allowed_fields:
        return False

    if not os.path.exists(file_path):
        return False

    df = pd.read_csv(
        file_path,
        encoding="utf-8",
    )

    if row_index not in df.index:
        return False

    # Проверяем принадлежность строки пользователю.
    if not _chat_id_matches(
        df.loc[row_index, "telegram_chat_id"],
        chat_id,
    ):
        return False

    # Изменяем выбранное поле.
    df.loc[row_index, field] = value

    # Если изменён грейс-период,
    # текущий статус оплаты сбрасывается.
    if field == "grace_till":
        df.loc[row_index, "paid"] = False

    df.to_csv(
        file_path,
        index=False,
        encoding="utf-8",
    )

    return True


# ============================================================================
# Обновление даты изменения
# ============================================================================

def update_card_timestamp(
    chat_id: int,
    row_index: int,
    file_path: str = r"credit_info/credit_info.csv",
) -> bool:
    """
    Обновляет поле `updated` текущей датой.

    Формат даты:

        DD.MM.YYYY

    Поле обновляется автоматически после полного завершения
    FSM добавления или редактирования карты.

    Пользователь не вводит это значение вручную.

    Возвращает:
        True — если дата успешно обновлена;
        False — если строка не найдена или не принадлежит
        пользователю.
    """
    if not os.path.exists(file_path):
        return False

    df = pd.read_csv(
        file_path,
        encoding="utf-8",
    )

    if row_index not in df.index:
        return False

    if not _chat_id_matches(
        df.loc[row_index, "telegram_chat_id"],
        chat_id,
    ):
        return False

    df.loc[
        row_index,
        "updated",
    ] = date.today().strftime(
        "%d.%m.%Y"
    )

    df.to_csv(
        file_path,
        index=False,
        encoding="utf-8",
    )

    return True


# ============================================================================
# Удаление незавершённой карты
# ============================================================================

def delete_card_row(
    chat_id: int,
    row_index: int,
    file_path: str = r"credit_info/credit_info.csv",
) -> bool:
    """
    Удаляет строку карты из CSV.

    Используется при отмене операции добавления новой карты.

    Перед удалением проверяется:
        1. существует ли строка;
        2. принадлежит ли она текущему пользователю.

    При редактировании существующей карты эта функция
    не вызывается.

    Возвращает:
        True — если строка успешно удалена;
        False — если удалить её не удалось.
    """
    if not os.path.exists(file_path):
        return False

    df = pd.read_csv(
        file_path,
        encoding="utf-8",
    )

    if row_index not in df.index:
        return False

    # Проверяем, что строка принадлежит пользователю.
    if not _chat_id_matches(
        df.loc[row_index, "telegram_chat_id"],
        chat_id,
    ):
        return False

    df = df.drop(
        index=row_index
    )

    df.to_csv(
        file_path,
        index=False,
        encoding="utf-8",
    )

    return True
