import json
import os
import sqlite3
import requests
import telebot
from dotenv import load_dotenv
from telebot.types import Message, ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime
import schedule
import time
import threading


# Завантаження змінних середовища
load_dotenv()
bot = telebot.TeleBot(os.environ.get('TELEGRAM_TOKEN'))

# Заздалегідь визначені координати для міст
city_coordinates = {
    "Київ": {"lat": 50.4501, "lon": 30.5234},
    "Львів": {"lat": 49.8397, "lon": 24.0297},
    "Одеса": {"lat": 46.4825, "lon": 30.7233},
    "Харків": {"lat": 49.9935, "lon": 36.2304},
    "Дніпро": {"lat": 48.4647, "lon": 35.0462}
}

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(60)
# Обробник команди /start
@bot.message_handler(commands=['start'])
def send_welcome(message: Message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    user_surname = message.from_user.last_name
    conn = None

    try:
        conn = sqlite3.connect("db/database.db")
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            cursor.execute(
                "INSERT INTO users (user_id, user_name, user_surname) VALUES (?, ?, ?)",
                (user_id, user_name, user_surname)
            )
            conn.commit()

        # Створення кнопок
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        buttons = [
            KeyboardButton("Поточна погода"),
            KeyboardButton("Щоденний прогноз"),
            KeyboardButton("Змінити місто"),
            KeyboardButton("Прогноз на кілька днів")
        ]
        keyboard.add(*buttons)

        bot.reply_to(message, "👋 Привіт! Я бот для прогнозів погоди. Виберіть, будь ласка, опцію з меню нижче:", reply_markup=keyboard)

    except Exception as err:
        print("error", err)
        bot.reply_to(message, "Сталася помилка, спробуйте, будь ласка, пізніше!")
    finally:
        if conn:
            conn.close()

def show_city_selection_buttons(message: Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = [
        KeyboardButton("Київ"),
        KeyboardButton("Львів"),
        KeyboardButton("Одеса"),
        KeyboardButton("Харків"),
        KeyboardButton("Дніпро"),
        KeyboardButton("Інше")
    ]
    keyboard.add(*buttons)
    bot.reply_to(message, "Оберіть нове місто з наведених кнопок:", reply_markup=keyboard)

def get_weather_for_existing_city_to_user(user_id, city_name):
    # Отримайте погоду для вказаного міста
    coordinates = city_coordinates.get(city_name)

    if coordinates:
        url = (
            f"https://api.openweathermap.org/data/3.0/onecall"
            f"?lat={coordinates['lat']}&lon={coordinates['lon']}&appid={os.environ.get('OPEN_WEATHER_TOKEN')}&units=metric&lang=uk"
        )

        try:
            response = requests.get(url)
            if response.status_code == 200:
                data = json.loads(response.text)
                weather = data['current']['weather'][0]['description'].capitalize()
                temp = data['current']['temp']
                wind_speed = data['current']['wind_speed']
                date = datetime.now().strftime("%d.%m.%y")

                weather_message = (
                    f"Погода у місті {city_name}: на {date}\n"
                    f"Температура: {temp}°C\n"
                    f"Опис: {weather}\n"
                    f"Швидкість вітру: {wind_speed} км/год"
                )

                # Відправляємо повідомлення користувачу
                bot.send_message(user_id, weather_message)
            else:
                bot.send_message(user_id, "Не вдалося отримати дані про погоду. Спробуйте пізніше.")
        except Exception as err:
            print("Error:", err)
            bot.send_message(user_id, "Сталася помилка, спробуйте пізніше.")

@bot.message_handler(func=lambda message: message.text == "Поточна погода")
def show_current_weather(message: Message):
    user_id = message.from_user.id
    conn = sqlite3.connect("db/database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT city FROM users WHERE user_id = ?", (user_id,))
    city = cursor.fetchone()
    conn.close()

    if city and city[0]:
        city_name = city[0]
        get_weather_for_existing_city_to_user(user_id, city_name)
    else:
        # Показати вибір міста, якщо воно не збережено
        bot.reply_to(message, "У вас ще немає обраного міста. Виберіть місто зараз:")
        show_city_selection_buttons(message)

def get_weather_for_existing_city(message: Message, city_name: str):
    coordinates = city_coordinates[city_name]

    url = (
        f"https://api.openweathermap.org/data/3.0/onecall"
        f"?lat={coordinates['lat']}&lon={coordinates['lon']}&appid={os.environ.get('OPEN_WEATHER_TOKEN')}&units=metric&lang=uk"
    )

    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = json.loads(response.text)
            weather = data['current']['weather'][0]['description'].capitalize()
            temp = data['current']['temp']
            wind_speed = data['current']['wind_speed']
            date = datetime.now().strftime("%d.%m.%y")

            weather_message = (
                f"Погода у місті {city_name}: на {date}\n"
                f"Температура: {temp}°C\n"
                f"Опис: {weather}\n"
                f"Швидкість вітру: {wind_speed} км/год"
            )
            bot.reply_to(message, weather_message)
        else:
            bot.reply_to(message, "Не вдалося отримати дані про погоду. Спробуйте пізніше.")
    except Exception as err:
        print("Error:", err)
        bot.reply_to(message, "Сталася помилка, спробуйте пізніше.")

@bot.message_handler(func=lambda message: message.text in city_coordinates)
def get_weather(message: Message):
    city_name = message.text
    coordinates = city_coordinates[city_name]

    user_id = message.from_user.id
    conn = sqlite3.connect("db/database.db")
    cursor = conn.cursor()

    cursor.execute("UPDATE users SET city = ? WHERE user_id = ?", (city_name, user_id))
    conn.commit()
    conn.close()

    url = (
        f"https://api.openweathermap.org/data/3.0/onecall"
        f"?lat={coordinates['lat']}&lon={coordinates['lon']}&appid={os.environ.get('OPEN_WEATHER_TOKEN')}&units=metric&lang=uk"
    )

    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = json.loads(response.text)
            weather = data['current']['weather'][0]['description'].capitalize()
            temp = data['current']['temp']
            wind_speed = data['current']['wind_speed']
            date = datetime.now().strftime("%d.%m.%y")

            weather_message = (
                f"Погода у місті {city_name}: на {date}\n"
                f"Температура: {temp}°C\n"
                f"Опис: {weather}\n"
                f"Швидкість вітру: {wind_speed} км/год"
            )
            bot.reply_to(message, weather_message)
            keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
            back_button = KeyboardButton("Назад")
            keyboard.add(back_button)
            bot.send_message(message.chat.id, "Щоб повернутись до меню, натисніть кнопку нижче.", reply_markup=keyboard)
        else:
            bot.reply_to(message, "Не вдалося отримати дані про погоду. Спробуйте пізніше.")
    except Exception as err:
        print("Error:", err)
        bot.reply_to(message, "Сталася помилка, спробуйте пізніше.")

@bot.message_handler(func=lambda message: message.text == "Назад")
def back_to_main_menu(message: Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = [
        KeyboardButton("Поточна погода"),
        KeyboardButton("Щоденний прогноз"),
        KeyboardButton("Змінити місто"),
        KeyboardButton("Прогноз на кілька днів"),
    ]
    keyboard.add(*buttons)
    bot.reply_to(message, "Ви повернулися до головного меню. Що ви хочете зробити?", reply_markup=keyboard)

@bot.message_handler(func=lambda message: message.text == "Змінити місто")
def change_city(message: Message):
    user_id = message.from_user.id
    conn = sqlite3.connect("db/database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT city FROM users WHERE user_id = ?", (user_id,))
    city = cursor.fetchone()
    conn.close()

    if city and city[0]:
        bot.reply_to(message, f"Ваше обране місто: {city[0]}. Виберіть нове місто:")
    else:
        bot.reply_to(message, "У вас ще немає обраного міста. Виберіть місто зараз:")
    show_city_selection_buttons(message)

@bot.message_handler(func=lambda message: message.text == "Щоденний прогноз")
def subscribe_daily_forecast(message: Message):
    user_id = message.from_user.id
    conn = sqlite3.connect("db/database.db")
    cursor = conn.cursor()

    # Оновлюємо або додаємо інформацію про бажання отримувати щоденний прогноз
    cursor.execute("UPDATE users SET daily_forecast = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

    bot.reply_to(message, "Ви підписалися на щоденний прогноз. Ви будете отримувати повідомлення о 10:00 ранку кожного дня.")

def send_daily_forecasts():
    conn = sqlite3.connect("db/database.db")
    cursor = conn.cursor()

    # Отримуємо всіх користувачів, які підписалися на щоденний прогноз
    cursor.execute("SELECT user_id, city FROM users WHERE daily_forecast = 1")
    users = cursor.fetchall()
    conn.close()

    for user in users:
        user_id, city_name = user
        # Надсилаємо прогноз для кожного користувача
        get_weather_for_existing_city_to_user(user_id, city_name)

@bot.message_handler(func=lambda message: message.text == "Прогноз на кілька днів")
def show_daily_forecast(message: Message):
    user_id = message.from_user.id
    conn = sqlite3.connect("db/database.db")
    cursor = conn.cursor()

    # Отримуємо збережене місто з бази даних
    cursor.execute("SELECT city FROM users WHERE user_id = ?", (user_id,))
    city = cursor.fetchone()
    conn.close()

    if city and city[0]:
        city_name = city[0]
        get_weather_forecast_for_city(message, city_name)
    else:
        bot.reply_to(message, "У вас ще немає обраного міста. Виберіть місто зараз:")
        show_city_selection_buttons(message)


def get_weather_forecast_for_city(message: Message, city_name: str):
    coordinates = city_coordinates[city_name]

    url = (
        f"https://api.openweathermap.org/data/3.0/onecall"
        f"?lat={coordinates['lat']}&lon={coordinates['lon']}&appid={os.environ.get('OPEN_WEATHER_TOKEN')}&units=metric&exclude=current,minutely,hourly,alerts&lang=uk"
    )

    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = json.loads(response.text)
            daily_forecasts = data['daily']

            forecast_message = f"Прогноз погоди на кілька днів для міста {city_name}:\n\n"
            for day in daily_forecasts[:7]:  # Обираємо перші 7 днів
                date = datetime.fromtimestamp(day['dt']).strftime('%d.%m.%Y')
                temp_day = day['temp']['day']
                weather_description = day['weather'][0]['description'].capitalize()
                forecast_message += f"{date}: Температура: {temp_day}°C, Опис: {weather_description}\n"

            bot.reply_to(message, forecast_message)
        else:
            bot.reply_to(message, "Не вдалося отримати дані про прогноз погоди. Спробуйте пізніше.")
    except Exception as err:
        print("Error:", err)
        bot.reply_to(message, "Сталася помилка, спробуйте пізніше.")

@bot.message_handler(func=lambda message: message.text == "Інше")
def ask_for_city(message: Message):
    bot.reply_to(message, "Введіть назву вашого міста:")

@bot.message_handler(func=lambda message: message.text not in city_coordinates and message.text != "Інше")
def get_weather_for_custom_city(message: Message):
    city_name = message.text

    try:
        resp = requests.get(
            f"http://api.openweathermap.org/geo/1.0/direct?q={city_name}&appid={os.environ.get('OPEN_WEATHER_TOKEN')}"
        )
        if resp.status_code == 200 and len(resp.json()) > 0:
            data = resp.json()[0]
            lat, lon = data['lat'], data['lon']

            url = (
                f"https://api.openweathermap.org/data/3.0/onecall"
                f"?lat={lat}&lon={lon}&appid={os.environ.get('OPEN_WEATHER_TOKEN')}&units=metric&lang=uk"
            )
            response = requests.get(url)
            if response.status_code == 200:
                data = json.loads(response.text)
                weather = data['current']['weather'][0]['description'].capitalize()
                temp = data['current']['temp']
                wind_speed = data['current']['wind_speed']
                date = datetime.now().strftime("%d.%m.%y")

                weather_message = (
                    f"Погода у місті {city_name}: на {date}\n"
                    f"Температура: {temp}°C\n"
                    f"Опис: {weather}\n"
                    f"Швидкість вітру: {wind_speed} км/год"
                )
                bot.reply_to(message, weather_message)
            else:
                bot.reply_to(message, "Не вдалося отримати дані про погоду. Спробуйте пізніше.")
        else:
            bot.reply_to(message, "Не вдалося знайти ваше місто. Перевірте правильність написання.")
    except Exception as err:
        print("Error:", err)
        bot.reply_to(message, "Сталася помилка, спробуйте пізніше.")

scheduler_thread = threading.Thread(target=run_scheduler)
scheduler_thread.start()

bot.infinity_polling()
