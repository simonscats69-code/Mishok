import os
import logging
from aiohttp import web
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DOMAIN = os.getenv("DOMAIN", "")
PORT = int(os.getenv("PORT", "8443"))
WEBHOOK_MODE = os.getenv("WEBHOOK_MODE", "false").lower() == "true"

if not BOT_TOKEN:
    logger.error("BOT_TOKEN не установлен!")
    exit(1)

if WEBHOOK_MODE and not DOMAIN:
    logger.error("DOMAIN не установлен для режима вебхуков!")
    exit(1)

try:
    from telegram import Update
    from telegram.ext import Application
except ImportError as e:
    logger.error(f"Ошибка импорта telegram: {e}")
    exit(1)

application = None

async def set_webhook_on_startup(app):
    if WEBHOOK_MODE:
        try:
            await application.bot.set_webhook(
                f"{DOMAIN}/webhook",
                secret_token=os.getenv("SECRET_TOKEN", "")
            )
            logger.info(f"Вебхук установлен на {DOMAIN}/webhook")
        except Exception as e:
            logger.error(f"Ошибка установки вебхука: {e}")

async def webhook_handler(request):
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        await application.update_queue.put(update)
        return web.Response(text="OK", status=200)
    except Exception as e:
        logger.error(f"Ошибка обработки вебхука: {e}")
        return web.Response(text="Error", status=500)

async def health_check(request):
    return web.Response(text="Бот работает", status=200)

def create_app():
    app = web.Application()
    app.router.add_post('/webhook', webhook_handler)
    app.router.add_get('/health', health_check)
    app.router.add_get('/', health_check)
    app.on_startup.append(set_webhook_on_startup)
    return app

def main():
    global application
    
    try:
        from bot import BOT_TOKEN as bot_token
    except ImportError as e:
        logger.error(f"Ошибка импорта бота: {e}")
        exit(1)
    
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        
        from bot import (
            start_command, shlep_command, stats_command, mishok_info_command,
            help_command, level_command, inline_handler,
            button_handler, group_welcome, error_handler
        )
        
        from telegram.ext import (
            CommandHandler, MessageHandler, CallbackQueryHandler, filters
        )
        
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("shlep", shlep_command))
        application.add_handler(CommandHandler("stats", stats_command))
        application.add_handler(CommandHandler("mishok", mishok_info_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("level", level_command))
        
        application.add_handler(CallbackQueryHandler(inline_handler))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler))
        application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, group_welcome))
        
        application.add_error_handler(error_handler)
        
        logger.info("Инициализация бота завершена")
        
        if WEBHOOK_MODE:
            logger.info(f"Запуск в режиме вебхука на порту {PORT}")
            web.run_app(create_app(), host='0.0.0.0', port=PORT)
        else:
            logger.info("Запуск в режиме polling")
            application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
            
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        exit(1)

if __name__ == "__main__":
    main()
