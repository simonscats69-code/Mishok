import os
import logging
import asyncio
import sys
from telegram.ext import Application

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    try:
        # Очистка просроченных дуэлей при запуске
        try:
            from database import cleanup_expired_duels
            cleaned = cleanup_expired_duels()
            if cleaned > 0:
                logger.info(f"Очищено {cleaned} просроченных дуэлей при запуске")
        except ImportError as e:
            logger.warning(f"Не удалось импортировать cleanup_expired_duels: {e}")
        
        # Импортируем основную функцию бота
        from bot import main as bot_main
        bot_main()
        
    except ImportError as e:
        logger.error(f"Ошибка импорта: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Ошибка запуска: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
