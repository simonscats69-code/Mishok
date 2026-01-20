import os
import logging
import asyncio
import sys
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_environment():
    logger.info("🔍 Проверка окружения...")
    
    if not os.getenv("BOT_TOKEN"):
        logger.error("❌ BOT_TOKEN не найден в .env файле!")
        return False
    
    from config import DATA_PATH, BACKUP_PATH
    
    if not os.path.exists(DATA_PATH):
        logger.warning(f"⚠️ Директория данных не существует: {DATA_PATH}")
        logger.info(f"📁 Создаю директорию: {DATA_PATH}")
        os.makedirs(DATA_PATH, exist_ok=True)
    
    if not os.path.exists(BACKUP_PATH):
        logger.info(f"📁 Создаю директорию для бэкапов: {BACKUP_PATH}")
        os.makedirs(BACKUP_PATH, exist_ok=True)
    
    return True

def migrate_old_data():
    from config import DATA_FILE, VOTES_FILE
    
    old_data_locations = [
        "mishok_data.json",
        "data/mishok_data.json",
        "/root/mishok_data.json",
        "/bothost/mishok_data.json",
        "/app/mishok_data.json"
    ]
    
    old_votes_locations = [
        "data/votes.json",
        "votes.json",
        "/data/votes.json"
    ]
    
    migrated = False
    
    for old_location in old_data_locations:
        if os.path.exists(old_location) and old_location != DATA_FILE:
            try:
                import shutil
                os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
                shutil.copy2(old_location, DATA_FILE)
                
                backup_name = f"{old_location}.migration_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                shutil.copy2(old_location, backup_name)
                
                logger.info(f"📦 Перенесены данные из {old_location} в {DATA_FILE}")
                logger.info(f"💾 Создан бэкап старого файла: {backup_name}")
                migrated = True
                break
            except Exception as e:
                logger.error(f"⚠️ Ошибка переноса {old_location}: {e}")
    
    for old_location in old_votes_locations:
        if os.path.exists(old_location) and old_location != VOTES_FILE:
            try:
                import shutil
                os.makedirs(os.path.dirname(VOTES_FILE), exist_ok=True)
                shutil.copy2(old_location, VOTES_FILE)
                logger.info(f"🗳️ Перенесены голосования из {old_location} в {VOTES_FILE}")
            except Exception as e:
                logger.error(f"⚠️ Ошибка переноса голосований {old_location}: {e}")
    
    return migrated

def check_initial_backup():
    from config import DATA_FILE, BACKUP_PATH
    import shutil
    from datetime import datetime
    
    if os.path.exists(DATA_FILE):
        try:
            os.makedirs(BACKUP_PATH, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(BACKUP_PATH, f"initial_backup_{timestamp}.json")
            
            shutil.copy2(DATA_FILE, backup_file)
            logger.info(f"📦 Создан начальный бэкап: {backup_file}")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка создания начального бэкапа: {e}")
            return False
    return True

def check_admin_config():
    from config import ADMIN_ID
    if ADMIN_ID == 0:
        logger.warning("⚠️ ADMIN_ID не установлен! Админ-панель будет недоступна.")
        logger.info("💡 Установите ADMIN_ID в .env файле для доступа к админ-панели")
    else:
        logger.info(f"✅ ADMIN_ID установлен: {ADMIN_ID}")

def main():
    try:
        logger.info("=" * 50)
        logger.info("🚀 Запуск Мишок Лысый Бота")
        logger.info("=" * 50)
        
        if not check_environment():
            sys.exit(1)
        
        check_admin_config()
        
        migrated = migrate_old_data()
        if migrated:
            logger.info("✅ Миграция данных завершена")
        
        check_initial_backup()
        
        from database import check_data_integrity, repair_data_structure
        
        result = check_data_integrity()
        if result['errors']:
            logger.warning("⚠️ Обнаружены ошибки в данных, запускаю восстановление...")
            repair_data_structure()
            logger.info("✅ Восстановление завершено")
        
        logger.info(f"📊 Данные загружены: {result['stats']['total_shleps']} шлёпков, {result['stats']['users']} пользователей")
        
        print("\n" + "=" * 50)
        print("🎮 ОСНОВНЫЕ КОМАНДЫ:")
        print("• /start - Начать работу")
        print("• /shlep - Шлёпнуть Мишка")
        print("• /stats - Статистика")
        print("• /level - Уровень")
        print("• /admin - Админ-панель (только для админов)")
        print("• /help - Помощь")
        print("=" * 50)
        print("\n⚙️  АДМИН-ПАНЕЛЬ ВКЛЮЧЕНА!")
        print("Доступные функции:")
        print("• 🧹 Очистка системы")
        print("• 🩺 Проверка здоровья")
        print("• 📊 Статистика пользователей")
        print("• 💾 Бэкапы данных")
        print("• 🔄 Миграция данных")
        print("• 🔧 Восстановление структуры")
        print("=" * 50 + "\n")
        
        from bot import main as bot_main
        bot_main()
        
    except ImportError as e:
        logger.error(f"❌ Ошибка импорта: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Ошибка запуска: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
