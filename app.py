import os
import logging
import asyncio
import sys
from telegram.ext import Application

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # Импортируем только после проверки токена
    try:
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
