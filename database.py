import json
import os
from datetime import datetime, timedelta
import logging
from typing import Optional, Tuple, List, Any, Dict
import shutil
import random

logger = logging.getLogger(__name__)

DATA_FILE = "data/mishok_data.json"
BACKUP_DIR = "data/backups"
VOTES_FILE = "data/votes.json"

# ========== Вспомогательные функции для безопасного доступа ==========

def get_active_duels_safe(data: Dict) -> Dict:
    """Безопасно получает активные дуэли"""
    try:
        if "duels" not in data:
            return {}
        return data["duels"].get("active", {})
    except:
        return {}

def get_duel_invites_safe(data: Dict) -> Dict:
    """Безопасно получает приглашения на дуэли"""
    try:
        if "duels" not in data:
            return {}
        return data["duels"].get("invites", {})
    except:
        return {}

def get_duel_history_safe(data: Dict) -> List:
    """Безопасно получает историю дуэлей"""
    try:
        if "duels" not in data:
            return []
        return data["duels"].get("history", [])
    except:
        return []

# ========== Функции для работы с голосованиями ==========

def ensure_votes_file():
    """Создает файл для голосований, если его нет"""
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
    """Получает данные голосования по ID"""
    ensure_votes_file()
    try:
        with open(VOTES_FILE, 'r', encoding='utf-8') as f:
            all_votes = json.load(f)
        return all_votes.get(vote_id)
    except Exception as e:
        logger.error(f"Ошибка чтения голосования: {e}")
        return None

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
    """Получает голос пользователя в конкретном голосовании"""
    vote_data = get_vote_data(vote_id)
    if not vote_data:
        return None
    user_id_str = str(user_id)
    if user_id_str in vote_data.get("votes_yes", []):
        return "yes"
    elif user_id_str in vote_data.get("votes_no", []):
        return "no"
    return None

# ========== Функции для работы с основными данными ==========

def ensure_data_file():
    """Создает файл данных, если его нет"""
    try:
        if not os.path.exists(DATA_FILE):
            os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
            default_data = create_default_data()
            save_data(default_data)
            logger.info(f"Создан новый файл данных: {DATA_FILE}")
            return default_data
        
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Конвертация старой структуры
        if "user_stats" in data and "users" not in data:
            logger.info("Автоматическая конвертация user_stats -> users")
            data["users"] = data.pop("user_stats")
            for user_id, user_data in data["users"].items():
                if "count" in user_data:
                    user_data["total_shleps"] = user_data.pop("count")
                user_data.setdefault("max_damage", 0)
                user_data.setdefault("last_shlep", None)
                user_data.setdefault("damage_history", [])
                user_data.setdefault("chat_stats", {})
            
            save_data(data)
        
        return data
    except Exception as e:
        logger.error(f"Ошибка загрузки файла данных: {e}")
        return create_new_data_file()

def create_default_data():
    """Создает структуру данных по умолчанию"""
    return {
        "users": {},
        "chats": {},
        "global_stats": {
            "total_shleps": 0,
            "last_shlep": None,
            "max_damage": 0,
            "max_damage_user": None,
            "max_damage_date": None,
            "total_users": 0
        },
        "timestamps": {},
        "records": [],
        "duels": {
            "active": {},
            "invites": {},
            "history": []
        }
    }

def create_new_data_file():
    """Создает новый файл данных"""
    default_data = create_default_data()
    save_data(default_data)
    logger.info(f"Создан новый файл данных: {DATA_FILE}")
    return default_data

def repair_data_structure():
    """Восстанавливает структуру данных при повреждении"""
    try:
        data = load_data_raw()
        
        # Устанавливаем стандартные ключи
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
        data.setdefault("duels", {
            "active": {},
            "invites": {},
            "history": []
        })
        
        # Восстанавливаем структуру пользователей
        for user_id, user_data in data["users"].items():
            user_data.setdefault("username", f"User_{user_id}")
            user_data.setdefault("total_shleps", user_data.get("count", 0))
            user_data.setdefault("max_damage", 0)
            user_data.setdefault("last_shlep", None)
            user_data.setdefault("damage_history", [])
            user_data.setdefault("chat_stats", {})
            user_data.setdefault("bonus_damage", 0)
            
            if "count" in user_data:
                del user_data["count"]
        
        # Восстанавливаем структуру чатов
        for chat_id, chat_data in data["chats"].items():
            chat_data.setdefault("total_shleps", 0)
            chat_data.setdefault("users", {})
            chat_data.setdefault("max_damage", 0)
            chat_data.setdefault("max_damage_user", None)
            chat_data.setdefault("max_damage_date", None)
            
            for user_id, user_data in chat_data["users"].items():
                user_data.setdefault("username", f"User_{user_id}")
                user_data.setdefault("total_shleps", user_data.get("count", 0))
                user_data.setdefault("max_damage", 0)
                
                if "count" in user_data:
                    del user_data["count"]
        
        data["global_stats"]["total_users"] = len(data["users"])
        
        save_data(data)
        logger.info("Структура данных восстановлена")
        return True
    except Exception as e:
        logger.error(f"Ошибка восстановления структуры данных: {e}")
        return False

def load_data_raw():
    """Загружает сырые данные без обработки"""
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка загрузки данных: {e}")
        return {}

def load_data():
    """Загружает и обрабатывает данные"""
    try:
        ensure_data_file()
        
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Конвертация старой структуры
        if "user_stats" in data and "users" not in data:
            logger.info("Обнаружена старая структура user_stats, конвертирую...")
            data["users"] = data.pop("user_stats")
            for user_id, user_data in data["users"].items():
                if "count" in user_data:
                    user_data["total_shleps"] = user_data.pop("count")
                user_data.setdefault("max_damage", 0)
                user_data.setdefault("last_shlep", None)
                user_data.setdefault("damage_history", [])
                user_data.setdefault("chat_stats", {})
                user_data.setdefault("bonus_damage", 0)
            
            save_data(data)
        
        # Восстановление множеств из списков для timestamps
        if "timestamps" in data:
            for key, value in data["timestamps"].items():
                if "users" in value and isinstance(value["users"], list):
                    value["users"] = set(value["users"])
        
        return data
    except Exception as e:
        logger.error(f"Ошибка загрузки данных: {e}")
        return load_data_raw()

def save_data(data):
    """Сохраняет данные в файл"""
    try:
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        
        # Создаем копию для сериализации
        data_copy = json.loads(json.dumps(data, default=str))
        
        # Конвертируем множества в списки для сериализации
        if "timestamps" in data_copy:
            for key, value in data_copy["timestamps"].items():
                if "users" in value:
                    if hasattr(value["users"], '__iter__'):
                        value["users"] = list(value["users"])
        
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data_copy, f, ensure_ascii=False, indent=2)
        
        logger.debug(f"Данные сохранены в {DATA_FILE}")
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения данных: {e}")
        return False

# ========== Основные функции для работы с шлепами ==========

def add_shlep(user_id: int, username: str, damage: int, chat_id: Optional[int] = None) -> Tuple[int, int, int]:
    """Добавляет шлеп в статистику"""
    try:
        data = load_data()
        now = datetime.now().isoformat()
        user_id_str = str(user_id)
        
        # Инициализация пользователя
        if user_id_str not in data["users"]:
            data["users"][user_id_str] = {
                "username": username,
                "total_shleps": 0,
                "max_damage": 0,
                "last_shlep": now,
                "damage_history": [],
                "chat_stats": {},
                "bonus_damage": 0
            }
            data["global_stats"]["total_users"] = len(data["users"])
        
        user = data["users"][user_id_str]
        user["username"] = username
        user.setdefault("total_shleps", 0)
        user.setdefault("max_damage", 0)
        user.setdefault("last_shlep", now)
        user.setdefault("damage_history", [])
        user.setdefault("chat_stats", {})
        user.setdefault("bonus_damage", 0)
        
        user["total_shleps"] += 1
        user["last_shlep"] = now
        
        if damage > user["max_damage"]:
            user["max_damage"] = damage
        
        user["damage_history"].append({
            "damage": damage,
            "timestamp": now,
            "chat_id": chat_id
        })
        
        if len(user["damage_history"]) > 100:
            user["damage_history"] = user["damage_history"][-100:]
        
        # Обработка статистики по чату
        if chat_id:
            chat_id_str = str(chat_id)
            
            if chat_id_str not in data["chats"]:
                data["chats"][chat_id_str] = {
                    "total_shleps": 0,
                    "users": {},
                    "max_damage": 0,
                    "max_damage_user": None,
                    "max_damage_date": None
                }
            
            chat = data["chats"][chat_id_str]
            chat["total_shleps"] += 1
            
            if user_id_str not in chat["users"]:
                chat["users"][user_id_str] = {
                    "username": username,
                    "total_shleps": 0,
                    "max_damage": 0
                }
            
            chat_user = chat["users"][user_id_str]
            chat_user["username"] = username
            chat_user.setdefault("total_shleps", 0)
            chat_user.setdefault("max_damage", 0)
            
            chat_user["total_shleps"] += 1
            
            if damage > chat_user["max_damage"]:
                chat_user["max_damage"] = damage
            
            if damage > chat["max_damage"]:
                chat["max_damage"] = damage
                chat["max_damage_user"] = username
                chat["max_damage_date"] = now
            
            if chat_id_str not in user["chat_stats"]:
                user["chat_stats"][chat_id_str] = {
                    "total_shleps": 0,
                    "max_damage": 0
                }
            
            user_chat_stats = user["chat_stats"][chat_id_str]
            user_chat_stats.setdefault("total_shleps", 0)
            user_chat_stats.setdefault("max_damage", 0)
            
            user_chat_stats["total_shleps"] += 1
            if damage > user_chat_stats["max_damage"]:
                user_chat_stats["max_damage"] = damage
        
        # Обновление глобальной статистики
        data["global_stats"]["total_shleps"] += 1
        data["global_stats"]["last_shlep"] = now
        
        if damage > data["global_stats"]["max_damage"]:
            data["global_stats"]["max_damage"] = damage
            data["global_stats"]["max_damage_user"] = username
            data["global_stats"]["max_damage_date"] = now
        
        # Обновление временных меток
        date_key = datetime.now().strftime("%Y-%m-%d")
        hour_key = datetime.now().strftime("%Y-%m-%d %H:00")
        
        if date_key not in data["timestamps"]:
            data["timestamps"][date_key] = {"count": 0, "users": set()}
        if hour_key not in data["timestamps"]:
            data["timestamps"][hour_key] = {"count": 0, "users": set()}
        
        data["timestamps"][date_key]["count"] += 1
        data["timestamps"][date_key]["users"].add(user_id_str)
        data["timestamps"][hour_key]["count"] += 1
        data["timestamps"][hour_key]["users"].add(user_id_str)
        
        # Добавление в рекорды если урон >= 30
        if damage >= 30:
            record = {
                "user_id": user_id,
                "username": username,
                "damage": damage,
                "timestamp": now,
                "chat_id": chat_id
            }
            data["records"].append(record)
            
            if len(data["records"]) > 100:
                data["records"] = data["records"][-100:]
        
        save_data(data)
        
        return (
            data["global_stats"]["total_shleps"],
            user["total_shleps"],
            user["max_damage"]
        )
        
    except Exception as e:
        logger.error(f"Ошибка в add_shlep: {e}", exc_info=True)
        # Возвращаем значения по умолчанию при ошибке
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
    """Получает топ пользователей по количеству шлепов"""
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
    """Получает статистику конкретного пользователя"""
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
        
        max_damage_date = chat_data.get("max_damage_date")
        
        return {
            "total_users": len(chat_data.get("users", {})),
            "total_shleps": chat_data.get("total_shleps", 0),
            "max_damage": chat_data.get("max_damage", 0),
            "max_damage_user": chat_data.get("max_damage_user"),
            "max_damage_date": datetime.fromisoformat(max_damage_date) if max_damage_date else None
        }
    except Exception as e:
        logger.error(f"Ошибка в get_chat_stats: {e}")
        return {}

def get_chat_top_users(chat_id: int, limit: int = 10) -> List[Tuple[str, int]]:
    """Получает топ пользователей в конкретном чате"""
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
    """Создает резервную копию базы данных"""
    try:
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(BACKUP_DIR, f"mishok_backup_{timestamp}.json")
        
        shutil.copy2(DATA_FILE, backup_file)
        
        # Удаляем старые бэкапы (оставляем последние 10)
        backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith('.json')])
        if len(backups) > 10:
            for old_backup in backups[:-10]:
                os.remove(os.path.join(BACKUP_DIR, old_backup))
        
        logger.info(f"Создан бэкап: {backup_file}")
        return True, f"Бэкап создан: {backup_file}"
    except Exception as e:
        logger.error(f"Ошибка создания бэкапа: {e}")
        return False, str(e)

def get_activity_stats(days: int = 7) -> Dict[str, Any]:
    """Получает статистику активности за указанное количество дней"""
    try:
        data = load_data()
        
        if "timestamps" not in data:
            return {"daily": [], "hourly": {}, "active_users": 0}
        
        timestamps = data["timestamps"]
        now = datetime.now()
        
        # Статистика по дням
        daily_stats = []
        for i in range(days):
            date = (now - timedelta(days=i)).strftime("%Y-%m-%d")
            if date in timestamps:
                users_list = timestamps[date]["users"]
                if isinstance(users_list, set):
                    users_count = len(users_list)
                elif isinstance(users_list, list):
                    users_count = len(set(users_list))
                else:
                    users_count = 0
                    
                daily_stats.append({
                    "date": date,
                    "count": timestamps[date]["count"],
                    "users": users_count
                })
            else:
                daily_stats.append({
                    "date": date,
                    "count": 0,
                    "users": 0
                })
        
        daily_stats.reverse()
        
        # Статистика по часам (текущий день)
        hourly_stats = {}
        for i in range(24):
            hour_key = now.strftime(f"%Y-%m-%d {i:02d}:00")
            if hour_key in timestamps:
                hourly_stats[f"{i:02d}:00"] = timestamps[hour_key]["count"]
            else:
                hourly_stats[f"{i:02d}:00"] = 0
        
        # Уникальные пользователи за период
        all_users = set()
        for i in range(days):
            date = (now - timedelta(days=i)).strftime("%Y-%m-%d")
            if date in timestamps:
                users_data = timestamps[date]["users"]
                if isinstance(users_data, set):
                    all_users.update(users_data)
                elif isinstance(users_data, list):
                    all_users.update(users_data)
        
        return {
            "daily": daily_stats,
            "hourly": hourly_stats,
            "active_users": len(all_users)
        }
    except Exception as e:
        logger.error(f"Ошибка в get_activity_stats: {e}")
        return {"daily": [], "hourly": {}, "active_users": 0}

def get_user_activity(user_id: int, days: int = 14) -> Dict[str, Any]:
    """Получает статистику активности конкретного пользователя"""
    try:
        data = load_data()
        
        user_data = data["users"].get(str(user_id))
        if not user_data or "damage_history" not in user_data:
            return {"daily": [], "hourly": {}, "total": 0}
        
        now = datetime.now()
        user_history = user_data["damage_history"]
        
        daily_counts = {}
        hourly_counts = {}
        
        for record in user_history:
            try:
                record_time = datetime.fromisoformat(record["timestamp"])
                days_diff = (now - record_time).days
                
                if days_diff <= days:
                    date_key = record_time.strftime("%Y-%m-%d")
                    hour_key = record_time.strftime("%H:00")
                    
                    daily_counts[date_key] = daily_counts.get(date_key, 0) + 1
                    hourly_counts[hour_key] = hourly_counts.get(hour_key, 0) + 1
            except:
                continue
        
        # Форматируем статистику по дням
        daily_stats = []
        for i in range(days):
            date = (now - timedelta(days=i)).strftime("%Y-%m-%d")
            daily_stats.append({
                "date": date,
                "count": daily_counts.get(date, 0)
            })
        
        daily_stats.reverse()
        
        # Форматируем статистику по часам
        formatted_hourly = {}
        for hour in range(24):
            hour_key = f"{hour:02d}:00"
            formatted_hourly[hour_key] = hourly_counts.get(hour_key, 0)
        
        return {
            "daily": daily_stats,
            "hourly": formatted_hourly,
            "total": len(user_history)
        }
    except Exception as e:
        logger.error(f"Ошибка в get_user_activity: {e}")
        return {"daily": [], "hourly": {}, "total": 0}

def check_data_integrity():
    """Проверяет целостность данных"""
    try:
        data = load_data()
        
        errors = []
        warnings = []
        
        # Проверка обязательных ключей
        required_keys = ["users", "chats", "global_stats", "timestamps", "records"]
        for key in required_keys:
            if key not in data:
                errors.append(f"Отсутствует обязательный ключ: {key}")
        
        # Проверка чатов на дубликаты пользователей
        for chat_id, chat_data in data.get("chats", {}).items():
            user_ids = list(chat_data.get("users", {}).keys())
            if len(user_ids) != len(set(user_ids)):
                warnings.append(f"Чат {chat_id}: обнаружены дубликаты пользователей")
        
        # Проверка структуры пользователей
        for user_id, user_data in data.get("users", {}).items():
            required_user_keys = ["username", "total_shleps", "max_damage", "last_shlep", "damage_history", "chat_stats"]
            missing_keys = []
            for key in required_user_keys:
                if key not in user_data:
                    missing_keys.append(key)
            
            if missing_keys:
                warnings.append(f"Пользователь {user_id}: отсутствуют ключи {missing_keys}")
        
        # Проверка согласованности счетчиков
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

# ========== Функции для работы с дуэлями ==========

def create_duel_invite(challenger_id: int, challenger_name: str, 
                       target_id: int, target_name: str, chat_id: int = None):
    """Создает приглашение на дуэль"""
    try:
        data = load_data()
        
        # Генерируем уникальный ID дуэли
        timestamp = int(datetime.now().timestamp())
        random_suffix = random.randint(1000, 9999)
        duel_id = f"{challenger_id}_{timestamp}_{random_suffix}"
        
        invite = {
            "id": duel_id,
            "challenger_id": challenger_id,
            "challenger_name": challenger_name,
            "target_id": target_id,
            "target_name": target_name,
            "chat_id": chat_id,
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(minutes=5)).isoformat(),
            "status": "pending"
        }
        
        # Инициализируем структуру duels если её нет
        if "duels" not in data:
            data["duels"] = {
                "active": {},
                "invites": {},
                "history": []
            }
        
        data["duels"].setdefault("invites", {})[duel_id] = invite
        save_data(data)
        
        logger.info(f"Создано приглашение на дуэль: {duel_id}, challenger: {challenger_name}, target: {target_name}")
        return duel_id
    except Exception as e:
        logger.error(f"Ошибка создания приглашения на дуэль: {e}", exc_info=True)
        return None

def accept_duel_invite(duel_id: str, target_id: int = None, target_name: str = None):
    """Принимает приглашение на дуэль"""
    try:
        data = load_data()
        
        # Используем безопасные функции
        invites = get_duel_invites_safe(data)
        
        if duel_id not in invites:
            logger.warning(f"Приглашение на дуэль не найдено: {duel_id}")
            return None
        
        invite = invites[duel_id]
        
        # Обновляем информацию о цели если передана
        if target_id:
            invite["target_id"] = target_id
        if target_name:
            invite["target_name"] = target_name
        
        # Проверяем target_id
        if invite.get("target_id") in [0, None, ""]:
            logger.warning(f"Target ID не установлен для дуэли {duel_id}: {invite.get('target_id')}")
            return None
        
        # Проверяем не просрочено ли приглашение
        expires_at = datetime.fromisoformat(invite["expires_at"])
        if datetime.now() > expires_at:
            logger.warning(f"Приглашение на дуэль просрочено: {duel_id}")
            # Автоматически перемещаем в историю как просроченное
            invite["status"] = "expired"
            invite["ended_at"] = datetime.now().isoformat()
            
            # Инициализируем историю если её нет
            if "history" not in data.setdefault("duels", {}):
                data["duels"]["history"] = []
            
            data["duels"]["history"].append(invite)
            del data["duels"]["invites"][duel_id]
            save_data(data)
            return None
        
        active_duel = {
            "id": duel_id,
            "challenger_id": invite["challenger_id"],
            "challenger_name": invite["challenger_name"],
            "challenger_damage": 0,
            "challenger_shleps": 0,
            "target_id": invite["target_id"],
            "target_name": invite["target_name"],
            "target_damage": 0,
            "target_shleps": 0,
            "chat_id": invite["chat_id"],
            "message_id": None,
            "started_at": datetime.now().isoformat(),
            "ends_at": (datetime.now() + timedelta(minutes=5)).isoformat(),
            "winner": None,
            "reward": random.randint(15, 40),
            "history": []
        }
        
        # Инициализируем структуру active если её нет
        data.setdefault("duels", {}).setdefault("active", {})[duel_id] = active_duel
        
        # Удаляем из invites
        if duel_id in data["duels"].get("invites", {}):
            del data["duels"]["invites"][duel_id]
        
        save_data(data)
        
        logger.info(f"Дуэль начата: {duel_id}, {invite['challenger_name']} vs {invite['target_name']}")
        return active_duel
    except Exception as e:
        logger.error(f"Ошибка принятия приглашения на дуэль: {e}", exc_info=True)
        return None

def decline_duel_invite(duel_id: str, user_id: int = None, user_name: str = None):
    """Отклоняет приглашение на дуэль"""
    try:
        data = load_data()
        
        # Используем безопасные функции
        invites = get_duel_invites_safe(data)
        
        if duel_id not in invites:
            logger.warning(f"Приглашение на дуэль не найдено для отклонения: {duel_id}")
            return False
        
        invite = invites[duel_id]
        invite["status"] = "declined"
        invite["ended_at"] = datetime.now().isoformat()
        
        if user_id:
            invite["declined_by_id"] = user_id
        if user_name:
            invite["declined_by"] = user_name
        
        # Инициализируем историю если её нет
        history = get_duel_history_safe(data)
        history.append(invite)
        data.setdefault("duels", {})["history"] = history
        
        # Удаляем из invites
        if duel_id in data["duels"].get("invites", {}):
            del data["duels"]["invites"][duel_id]
        
        save_data(data)
        logger.info(f"Дуэль отклонена: {duel_id}")
        return True
    except Exception as e:
        logger.error(f"Ошибка отклонения приглашения на дуэль: {e}", exc_info=True)
        return False

def get_active_duel(duel_id: str):
    """Получает активную дуэль по ID"""
    try:
        data = load_data()
        
        # Используем безопасные функции
        active_duels = get_active_duels_safe(data)
        return active_duels.get(duel_id)
    except Exception as e:
        logger.error(f"Ошибка получения активной дуэли: {e}")
        return None

def add_shlep_to_duel(duel_id: str, user_id: int, damage: int):
    """Добавляет шлеп в активную дуэль"""
    try:
        data = load_data()
        
        # Используем безопасные функции
        active_duels = get_active_duels_safe(data)
        
        if duel_id not in active_duels:
            return None
        
        duel = active_duels[duel_id]
        
        action = {
            "user_id": user_id,
            "damage": damage,
            "timestamp": datetime.now().isoformat()
        }
        
        if user_id == duel["challenger_id"]:
            duel["challenger_damage"] += damage
            duel["challenger_shleps"] += 1
            action["user_name"] = duel["challenger_name"]
            action["side"] = "challenger"
        elif user_id == duel["target_id"]:
            duel["target_damage"] += damage
            duel["target_shleps"] += 1
            action["user_name"] = duel["target_name"]
            action["side"] = "target"
        else:
            return None
        
        duel["history"].append(action)
        if len(duel["history"]) > 50:
            duel["history"] = duel["history"][-50:]
        
        ends_at = datetime.fromisoformat(duel["ends_at"])
        if datetime.now() >= ends_at:
            return finish_duel(duel_id)
        
        save_data(data)
        
        return {
            "duel": duel,
            "is_finished": False
        }
    except Exception as e:
        logger.error(f"Ошибка добавления шлёпка в дуэль: {e}")
        return None

def finish_duel(duel_id: str):
    """Завершает дуэль и определяет победителя"""
    try:
        data = load_data()
        
        # Используем безопасные функции
        active_duels = get_active_duels_safe(data)
        
        if duel_id not in active_duels:
            return None
        
        duel = active_duels[duel_id]
        
        if duel["challenger_damage"] > duel["target_damage"]:
            winner_id = duel["challenger_id"]
            winner_name = duel["challenger_name"]
            loser_id = duel["target_id"]
            winner_damage = duel["challenger_damage"]
            loser_damage = duel["target_damage"]
        elif duel["target_damage"] > duel["challenger_damage"]:
            winner_id = duel["target_id"]
            winner_name = duel["target_name"]
            loser_id = duel["challenger_id"]
            winner_damage = duel["target_damage"]
            loser_damage = duel["challenger_damage"]
        else:
            winner_id = None
            winner_name = None
            winner_damage = duel["challenger_damage"]
            loser_damage = duel["target_damage"]
        
        # Награда победителю
        if winner_id and str(winner_id) in data["users"]:
            user = data["users"][str(winner_id)]
            user.setdefault("bonus_damage", 0)
            user["bonus_damage"] = user.get("bonus_damage", 0) + duel["reward"]
        
        duel["winner_id"] = winner_id
        duel["winner_name"] = winner_name if winner_id else None
        duel["finished_at"] = datetime.now().isoformat()
        duel["winner_damage"] = winner_damage if winner_id else winner_damage
        duel["loser_damage"] = loser_damage if winner_id else loser_damage
        
        result = {
            "winner_id": winner_id,
            "winner_name": winner_name if winner_id else None,
            "challenger_damage": duel["challenger_damage"],
            "target_damage": duel["target_damage"],
            "challenger_shleps": duel["challenger_shleps"],
            "target_shleps": duel["target_shleps"],
            "reward": duel["reward"] if winner_id else 0,
            "is_draw": winner_id is None
        }
        
        # Инициализируем историю если её нет
        history = get_duel_history_safe(data)
        history.append(duel)
        data.setdefault("duels", {})["history"] = history
        
        # Удаляем из активных
        if duel_id in data["duels"].get("active", {}):
            del data["duels"]["active"][duel_id]
        
        save_data(data)
        
        logger.info(f"Дуэль завершена: {duel_id}, победитель: {winner_name if winner_id else 'Ничья'}")
        return result
    except Exception as e:
        logger.error(f"Ошибка завершения дуэли: {e}")
        return None

def surrender_duel(duel_id: str, user_id: int):
    """Сдача в дуэли"""
    try:
        data = load_data()
        
        # Используем безопасные функции
        active_duels = get_active_duels_safe(data)
        
        if duel_id not in active_duels:
            return None
        
        duel = active_duels[duel_id]
        
        if user_id == duel["challenger_id"]:
            winner_id = duel["target_id"]
            winner_name = duel["target_name"]
            surrenderer_name = duel["challenger_name"]
            winner_damage = duel["target_damage"]
            surrenderer_damage = duel["challenger_damage"]
        else:
            winner_id = duel["challenger_id"]
            winner_name = duel["challenger_name"]
            surrenderer_name = duel["target_name"]
            winner_damage = duel["challenger_damage"]
            surrenderer_damage = duel["target_damage"]
        
        # Уменьшенная награда при сдаче
        if str(winner_id) in data["users"]:
            user = data["users"][str(winner_id)]
            user.setdefault("bonus_damage", 0)
            user["bonus_damage"] = user.get("bonus_damage", 0) + (duel["reward"] // 2)
        
        result = {
            "winner_id": winner_id,
            "winner_name": winner_name,
            "surrenderer_name": surrenderer_name,
            "winner_damage": winner_damage,
            "surrenderer_damage": surrenderer_damage,
            "reward": duel["reward"] // 2
        }
        
        duel["winner_id"] = winner_id
        duel["winner_name"] = winner_name
        duel["surrenderer_id"] = user_id
        duel["surrenderer_name"] = surrenderer_name
        duel["finished_at"] = datetime.now().isoformat()
        duel["ended_by"] = "surrender"
        
        # Инициализируем историю если её нет
        history = get_duel_history_safe(data)
        history.append(duel)
        data.setdefault("duels", {})["history"] = history
        
        # Удаляем из активных
        if duel_id in data["duels"].get("active", {}):
            del data["duels"]["active"][duel_id]
        
        save_data(data)
        
        logger.info(f"Дуэль сдана: {duel_id}, сдался: {surrenderer_name}, победитель: {winner_name}")
        return result
    except Exception as e:
        logger.error(f"Ошибка при сдаче в дуэли: {e}")
        return None

def get_user_active_duel(user_id: int):
    """Получает активную дуэль пользователя"""
    try:
        data = load_data()
        
        # Используем безопасные функции
        active_duels = get_active_duels_safe(data)
        
        for duel_id, duel in active_duels.items():
            if duel.get("challenger_id") == user_id or duel.get("target_id") == user_id:
                return duel
        
        return None
    except Exception as e:
        logger.error(f"Ошибка получения активной дуэли пользователя: {e}", exc_info=True)
        return None

def cleanup_expired_duels():
    """Очищает просроченные дуэли и приглашения"""
    try:
        data = load_data()
        
        if "duels" not in data:
            return 0
        
        now = datetime.now()
        cleaned = 0
        
        # Используем безопасные функции
        invites = get_duel_invites_safe(data)
        active_duels = get_active_duels_safe(data)
        
        # Очистка просроченных приглашений
        expired_invites = []
        for duel_id, invite in invites.items():
            expires_at = datetime.fromisoformat(invite["expires_at"])
            if now >= expires_at:
                invite["status"] = "expired"
                invite["ended_at"] = now.isoformat()
                
                # Инициализируем историю если её нет
                history = get_duel_history_safe(data)
                history.append(invite)
                data.setdefault("duels", {})["history"] = history
                
                expired_invites.append(duel_id)
                cleaned += 1
        
        for duel_id in expired_invites:
            if duel_id in data["duels"].get("invites", {}):
                del data["duels"]["invites"][duel_id]
        
        # Очистка просроченных дуэлей
        expired_duels = []
        for duel_id, duel in active_duels.items():
            ends_at = datetime.fromisoformat(duel["ends_at"])
            if now >= ends_at:
                finish_duel(duel_id)
                expired_duels.append(duel_id)
                cleaned += 1
        
        for duel_id in expired_duels:
            if duel_id in data["duels"].get("active", {}):
                del data["duels"]["active"][duel_id]
        
        if cleaned > 0:
            save_data(data)
            logger.info(f"Очищено {cleaned} просроченных дуэлей и приглашений")
        
        return cleaned
    except Exception as e:
        logger.error(f"Ошибка очистки просроченных дуэлей: {e}")
        return 0

def update_duel_message_id(duel_id: str, message_id: int):
    """Обновляет ID сообщения дуэли"""
    try:
        data = load_data()
        
        # Используем безопасные функции
        active_duels = get_active_duels_safe(data)
        
        if duel_id not in active_duels:
            return False
        
        data["duels"]["active"][duel_id]["message_id"] = message_id
        save_data(data)
        
        return True
    except Exception as e:
        logger.error(f"Ошибка обновления ID сообщения дуэли: {e}")
        return False

# ========== Инициализация ==========
logger.info("База данных готова к работе")
