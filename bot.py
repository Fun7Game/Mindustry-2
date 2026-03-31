import logging
import random
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import Update

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# ТОКЕН
TOKEN = "8490172496:AAG9SmhT3xhL3_QrsjE3QOomniwPxEaEYRQ"

# Хранилище игр
user_data = {}

def start(update, context):
    """Команда /start"""
    user_id = update.effective_user.id
    user_data[user_id] = {'secret_number': None}
    update.message.reply_text(
        "🎮 Привет! Я игровой бот!\n\n"
        "Команды:\n"
        "/play - начать игру 'Угадай число'\n"
        "/help - помощь"
    )

def help_command(update, context):
    """Команда /help"""
    update.message.reply_text(
        "Игра 'Угадай число':\n"
        "1. Напиши /play\n"
        "2. Я загадаю число от 1 до 100\n"
        "3. Вводи числа, я буду подсказывать\n\n"
        "Создано на Python + python-telegram-bot"
    )

def play(update, context):
    """Начать игру"""
    user_id = update.effective_user.id
    secret = random.randint(1, 100)
    user_data[user_id] = {'secret_number': secret}
    print(f"User {user_id} started game. Secret: {secret}")
    update.message.reply_text(
        "🎲 Игра началась!\n"
        "Я загадал число от 1 до 100.\n"
        "Попробуй угадай! Вводи числа."
    )

def handle_message(update, context):
    """Обработка попыток угадать"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # Проверяем, есть ли активная игра
    if user_id not in user_data or user_data[user_id].get('secret_number') is None:
        update.message.reply_text("Чтобы начать игру, используй /play")
        return
    
    # Проверяем, что введено число
    if not text.isdigit():
        update.message.reply_text("Введи целое число от 1 до 100!")
        return
    
    guess = int(text)
    secret = user_data[user_id]['secret_number']
    
    # Логика игры
    if guess < 1 or guess > 100:
        update.message.reply_text("Число должно быть от 1 до 100!")
    elif guess < secret:
        update.message.reply_text("📈 Загаданное число БОЛЬШЕ! Попробуй еще.")
    elif guess > secret:
        update.message.reply_text("📉 Загаданное число МЕНЬШЕ! Попробуй еще.")
    else:
        update.message.reply_text(f"🎉 ПОБЕДА! 🎉\nТы угадал число {secret}!\n\nСыграем еще? Напиши /play")
        user_data[user_id]['secret_number'] = None

def main():
    """Запуск бота"""
    print("🚀 Запуск бота на Render.com...")
    
    # Создаем updater
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    
    # Регистрируем команды
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("play", play))
    
    # Регистрируем обработчик сообщений
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    
    # Запускаем
    print("✅ Бот запущен и готов к работе!")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
