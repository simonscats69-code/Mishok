import json
import os
from datetime import datetime, timedelta
import logging
from typing import Optional, Tuple, List, Any, Dict
import shutil
import threading
import time

logger = logging.getLogger(__name__)

from config import DATA_FILE, VOTES_FILE, BACKUP_PATH, BACKUP_ENABLED, AUTOSAVE_INTERVAL

# Глобальная переменная для хранения данных в памяти
_in_memory_data = None
_data_lock = threading.Lock()
_last_save_time = time.time()
_data_modified = False

def ensure_votes_file():
    """Создаёт файл голосований если его нет"""
    try:
        if not os.path.exists(VOTES_FILE):
            os.makedirs(os.path.dirname(VOTES_FILE), exist_ok=True)
            with open(VOTES_FILE, 'w', encoding='utf-8') as f:
                json.dump({}, f)
    except Exception as e:
        logger.error(f"Ошибка создания файла голосований: {e}")

def save_vote_data(vote_data):
    """Сохраняет данные голосования"""
    ensure_votes_file()
    try:
        with open(VOTES_FILE, 'r', encoding='utf-8') as f:
            all_votes = json.load(f)
        all_votes[vote_data["id"]] = vote_data
        with open(VOTES_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_votes, f, indent=2, ensure_ascii=False, default=str)
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения голосования: {e}")
        return False

def get_vote_data(vote_id):
    """Получает данные голосования"""
    ensure_votes_file()
    try:
        with open(VOTES_FILE, 'r', encoding='utf-8') as f:
            all_votes = json.load(f)
        return all_votes.get(vote_id)
    except Exception as e:
        logger.error(f"Ошибка чтения голосования: {e}")
        return None

def get_all_votes():
    """Получает все голосования"""
    ensure_votes_file()
    try:
        with open(VOTES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка чтения всех голосований: {e}")
        return {}

def delete_vote_data(vote_id):
    """Удаляет данные голосования"""
    ensure_votes_file()
    try:
        with open(VOTES_FILE, 'r', encoding='utf-8') as f:
            all_votes = json.load(f)
        if vote_id in all_votes:
            del all_votes[vote_id]
        with open(VOTES_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_votes, f, indent=2, ensure_ascii=False, default=str)
        return True
    except Exception as e:
        logger.error(f"Ошибка удаления голосования: {e}")
        return False

def get_user_vote(vote_id, user_id):
    """Получает голос пользователя"""
    vote_data = get_vote_data(vote_id)
    if not vote_data:
        return None
    user_id_str = str(user_id)
    if user_id_str in vote_data.get("votes_yes", []):
        return "yes"
    elif user_id_str in vote_data.get("votes_no", []):
        return "no"
    return None

def cleanup_expired_votes():
    """Удаляет просроченные голосования (старше 30 дней)"""
    try:
        all_votes = get_all_votes()
        now = datetime.now()
        expired = []
        
        for vote_id, vote_data in all_votes.items():
            ends_at_str = vote_data.get("ends_at")
            if ends_at_str:
                try:
                    ends_at = datetime.fromisoformat(ends_at_str)
                    finished = vote_data.get("finished", False)
                    
                    # Удаляем голосования старше 30 дней
                    if now > ends_at + timedelta(days=30):
                        expired.append(vote_id)
                except:
                    continue
        
        for vote_id in expired:
            del all_votes[vote_id]
        
        if expired:
            with open(VOTES_FILE, 'w', encoding='utf-8') as f:
                json.dump(all_votes, f, indent=2, ensure_ascii=False, default=str)
            logger.info(f"Удалено {len(expired)} просроченных голосований")
            
    except Exception as e:
        logger.error(f"Ошибка очистки голосований: {e}")

def create_default_data():
    """Создаёт структуру данных по умолчанию"""
    return {
        "version": "3.0",  # Новая версия структуры
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "users": {},  # Основные данные пользователей
        "chats": {},  # Минимальные данные чатов
        "global_stats": {
            "total_shleps": 0,
            "last_shlep": None,
            "max_damage": 0,
            "max_damage_user": None,
            "max_damage_date": None,
            "total_users": 0
        },
        "timestamps": {},  # Только счётчики по дням
        "records": []  # Только топ-5 рекордов
    }

def ensure_data_file():
    """Создаёт файл данных если его нет"""
    try:
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        
        if not os.path.exists(DATA_FILE):
            default_data = create_default_data()
            save_data_to_disk(default_data)
            logger.info(f"Создан новый файл данных: {DATA_FILE}")
            return default_data
        
        return load_data_from_disk()
        
    except Exception as e:
        logger.error(f"Ошибка загрузки файла данных: {e}")
        return create_default_data()

def convert_old_structure(data):
    """Конвертирует старую структуру в новую"""
    logger.info("Конвертируем старую структуру в новую...")
    
    # Удаляем лишние данные из старой структуры
    for user_id, user_data in data.get("users", {}).items():
        # Удаляем damage_history если есть
        if "damage_history" in user_data:
            del user_data["damage_history"]
        
        # Удаляем chat_stats если есть
        if "chat_stats" in user_data:
            del user_data["chat_stats"]
    
    # Упрощаем timestamps - оставляем только счётчики
    if "timestamps" in data:
        for key in list(data["timestamps"].keys()):
            if isinstance(data["timestamps"][key], dict) and "count" in data["timestamps"][key]:
                # Оставляем только счётчик
                data["timestamps"][key] = data["timestamps"][key]["count"]
    
    # Ограничиваем records до 5
    if "records" in data and len(data["records"]) > 5:
        data["records"] = data["records"][-5:]
    
    data["version"] = "3.0"
    data["updated_at"] = datetime.now().isoformat()
    
    return data

def load_data_from_disk():
    """Загружает данные с диска и конвертирует при необходимости"""
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        version = data.get("version", "1.0")
        
        # Конвертируем если старая версия
        if version != "3.0":
            logger.info(f"Конвертируем данные с версии {version} на 3.0")
            data = convert_old_structure(data)
            save_data_to_disk(data)
        
        logger.info(f"Загружен файл данных: {DATA_FILE}")
        logger.info(f"   Пользователей: {len(data.get('users', {}))}")
        logger.info(f"   Шлёпков: {data.get('global_stats', {}).get('total_shleps', 0)}")
        
        return data
        
    except Exception as e:
        logger.error(f"Ошибка загрузки файла данных: {e}")
        return create_default_data()

def repair_data_structure():
    """Восстанавливает структуру данных"""
    try:
        data = load_data()
        
        # Обеспечиваем минимальную структуру
        data.setdefault("users", {})
        data.setdefault("chats", {})
        data.setdefault("global_stats", {
            "total_shleps": 0,
            "last_shlep": None,
            "max_damage": 0,
            "max_damage_user": None,
            "max_damage_date": None,
            "total_users": 0
        })
        data.setdefault("timestamps", {})
        data.setdefault("records", [])
        
        # Упрощаем пользователей
        for user_id, user_data in data["users"].items():
            user_data.setdefault("username", f"User_{user_id}")
            user_data.setdefault("total_shleps", 0)
            user_data.setdefault("max_damage", 0)
            user_data.setdefault("last_shlep", None)
            user_data.setdefault("bonus_damage", 0)
            
            # Удаляем старые поля если есть
            user_data.pop("damage_history", None)
            user_data.pop("chat_stats", None)
            user_data.pop("count", None)
        
        # Упрощаем чаты
        for chat_id, chat_data in data["chats"].items():
            chat_data.setdefault("total_shleps", 0)
            chat_data.setdefault("users", {})
            
            # Упрощаем пользователей в чатах
            for user_id, user_data in chat_data["users"].items():
                user_data.setdefault("username", f"User_{user_id}")
                user_data.setdefault("total_shleps", 0)
                user_data.pop("max_damage", None)  # Не храним в чатах
        
        # Обновляем счётчик пользователей
        data["global_stats"]["total_users"] = len(data["users"])
        
        save_data(data)
        logger.info("Структура данных восстановлена")
        return True
    except Exception as e:
        logger.error(f"Ошибка восстановления структуры данных: {e}")
        return False

def load_data():
    """Загружает данные из памяти или с диска"""
    global _in_memory_data
    
    with _data_lock:
        if _in_memory_data is None:
            _in_memory_data = ensure_data_file()
        return _in_memory_data.copy()

def save_data_to_disk(data):
    """Сохранение данных на диск (без лишних операций)"""
    try:
        data["updated_at"] = datetime.now().isoformat()
        
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        
        # Упрощённая сериализация
        temp_file = DATA_FILE + ".tmp"
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, separators=(',', ':'))  # Минимизируем JSON
        
        os.replace(temp_file, DATA_FILE)
        
        logger.debug(f"Данные сохранены на диск: {DATA_FILE}")
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения данных на диск: {e}")
        return False

def schedule_save():
    """Планировщик автосохранения (раз в AUTOSAVE_INTERVAL секунд)"""
    global _data_modified, _last_save_time
    
    with _data_lock:
        current_time = time.time()
        
        # Сохраняем если данные изменены и прошло достаточно времени
        if _data_modified and (current_time - _last_save_time) > AUTOSAVE_INTERVAL:
            
            if _in_memory_data:
                save_data_to_disk(_in_memory_data)
                # Создаем дневной бэкап если нужно
                if BACKUP_ENABLED and should_create_backup():
                    create_daily_backup()
            
            _data_modified = False
            _last_save_time = current_time
            logger.debug(f"Автосохранение через {current_time - _last_save_time:.1f} секунд")
            return True
    
    return False

def should_create_backup():
    """Проверяет, нужно ли создавать бэкап (только раз в день)"""
    if not BACKUP_ENABLED:
        return False
    
    backup_marker = os.path.join(BACKUP_PATH, ".last_backup_date")
    
    try:
        if os.path.exists(backup_marker):
            with open(backup_marker, 'r') as f:
                last_backup_date = f.read().strip()
            
            # Если сегодня уже был бэкап - не создаем
            if last_backup_date == datetime.now().strftime("%Y-%m-%d"):
                return False
    except:
        pass
    
    return True

def create_daily_backup():
    """Создает бэкап только раз в день"""
    try:
        if not os.path.exists(DATA_FILE):
            return False
        
        os.makedirs(BACKUP_PATH, exist_ok=True)
        
        # Проверяем, был ли сегодня бэкап
        backup_marker = os.path.join(BACKUP_PATH, ".last_backup_date")
        today = datetime.now().strftime("%Y-%m-%d")
        
        try:
            if os.path.exists(backup_marker):
                with open(backup_marker, 'r') as f:
                    last_backup_date = f.read().strip()
                
                if last_backup_date == today:
                    logger.debug("Бэкап сегодня уже создавался, пропускаем")
                    return False
        except:
            pass
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(BACKUP_PATH, f"daily_{timestamp}.json")
        
        shutil.copy2(DATA_FILE, backup_file)
        
        # Сохраняем дату последнего бэкапа
        with open(backup_marker, 'w') as f:
            f.write(today)
        
        # Очищаем старые бэкапы (оставляем только 5 последних)
        cleanup_backups(max_backups=5)
        
        size = os.path.getsize(backup_file)
        logger.info(f"Создан дневной бэкап: {backup_file} ({size} байт)")
        
        return True
    except Exception as e:
        logger.error(f"Ошибка создания дневного бэкапа: {e}")
        return False

def cleanup_backups(max_backups=5):
    """Удаляет старые бэкапы, оставляя только max_backups последних"""
    try:
        if not os.path.exists(BACKUP_PATH):
            return
        
        backups = []
        for filename in os.listdir(BACKUP_PATH):
            if filename.endswith('.json') and filename.startswith('daily_'):
                filepath = os.path.join(BACKUP_PATH, filename)
                mtime = os.path.getmtime(filepath)
                backups.append((filepath, mtime, filename))
        
        # Сортируем по дате изменения (новые сначала)
        backups.sort(key=lambda x: x[1], reverse=True)
        
        # Удаляем старые, оставляем только max_backups
        for backup in backups[max_backups:]:
            try:
                os.remove(backup[0])
                logger.debug(f"Удален старый бэкап: {backup[2]}")
            except Exception as e:
                logger.error(f"Ошибка удаления старого бэкапа {backup[2]}: {e}")
                
    except Exception as e:
        logger.error(f"Ошибка очистки бэкапов: {e}")

def save_data(data):
    """Обновляет данные в памяти и помечает для сохранения"""
    global _in_memory_data, _data_modified
    
    with _data_lock:
        _in_memory_data = data
        _data_modified = True
    
    # Пытаемся сохранить если прошло много времени
    schedule_save()
    
    return True

def create_safe_backup(description: str = "") -> Tuple[bool, str]:
    """Ручное создание бэкапа (только по команде)"""
    try:
        if not os.path.exists(DATA_FILE):
            return False, "Файл данных не существует"
        
        os.makedirs(BACKUP_PATH, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        desc_part = f"_{description}" if description else ""
        backup_file = os.path.join(BACKUP_PATH, f"manual{desc_part}_{timestamp}.json")
        
        # Сначала сохраняем текущие данные из памяти
        with _data_lock:
            if _in_memory_data:
                save_data_to_disk(_in_memory_data)
        
        # Копируем файл
        shutil.copy2(DATA_FILE, backup_file)
        
        # Очищаем старые ручные бэкапы (оставляем 3 последних)
        cleanup_manual_backups(max_backups=3)
        
        size = os.path.getsize(backup_file)
        logger.info(f"Создан ручной бэкап: {backup_file} ({size} байт)")
        
        return True, backup_file
    except Exception as e:
        logger.error(f"Ошибка создания ручного бэкапа: {e}")
        return False, str(e)

def cleanup_manual_backups(max_backups=3):
    """Удаляет старые ручные бэкапы"""
    try:
        if not os.path.exists(BACKUP_PATH):
            return
        
        manual_backups = []
        for filename in os.listdir(BACKUP_PATH):
            if filename.endswith('.json') and filename.startswith('manual'):
                filepath = os.path.join(BACKUP_PATH, filename)
                mtime = os.path.getmtime(filepath)
                manual_backups.append((filepath, mtime, filename))
        
        # Сортируем по дате изменения (новые сначала)
        manual_backups.sort(key=lambda x: x[1], reverse=True)
        
        # Удаляем старые, оставляем только max_backups
        for backup in manual_backups[max_backups:]:
            try:
                os.remove(backup[0])
                logger.debug(f"Удален старый ручной бэкап: {backup[2]}")
            except Exception as e:
                logger.error(f"Ошибка удаления старого ручного бэкапа {backup[2]}: {e}")
                
    except Exception as e:
        logger.error(f"Ошибка очистки ручных бэкапов: {e}")

def get_backup_list(limit: int = 10) -> List[Dict]:
    """Получает список бэкапов"""
    try:
        if not os.path.exists(BACKUP_PATH):
            return []
        
        backups = []
        for filename in os.listdir(BACKUP_PATH):
            if filename.endswith('.json'):
                filepath = os.path.join(BACKUP_PATH, filename)
                mtime = os.path.getmtime(filepath)
                size = os.path.getsize(filepath)
                
                backups.append({
                    "name": filename,
                    "path": filepath,
                    "size": size,
                    "modified": datetime.fromtimestamp(mtime),
                    "age_days": (datetime.now() - datetime.fromtimestamp(mtime)).days
                })
        
        backups.sort(key=lambda x: x["modified"], reverse=True)
        return backups[:limit]
    except Exception as e:
        logger.error(f"Ошибка получения списка бэкапов: {e}")
        return []

def get_database_size() -> Dict[str, Any]:
    """Получает информацию о размере БД"""
    try:
        if not os.path.exists(DATA_FILE):
            return {"exists": False, "size": 0, "users": 0, "chats": 0}
        
        size = os.path.getsize(DATA_FILE)
        
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return {
            "exists": True,
            "size": size,
            "users": len(data.get("users", {})),
            "chats": len(data.get("chats", {})),
            "total_shleps": data.get("global_stats", {}).get("total_shleps", 0),
            "last_modified": datetime.fromtimestamp(os.path.getmtime(DATA_FILE))
        }
    except Exception as e:
        logger.error(f"Ошибка получения размера БД: {e}")
        return {"exists": False, "size": 0, "error": str(e)}

def add_shlep(user_id: int, username: str, damage: int, chat_id: Optional[int] = None) -> Tuple[int, int, int]:
    """Добавляет шлёпок - оптимизированная версия"""
    try:
        global _in_memory_data, _data_modified
        
        with _data_lock:
            if _in_memory_data is None:
                _in_memory_data = ensure_data_file()
            
            data = _in_memory_data
            now = datetime.now().isoformat()
            user_id_str = str(user_id)
            
            # Обновляем пользователя
            if user_id_str not in data["users"]:
                data["users"][user_id_str] = {
                    "username": username,
                    "total_shleps": 0,
                    "max_damage": 0,
                    "last_shlep": now,
                    "bonus_damage": 0
                }
                data["global_stats"]["total_users"] = len(data["users"])
            
            user = data["users"][user_id_str]
            user["username"] = username
            user["total_shleps"] += 1
            user["last_shlep"] = now
            
            if damage > user["max_damage"]:
                user["max_damage"] = damage
            
            # Обновляем чат если указан
            if chat_id:
                chat_id_str = str(chat_id)
                
                if chat_id_str not in data["chats"]:
                    data["chats"][chat_id_str] = {
                        "total_shleps": 0,
                        "users": {}
                    }
                
                chat = data["chats"][chat_id_str]
                chat["total_shleps"] += 1
                
                if user_id_str not in chat["users"]:
                    chat["users"][user_id_str] = {
                        "username": username,
                        "total_shleps": 0
                    }
                
                chat_user = chat["users"][user_id_str]
                chat_user["username"] = username
                chat_user["total_shleps"] += 1
            
            # Обновляем глобальную статистику
            data["global_stats"]["total_shleps"] += 1
            data["global_stats"]["last_shlep"] = now
            
            if damage > data["global_stats"]["max_damage"]:
                data["global_stats"]["max_damage"] = damage
                data["global_stats"]["max_damage_user"] = username
                data["global_stats"]["max_damage_date"] = now
            
            # Простые счётчики по дням
            date_key = datetime.now().strftime("%Y-%m-%d")
            if date_key not in data["timestamps"]:
                data["timestamps"][date_key] = 0
            data["timestamps"][date_key] += 1
            
            # Сохраняем рекорд если урон >= 50 (только топ-5)
            if damage >= 50:
                record = {
                    "user_id": user_id,
                    "username": username,
                    "damage": damage,
                    "timestamp": now,
                    "chat_id": chat_id
                }
                data["records"].append(record)
                
                # Оставляем только 5 последних рекордов
                if len(data["records"]) > 5:
                    data["records"] = data["records"][-5:]
            
            # Помечаем данные как изменённые
            _data_modified = True
            
            return (
                data["global_stats"]["total_shleps"],
                user["total_shleps"],
                user["max_damage"]
            )
            
    except Exception as e:
        logger.error(f"Ошибка в add_shlep: {e}", exc_info=True)
        return (0, 0, 0)

def get_stats() -> Tuple[int, Optional[datetime], int, Optional[str], Optional[datetime]]:
    """Получает глобальную статистику"""
    try:
        data = load_data()
        
        last_shlep = data["global_stats"].get("last_shlep")
        max_damage_date = data["global_stats"].get("max_damage_date")
        
        return (
            data["global_stats"].get("total_shleps", 0),
            datetime.fromisoformat(last_shlep) if last_shlep else None,
            data["global_stats"].get("max_damage", 0),
            data["global_stats"].get("max_damage_user"),
            datetime.fromisoformat(max_damage_date) if max_damage_date else None
        )
    except Exception as e:
        logger.error(f"Ошибка в get_stats: {e}")
        return (0, None, 0, None, None)

def get_top_users(limit: int = 10) -> List[Tuple[str, int]]:
    """Получает топ пользователей"""
    try:
        data = load_data()
        
        users_list = []
        for user_id, user_data in data["users"].items():
            username = user_data.get("username", f"Игрок_{user_id}")
            total = user_data.get("total_shleps", 0)
            users_list.append((username, total))
        
        users_list.sort(key=lambda x: x[1], reverse=True)
        return users_list[:limit]
    except Exception as e:
        logger.error(f"Ошибка в get_top_users: {e}")
        return []

def get_user_stats(user_id: int) -> Tuple[Optional[str], int, Optional[datetime]]:
    """Получает статистику пользователя"""
    try:
        data = load_data()
        
        user_data = data["users"].get(str(user_id))
        if not user_data:
            return (None, 0, None)
        
        last_shlep = user_data.get("last_shlep")
        return (
            user_data.get("username"),
            user_data.get("total_shleps", 0),
            datetime.fromisoformat(last_shlep) if last_shlep else None
        )
    except Exception as e:
        logger.error(f"Ошибка в get_user_stats: {e}")
        return (None, 0, None)

def get_chat_stats(chat_id: int) -> Dict[str, Any]:
    """Получает статистику чата"""
    try:
        data = load_data()
        
        chat_data = data["chats"].get(str(chat_id))
        if not chat_data:
            return {}
        
        # Вычисляем максимальный урон из пользователей чата
        max_damage = 0
        max_damage_user = None
        
        for user_id, user_data in data["users"].items():
            if user_id in chat_data.get("users", {}):
                user_damage = user_data.get("max_damage", 0)
                if user_damage > max_damage:
                    max_damage = user_damage
                    max_damage_user = user_data.get("username")
        
        return {
            "total_users": len(chat_data.get("users", {})),
            "total_shleps": chat_data.get("total_shleps", 0),
            "max_damage": max_damage,
            "max_damage_user": max_damage_user
        }
    except Exception as e:
        logger.error(f"Ошибка в get_chat_stats: {e}")
        return {}

def get_chat_top_users(chat_id: int, limit: int = 10) -> List[Tuple[str, int]]:
    """Получает топ пользователей чата"""
    try:
        data = load_data()
        
        chat_data = data["chats"].get(str(chat_id))
        if not chat_data:
            return []
        
        users_list = []
        for user_id, user_data in chat_data.get("users", {}).items():
            username = user_data.get("username", f"Игрок_{user_id}")
            total = user_data.get("total_shleps", 0)
            users_list.append((username, total))
        
        users_list.sort(key=lambda x: x[1], reverse=True)
        return users_list[:limit]
    except Exception as e:
        logger.error(f"Ошибка в get_chat_top_users: {e}")
        return []

def backup_database():
    """Создаёт бэкап (алиас для create_safe_backup)"""
    return create_safe_backup("command")

def check_data_integrity():
    """Проверяет целостность данных"""
    try:
        data = load_data()
        
        errors = []
        warnings = []
        
        required_keys = ["users", "chats", "global_stats", "timestamps", "records"]
        for key in required_keys:
            if key not in data:
                errors.append(f"Отсутствует обязательный ключ: {key}")
        
        # Проверяем что все пользователи в чатах существуют
        for chat_id, chat_data in data.get("chats", {}).items():
            for user_id in chat_data.get("users", {}).keys():
                if user_id not in data.get("users", {}):
                    warnings.append(f"Чат {chat_id}: пользователь {user_id} не найден в общих данных")
        
        total_from_users = sum(user.get("total_shleps", 0) for user in data.get("users", {}).values())
        total_in_global = data.get("global_stats", {}).get("total_shleps", 0)
        
        if total_from_users != total_in_global:
            warnings.append(f"Несоответствие счетчиков: пользователи={total_from_users}, глобально={total_in_global}")
        
        return {
            "errors": errors,
            "warnings": warnings,
            "stats": {
                "users": len(data.get("users", {})),
                "chats": len(data.get("chats", {})),
                "total_shleps": data.get("global_stats", {}).get("total_shleps", 0)
            }
        }
    except Exception as e:
        logger.error(f"Ошибка в check_data_integrity: {e}")
        return {
            "errors": [f"Ошибка проверки: {str(e)}"],
            "warnings": [],
            "stats": {}
        }

# Запускаем очистку при импорте
cleanup_expired_votes()
logger.info("Оптимизированная база данных готова к работе")
