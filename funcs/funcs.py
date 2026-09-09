import pandas as pd
import traceback
from datetime import date, timedelta
from lexicon.lexicon import card_info

def get_upcoming_payments(chat_id:int, file_path: str = r"credit_info\credit_info.csv") -> str:
    """Ищет карты, которые еще не оплачены (paid == False)."""
    try:
        df = pd.read_csv(file_path, encoding="utf-8")
        df = df[df['telegram_chat_id']==chat_id]
        result = "Необходимо оплатить:\n\n"
        for _, row in df.iterrows():
            if row['paid'] == False:
                result += f"Банк: {row['card_name']}\n"
                result += f"Сумма платежа: {row['min_pay']} руб.\n"
                result += f"Оплатить до: {pd.to_datetime(row['pay_until']).strftime('%d.%m.%Y')}\n"
                result += "───────────────────\n"
        if all(df['paid']) == True:
            result = "🎉 Отлично! Все минимальные платежи по картам внесены."
        return result
    except Exception as e:
        # Возвращаем стандартную ошибку питона и стек вызовов в чат
        error_msg = traceback.format_exc()
        return f"❌ Ошибка Python при чтении платежей:\n```python\n{error_msg}\n```"

def get_detailed_card_info(chat_id:int, card_name_btn: str, file_path: str = r"credit_info\credit_info.csv") -> str:
    """Ищет карту по названию кнопки и выдает столбиком всю информацию по словарю card_info."""
    try:
        df = pd.read_csv(file_path, encoding="utf-8")
        df = df[df['telegram_chat_id']==chat_id]
        clean_btn = card_name_btn.strip() # Очищаем случайные пробелы кнопки

        for _, row in df.iterrows():
            current_label = str(row['card_name']).strip()

            if current_label == clean_btn:
                result = f"Информация по карте {current_label}:\n\n"

                # Выводим строго в том порядке, который задан в словаре card_info в lexicon.py
                for key_column, friendly_name in card_info.items():
                    if key_column in df.columns:
                        val = row[key_column]
                        # Красивый формат для дат
                        if key_column in ['grace_till', 'check_date', 'pay_until', 'updated'] :
                            if pd.notna(val):
                                val = pd.to_datetime(val).strftime("%d.%m.%Y")
                            else:
                                val = "—"
                        # Форматируем отображение статуса оплаты
                        if key_column == 'paid':
                            if val == True:
                                val = "✅ Да (Оплачено)"
                            else:
                                val = "❌ Нет (Нужно оплатить)"

                        result += f"{friendly_name}: {val}\n"
                return result

        return f"❌ Карта '{clean_btn}' не найдена в таблице базы данных."
    except Exception as e:
        error_msg = traceback.format_exc()
        return f"❌ Ошибка Python при поиске карты:\n```python\n{error_msg}\n```"


def total_debt(chat_id:int, file_path: str = r"credit_info\credit_info.csv") -> str:
    """ возвращает общую сумму долга по всем картам из поля debt"""
    df = pd.read_csv(file_path, encoding='utf-8')
    df = df[df['telegram_chat_id']==chat_id]
    return f"общий долг по всем картам: {sum(df['debt'])} рублей"


def mark_card_as_paid(
    chat_id:int,
    card_name: str,
    file_path: str = r"credit_info\credit_info.csv"
) -> str:
    """Ставит True в колонке paid для выбранной карты."""

    df = pd.read_csv(file_path, encoding="utf-8")
     # Исправлено: добавил скобки вокруг всего условия
    mask = (df['telegram_chat_id'] == chat_id) & (df['card_name'] == card_name)

    if mask.any():  # проверяем, найдена ли карта
        # Обновляем значения напрямую через .loc
        df.loc[mask, 'paid'] = True
        df.loc[mask, 'updated'] = date.today().strftime("%d.%m.%Y")

        # Сохраняем таблицу
        df.to_csv(file_path, index=False, encoding="utf-8")
        return f"✅ Карта «{card_name}» отмечена как оплаченная."
    else:
        return f"❌ Карта «{card_name}» не найдена."



def get_payments_for_reminder(
    chat_id:int,
    file_path: str = r"credit_info\credit_info.csv") -> list[dict]:
    """
    Принимает путь к CSV-файлу.
    Возвращает list[dict] список карт, по которым платеж через 2 дня.
    Игнорирует оплаченные карты и карты без даты платежа.
    """
    df = pd.read_csv(file_path, encoding="utf-8")
    df = df[df['telegram_chat_id']==chat_id]
    today = date.today()
    reminder_date = today + timedelta(days=2)

    reminders = []

    for _, row in df.iterrows():

        if str(row["paid"]).strip().lower() == "true":
            continue

        if pd.isna(row["pay_until"]):
            continue

        pay_until = pd.to_datetime(row["pay_until"]).date()

        if pay_until == reminder_date:
            reminders.append({
                "card_name": row["card_name"],
                "min_pay": row["min_pay"],
                "pay_until": pay_until.strftime("%d.%m.%Y")
            })

    return reminders
