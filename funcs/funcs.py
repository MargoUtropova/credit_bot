import pandas as pd
import traceback
from datetime import date
from lexicon.lexicon import card_info

def get_upcoming_payments(file_path: str = r"credit_info\credit_info.csv") -> str:
    """Ищет карты, которые еще не оплачены (paid == False)."""
    try:
        df = pd.read_csv(file_path, encoding="utf-8")

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

def get_detailed_card_info(card_name_btn: str, file_path: str = r"credit_info\credit_info.csv") -> str:
    """Ищет карту по названию кнопки и выдает столбиком всю информацию по словарю card_info."""
    try:
        df = pd.read_csv(file_path, encoding="utf-8")
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


def total_debt(file_path: str = r"credit_info\credit_info.csv") -> str:
    """ возвращает общую сумму долга по всем картам из поля debt"""
    file = pd.read_csv(file_path, encoding='utf-8')
    return f"общий долг по всем картам: {sum(file['debt'])} рублей"


def mark_card_as_paid(
    card_name: str,
    file_path: str = r"credit_info\credit_info.csv"
) -> str:
    """Ставит True в колонке paid для выбранной карты."""

    df = pd.read_csv(file_path, encoding="utf-8")

    mask = df["card_name"].astype(str).str.strip() == card_name.strip()

    if not mask.any():
        return f"❌ Карта «{card_name}» не найдена."

    # Меняем статус оплаты
    df.loc[mask, "paid"] = True

    # Обновляем дату изменения
    df.loc[mask, "updated"] = date.today().strftime("%d.%m.%Y")
    # Сохраняем таблицу
    df.to_csv(file_path, index=False, encoding="utf-8")

    return f"✅ Карта «{card_name}» отмечена как оплаченная."
