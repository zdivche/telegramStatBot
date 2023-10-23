import sqlite3
from telebot import *
import matplotlib.pyplot as plt
import os

conn = sqlite3.connect('bot.db', check_same_thread=False)
cursor = conn.cursor()

bot = telebot.TeleBot('6854915233:AAHTFl1xjfpzMNgTCDo6VyjEsUpO0r3s8jg')

keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
button1 = types.KeyboardButton("Добавить расход")
button2 = types.KeyboardButton("Вывести отчет")
button3 = types.KeyboardButton("Помощь")
button4 = types.KeyboardButton("Очистить отчет")
keyboard.add(button1, button2, button3, button4)


@bot.message_handler(func=lambda message: message.text == "Очистить отчет")
def clear_report(message):
    user_id = message.from_user.id

    # Функция для очистки отчета
    def clear_expense_report(user_id):
        cursor.execute('DELETE FROM user_expenses WHERE id=?', (user_id,))
        conn.commit()

    clear_expense_report(user_id)  # Вызываем функцию для очистки отчета

    bot.send_message(user_id, "Отчет очищен.")
def plot_expenses_pie_chart(user_id):
    if os.path.exists('expense_pie_chart.png'):
        os.remove('expense_pie_chart.png')

    cursor.execute('SELECT expenses, descr_exp FROM user_expenses WHERE id=?', (user_id,))
    expenses = cursor.fetchall()

    if not expenses:
        return 'У вас нет записей о расходах.'

    expense_labels = [expense[1] for expense in expenses]
    expense_values = [expense[0] for expense in expenses]

    plt.figure(figsize=(8, 8))
    plt.pie(expense_values, labels=expense_labels, autopct='%1.1f%%')
    plt.title('Структура расходов')
    plt.axis('equal')

    # Сохраните диаграмму как изображение
    plt.savefig('expense_pie_chart.png')

def check_user(user_id: int):
    cursor.execute('SELECT EXISTS(SELECT 1 FROM user WHERE user_id = ?)', (user_id,))
    result = cursor.fetchone()

    if result[0] == 1:
        return True
    else:
        return False

def add_user_in_db(user_id: int, username: str):
    if not check_user(user_id):
        cursor.execute('INSERT INTO user (user_id, username) VALUES (?, ?)', (user_id, username))
        conn.commit()
    else:
        print('пользователь уже есть в базе')


def add_expenses(user_id, expense, descr_exp):
    if check_user(user_id):
        username = get_username(user_id)
        cursor.execute('INSERT INTO user_expenses (id, username, expenses, descr_exp) VALUES (?, ?, ?, ?)',
                       (user_id, username, expense, descr_exp))
        conn.commit()
    else:
        print("Пользователя с таким ID не существует")


def get_username(user_id):
    cursor.execute('SELECT username FROM user WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    if result:
        return result[0]
    else:
        return None


def get_expenses_report(user_id):
    cursor.execute('SELECT username, expenses, descr_exp FROM user_expenses WHERE id=?', (user_id,))
    expenses = cursor.fetchall()

    if not expenses:
        return 'У вас нет записей о расходах.'

    total_sum = 0
    report = f'Отчет о расходах пользователя {expenses[0][0]}:\n\n'  # Выводим имя пользователя

    for expense in expenses:
        username, amount, description = expense
        report += f'{description} - {amount} рублей\n'
        total_sum += amount

    report += f'\nОбщая сумма: {total_sum} рублей'

    return report


@bot.message_handler(func=lambda message: message.text == "Вывести отчет")
def handle_show_report(message):
    user_id = message.from_user.id
    plot_expenses_pie_chart(user_id)  # Создайте диаграмму
    report = get_expenses_report(user_id)

    # Проверяем наличие файла перед отправкой
    if os.path.exists('expense_pie_chart.png'):
        bot.send_photo(message.chat.id, open('expense_pie_chart.png', 'rb'))
    else:
        bot.send_message(message.chat.id, "Извините, но отчет пока не доступен.")
    bot.send_message(message.chat.id, report)


@bot.message_handler(commands=['start'])
def add_user(message):
    user_id = message.from_user.id
    username = message.from_user.username
    add_user_in_db(user_id, username)
    bot.send_message(user_id, 'Давай начнем следить за твоими расходами.\nВыберите опцию из меню:',
                     reply_markup=keyboard)

@bot.message_handler(func=lambda message: message.text == "Помощь")
def handle_help(message):
    user_id = message.from_user.id
    bot.send_message(user_id, 'Этот бот поможет вам учитывать ваши расходы.\n'
                             'Чтобы начать, выберите "Добавить расход" и введите сумму и описание расхода.\n'
                             'Для получения отчета, выберите "Вывести отчет".\n'
                             'Если у вас возникли вопросы, выберите "Помощь".')
@bot.message_handler(func=lambda message: message.text == "Добавить расход")
def handle_add_expense(message):
    user_id = message.from_user.id
    user_states[user_id] = {"state": "waiting_for_amount"}
    bot.send_message(user_id, "Введите сумму расхода:")


@bot.message_handler(
    func=lambda message: user_states.get(message.from_user.id, {}).get("state") == "waiting_for_amount")
def handle_amount(message):
    user_id = message.from_user.id
    try:
        amount = float(message.text)
        states[user_id] = {"amount": amount}
        user_states[user_id]["state"] = "waiting_for_description"
        bot.send_message(user_id, "Введите описание расхода:")
    except ValueError:
        bot.send_message(user_id, "Сумма должна быть числом. Попробуйте снова:")


@bot.message_handler(
    func=lambda message: user_states.get(message.from_user.id, {}).get("state") == "waiting_for_description")
def handle_description(message):
    user_id = message.from_user.id
    description = message.text
    amount = states[user_id]["amount"]
    add_expenses(user_id, amount, description)
    bot.send_message(user_id, f'Расход "{description}" на сумму {amount} рублей добавлен.')
    user_states[user_id] = {}


@bot.message_handler(commands=['report'])
def send_expenses(message):
    user_id = message.from_user.id
    report = get_expenses_report(user_id)
    bot.send_message(user_id, report)


@bot.message_handler(commands=['help'])
def help(message):
    bot.send_message(message.chat.id, 'Чтобы начать пользоваться - /start\n'
                                      'Добавить трату- /add_expense\n'
                                      'Сформировать отчет - /report\n')

@bot.message_handler(func=lambda message: True)
def handle_other_messages(message):
    user_id = message.from_user.id
    bot.send_message(user_id, 'Извините, не могу понять ваш запрос. Выберите опцию из меню или воспользуйтесь командой /help для получения справки.')


states = {}
user_states = {}
bot.polling(none_stop=True)


