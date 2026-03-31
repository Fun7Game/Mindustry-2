import logging
import random
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Включим логирование, чтобы видеть ошибки
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- Состояния игры (простая база данных в памяти) ---
# В реальном проекте лучше использовать базу данных (SQLite, Redis),
# но для начала сойдет и словарь.
user_data = {}

# --- Команда /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # Инициализируем нового игрока
    user_data[user_id] = {'secret_number': None, 'attempts': 0}
    await update.message.reply_text(
        "Привет! Давай сыграем в 'Угадай число'? 🎲\n"
        "Я загадал число от 1 до 100.\n"
        "Используй команду /play, чтобы начать новую игру, или просто вводи числа."
    )

# --- Команда /play (начало игры) ---
async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # Генерируем случайное число
    secret = random.randint(1, 100)
    # Сохраняем данные для пользователя
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]['secret_number'] = secret
    user_data[user_id]['attempts'] = 0
    
    await update.message.reply_text("Игра началась! Я загадал число от 1 до 100. Попробуй угадать!")

# --- Обработка текстовых сообщений (попыток угадать) ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    # Проверяем, есть ли активная игра у пользователя
    if user_id not in user_data or user_data[user_id].get('secret_number') is None:
        await update.message.reply_text("Чтобы начать игру, используй команду /play.")
        return
    
    # Проверяем, является ли ввод числом
    if not text.isdigit():
        await update.message.reply_text("Пожалуйста, введи целое число.")
        return
    
    guess = int(text)
    secret = user_data[user_id]['secret_number']
    user_data[user_id]['attempts'] += 1
    attempts = user_data[user_id]['attempts']
    
    # Логика игры
    if guess < secret:
        await update.message.reply_text("📉 Загаданное число БОЛЬШЕ. Попробуй еще.")
    elif guess > secret:
        await update.message.reply_text("📈 Загаданное число МЕНЬШЕ. Попробуй еще.")
    else:
        await update.message.reply_text(f"🎉 Поздравляю! Ты угадал число {secret} за {attempts} попыток! 🎉\nЧтобы сыграть снова, введи /play.")
        # Сбрасываем игру (удаляем секретное число)
        user_data[user_id]['secret_number'] = None

# --- Главная функция запуска ---
def main():
    # Вставь сюда свой токен, который дал BotFather
    TOKEN = "8490172496:AAG9SmhT3xhL3_QrsjE3QOomniwPxEaEYRQ"
    
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()
    
    # Регистрируем команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("play", play))
    
    # Регистрируем обработчик текста (для попыток угадать)
    # filters.TEXT & ~filters.COMMAND означает: любой текст, кроме команд
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Запускаем бота (polling — метод опроса серверов Telegram)
    print("Бот запущен...")
    application.run_polling()

if __name__ == '__main__':
    main()
