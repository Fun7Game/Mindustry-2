import logging
import random
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ТОКЕН - ВАШ ТОКЕН
TOKEN = "8490172496:AAG9SmhT3xhL3_QrsjE3QOomniwPxEaEYRQ"

# Хранилище игр
user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user_id = update.effective_user.id
    user_data[user_id] = {'secret_number': None}
    await update.message.reply_text(
        "🎮 Привет! Я игровой бот!\n\n"
        "Команды:\n"
        "/play - начать игру 'Угадай число'\n"
        "/help - помощь"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    await update.message.reply_text(
        "Игра 'Угадай число':\n"
        "1. Напиши /play\n"
        "2. Я загадаю число от 1 до 100\n"
        "3. Вводи числа, я буду подсказывать\n\n"
        "Создано на Python + python-telegram-bot"
    )

async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать игру"""
    user_id = update.effective_user.id
    secret = random.randint(1, 100)
    user_data[user_id] = {'secret_number': secret}
    logger.info(f"User {user_id} started game. Secret: {secret}")
    await update.message.reply_text(
        "🎲 Игра началась!\n"
        "Я загадал число от 1 до 100.\n"
        "Попробуй угадай! Вводи числа."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка попыток угадать"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # Проверяем, есть ли активная игра
    if user_id not in user_data or user_data[user_id].get('secret_number') is None:
        await update.message.reply_text("Чтобы начать игру, используй /play")
        return
    
    # Проверяем, что введено число
    if not text.isdigit():
        await update.message.reply_text("Введи целое число от 1 до 100!")
        return
    
    guess = int(text)
    secret = user_data[user_id]['secret_number']
    
    # Логика игры
    if guess < 1 or guess > 100:
        await update.message.reply_text("Число должно быть от 1 до 100!")
    elif guess < secret:
        await update.message.reply_text("📈 Загаданное число БОЛЬШЕ! Попробуй еще.")
    elif guess > secret:
        await update.message.reply_text("📉 Загаданное число МЕНЬШЕ! Попробуй еще.")
    else:
        await update.message.reply_text(f"🎉 ПОБЕДА! 🎉\nТы угадал число {secret}!\n\nСыграем еще? Напиши /play")
        user_data[user_id]['secret_number'] = None
        logger.info(f"User {user_id} won the game!")

def main():
    """Запуск бота"""
    print("🚀 Запуск бота на Render.com...")
    
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()
    
    # Регистрируем команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("play", play))
    
    # Регистрируем обработчик сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Запускаем
    print("✅ Бот запущен и готов к работе!")
    application.run_polling()

if __name__ == "__main__":
    main()
