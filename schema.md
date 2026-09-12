**notifications schema:**

services/notifications.py/

async def payment_reminder():
    ├── определяет, когда запускать проверку
    ├── get_users() → список пользователей
    ├── get_payments_for_reminder() → общий список уведомлений
    ├── передает все в async def send_payment_reminders() → отправляет каждый текст каждому пользователю
    |
    ├── async def send_payment_reminders()
        ├── получает платежи конкретного пользователя
        ├── формирует текст сообщения
        └── отправляет каждому польз-лю сообщения про каждый платеж с клавиатурой get_paid_keyboard, чтобы сразу помечать как прочитанное

хэндлер check_payments_handler:
    ├── получает команду "Ближайшие платежи"/"check_payments"
    ├── запускает принудительно функцию async def send_payment_reminders()



**Ближайшие платежи:**

get_payments_for_reminder()
    ↓
получает общий список платежей по всем картам


send_payment_messages()
    ↓
отправляет каждый платеж отдельным сообщением с клавиатурой


payment_reminder()
    ↓
запускает отправку автоматически в 10:00