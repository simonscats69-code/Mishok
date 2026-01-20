import os
from dotenv import load_dotenv
import random

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден! Создайте .env файл с BOT_TOKEN=ваш_токен")

ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_PATH = os.getenv("DATA_PATH", "data/mishok_bot")
DATA_FILE = os.path.join(BASE_DIR, DATA_PATH, "mishok_data.json")
BACKUP_PATH = os.path.join(BASE_DIR, DATA_PATH, "backups")
LOG_FILE = os.path.join(BASE_DIR, DATA_PATH, "bot.log")

CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "300"))
MAX_CACHE_SIZE = int(os.getenv("MAX_CACHE_SIZE", "1000"))
LOG_CACHE_STATS = os.getenv("LOG_CACHE_STATS", "false").lower() == "true"

CHAT_VOTE_DURATION = int(os.getenv("CHAT_VOTE_DURATION", "300"))  # 5 минут
CHAT_NOTIFICATIONS_ENABLED = os.getenv("CHAT_NOTIFICATIONS_ENABLED", "true").lower() == "true"

BACKUP_ENABLED = os.getenv("BACKUP_ENABLED", "true").lower() == "true"
BACKUP_RETENTION_DAYS = int(os.getenv("BACKUP_RETENTION_DAYS", "7"))

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
AUTOSAVE_INTERVAL = int(os.getenv("AUTOSAVE_INTERVAL", "30"))  # Сохраняем каждые 30 секунд

for directory in [os.path.dirname(DATA_FILE), BACKUP_PATH]:
    if directory and not os.path.exists(directory):
        try:
            os.makedirs(directory, exist_ok=True)
            print(f"📁 Создана директория: {directory}")
        except:
            pass

# Импортируем тексты из texts.py
from texts import CONFIG_MESSAGES, MISHOK_REACTIONS, MISHOK_INTRO

# Используем тексты из texts.py
print(CONFIG_MESSAGES['title'])
print(CONFIG_MESSAGES['bot_token'].format(status='✅ Установлен' if BOT_TOKEN else '❌ НЕТ!'))
print(CONFIG_MESSAGES['admin_id'].format(admin_id=ADMIN_ID))
print(CONFIG_MESSAGES['paths_title'])
print(CONFIG_MESSAGES['data_path'].format(path=DATA_PATH))
print(CONFIG_MESSAGES['data_file'].format(file=DATA_FILE))
print(CONFIG_MESSAGES['backup_path'].format(path=BACKUP_PATH))
print(CONFIG_MESSAGES['log_file'].format(file=LOG_FILE))
print(CONFIG_MESSAGES['autosave'].format(interval=AUTOSAVE_INTERVAL))
print(CONFIG_MESSAGES['vote_duration'].format(duration=CHAT_VOTE_DURATION))
print(CONFIG_MESSAGES['divider'])
