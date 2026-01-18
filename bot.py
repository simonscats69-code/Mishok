import logging
from random import choice
from telegram import Update, Sticker
from telegram.ext import Application, CommandHandler, ContextTypes

# Вставьте ваш токен от BotFather
TOKEN = "ВАШ_ТОКЕН_ЗДЕСЬ"

# Включим логирование
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Словарь для хранения счётчика (временный, для демо)
counter = {"global": 0}

# Реакции на "шлёпок"
reactions = [
    "Лысик говорит: 'Ай! Зачем шлёпать? Я же красивый!' 👴💢",
    "Лысик издал звонкий *ХЛОП* и покраснел! 🔴",
    "От лысины пошли круги по воде... 🌊",
    "Лысик моргнул и сказал: 'Ещё!' 😄",
    "Вот это шлёпок! Лысина теперь блестит ещё сильнее! ✨",
    "Лысик сделал сальто от неожиданности! 🤸"
]

# ID безопасных стикеров (можно заменить на свои)
STICKER_IDS = [
    "CAACAgIAAxkBAAEL...",  # Замените на реальные ID стикеров
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    welcome_text = (
        "Привет! Я бот с виртуальным Лысиком! 👴\n"
        "Используй /shlep чтобы шлёпнуть его по лысине (шуточно!)\n"
        "Используй /stats чтобы увидеть счётчик шлёпков."
    )
    await update.message.reply_text(welcome_text)

async def shlep(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /shlep"""
    # Увеличиваем счётчик
    counter["global"] += 1
    
    # Выбираем случайную реакцию
    reaction = choice(reactions)
    
    # Отправляем текст
    await update.message.reply_text(f"{reaction}\n(Всего шлёпков: {counter['global']})")
    
    # Если есть стикеры, отправим случайный стикер
    if STICKER_IDS:
        # Временно используем стандартный стикер, если свои не добавлены
        await update.message.reply_sticker("CAACAgIAAxkBAAIBTWadRzLgL5EwAAE2e0AAAUH2oYD-8QACPlIAAr5d4UoGAAH62QABlBzHMwQ")
    else:
        # Альтернатива: отправить эмодзи
        await update.message.reply_text("👋")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику"""
    await update.message.reply_text(f"Всего шлёпков по лысине: {counter['global']}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ошибок"""
    logger.warning(f"Update {update} caused error {context.error}")

def main():
    """Запуск бота"""
    # Создаём приложение
    application = Application.builder().token(TOKEN).build()
    
    # Регистрируем команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("shlep", shlep))
    application.add_handler(CommandHandler("stats", stats))
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Запускаем бота
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
