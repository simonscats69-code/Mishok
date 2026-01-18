import os
import logging
from aiohttp import web
import asyncio
import signal
import sys

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

async def health_detailed(request):
    try:
        from cache import cache
        cache_stats = cache.get_stats() if hasattr(cache, 'get_stats') else {}
        
        health_data = {
            "status": "healthy",
            "timestamp": asyncio.get_event_loop().time(),
            "webhook_mode": WEBHOOK_MODE,
            "cache": cache_stats
        }
        
        return web.json_response(health_data, status=200)
    except Exception as e:
        logger.error(f"Ошибка детального health check: {e}")
        return web.json_response({"status": "error", "error": str(e)}, status=500)

async def cache_stats_endpoint(request):
    try:
        from cache import cache
        stats = cache.get_stats()
        
        response = {
            "timestamp": asyncio.get_event_loop().time(),
            "cache_stats": stats
        }
        
        return web.json_response(response, status=200)
    except Exception as e:
        logger.error(f"Ошибка получения статистики кэша: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def clear_cache_endpoint(request):
    try:
        from cache import cache
        await cache.clear()
        
        response = {
            "timestamp": asyncio.get_event_loop().time(),
            "message": "Кэш очищен"
        }
        
        return web.json_response(response, status=200)
    except Exception as e:
        logger.error(f"Ошибка очистки кэша: {e}")
        return web.json_response({"error": str(e)}, status=500)

def create_app():
    app = web.Application()
    
    # Основные эндпоинты
    app.router.add_post('/webhook', webhook_handler)
    app.router.add_get('/health', health_check)
    app.router.add_get('/health/detailed', health_detailed)
    app.router.add_get('/cache/stats', cache_stats_endpoint)
    app.router.add_post('/cache/clear', clear_cache_endpoint)
    app.router.add_get('/', health_check)
    
    # Webhook настройки
    app.on_startup.append(set_webhook_on_startup)
    
    return app

async def cleanup_cache():
    """Фоновая задача для очистки кэша"""
    try:
        from cache import cache
        logger.info("Запущена фоновая задача очистки кэша")
        
        while True:
            await asyncio.sleep(60)  # Каждую минуту
            cleared = await cache.clear_expired()
            if cleared > 0:
                logger.debug(f"Фоновая очистка кэша: удалено {cleared} записей")
    except ImportError:
        logger.warning("Кэш система не найдена, фоновая задача не запущена")
    except Exception as e:
        logger.error(f"Ошибка в фоновой задаче кэша: {e}")

async def startup_tasks(app):
    """Запуск фоновых задач при старте"""
    if WEBHOOK_MODE:
        # Запускаем фоновую задачу очистки кэша только в режиме webhook
        asyncio.create_task(cleanup_cache())
        logger.info("Фоновые задачи запущены")

def handle_shutdown(signum, frame):
    """Обработчик graceful shutdown"""
    logger.info(f"Получен сигнал {signum}, завершаем работу...")
    
    if application:
        logger.info("Останавливаем приложение...")
        try:
            if WEBHOOK_MODE:
                # В режиме webhook нужно явно остановить
                pass
            else:
                # В режиме polling останавливаем приложение
                import threading
                if hasattr(application, '_initialized') and application._initialized:
                    application.stop()
        except Exception as e:
            logger.error(f"Ошибка при остановке приложения: {e}")
    
    logger.info("Бот завершил работу")
    sys.exit(0)

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
            button_handler, group_welcome, error_handler,
            cache_stats_command, clear_cache_command
        )
        
        from telegram.ext import (
            CommandHandler, MessageHandler, CallbackQueryHandler, filters
        )
        
        # Основные команды
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("shlep", shlep_command))
        application.add_handler(CommandHandler("stats", stats_command))
        application.add_handler(CommandHandler("mishok", mishok_info_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("level", level_command))
        
        # Админские команды для кэша
        from config import ADMIN_ID
        if ADMIN_ID:
            from telegram.ext import filters as tg_filters
            admin_filter = tg_filters.User(user_id=ADMIN_ID)
            application.add_handler(CommandHandler("cache_stats", cache_stats_command, filters=admin_filter))
            application.add_handler(CommandHandler("clear_cache", clear_cache_command, filters=admin_filter))
        
        # Обработчики
        application.add_handler(CallbackQueryHandler(inline_handler))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler))
        application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, group_welcome))
        
        application.add_error_handler(error_handler)
        
        # Настраиваем обработчики сигналов для graceful shutdown
        signal.signal(signal.SIGINT, handle_shutdown)
        signal.signal(signal.SIGTERM, handle_shutdown)
        
        logger.info("Инициализация бота завершена")
        
        if WEBHOOK_MODE:
            logger.info(f"Запуск в режиме вебхука на порту {PORT}")
            
            # Создаем приложение и запускаем
            app = create_app()
            
            # Запускаем фоновые задачи
            asyncio.get_event_loop().run_until_complete(startup_tasks(app))
            
            # Запускаем веб-сервер
            web.run_app(
                app, 
                host='0.0.0.0', 
                port=PORT,
                shutdown_timeout=10  # Время на graceful shutdown
            )
        else:
            logger.info("Запуск в режиме polling")
            
            # Запускаем фоновые задачи для polling режима
            loop = asyncio.get_event_loop()
            loop.create_task(cleanup_cache())
            
            # Запускаем polling
            application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,
                close_loop=False  # Не закрывать event loop
            )
            
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        exit(1)

if __name__ == "__main__":
    main()
