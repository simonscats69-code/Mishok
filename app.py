import os
import shutil
import logging
import sys
from datetime import datetime

from texts import APP_TEXTS, format_command_list, format_admin_features
from config import DATA_FILE, DATA_PATH, BACKUP_PATH, ADMIN_ID
from database import check_data_integrity, repair_data_structure, cleanup_old_votes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_environment() -> bool:
    logger.info(APP_TEXTS['env_check'])

    if not os.getenv("BOT_TOKEN"):
        logger.error(APP_TEXTS['token_error'])
        return False

    for path in (DATA_PATH, BACKUP_PATH):
        if not os.path.exists(path):
            logger.info(APP_TEXTS['dir_create'].format(path=path))
            os.makedirs(path, exist_ok=True)

    return True

def check_admin_config():
    if ADMIN_ID == 0:
        logger.warning(APP_TEXTS['admin_check'])
        logger.info(APP_TEXTS['admin_tip'])
    else:
        logger.info(APP_TEXTS['admin_ok'].format(id=ADMIN_ID))

def create_initial_backup() -> bool:
    if not os.path.exists(DATA_FILE):
        return True
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(BACKUP_PATH, f"initial_backup_{timestamp}.json")
        shutil.copy2(DATA_FILE, backup_file)
        logger.info(APP_TEXTS['initial_backup'].format(file=backup_file))
        return True
    except Exception as e:
        logger.error(APP_TEXTS['backup_error'].format(error=e))
        return False

def main():
    try:
        logger.info(APP_TEXTS['divider'])
        logger.info(APP_TEXTS['startup'])
        logger.info(APP_TEXTS['divider'])
        
        if not check_environment():
            sys.exit(1)
        
        check_admin_config()
        
        create_initial_backup()
        
        # Очищаем старые голосования при старте
        from database import cleanup_old_votes
        cleanup_old_votes()
        
        result = check_data_integrity()
        if result['errors']:
            logger.warning(APP_TEXTS['data_errors'])
            repair_data_structure()
            logger.info(APP_TEXTS['repair_complete'])
        
        logger.info(APP_TEXTS['data_loaded'].format(
            shleps=result['stats']['total_shleps'],
            users=result['stats']['users']
        ))
        
        print("\n" + APP_TEXTS['divider'])
        print(format_command_list())
        print("\n" + APP_TEXTS['divider'])
        print(format_admin_features())
        print(APP_TEXTS['divider'] + "\n")
        
        from bot import main as bot_main
        bot_main()
        
    except ImportError as e:
        logger.error(APP_TEXTS['import_error'].format(error=e))
        sys.exit(1)
    except Exception as e:
        logger.error(APP_TEXTS['startup_error'].format(error=e), exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
