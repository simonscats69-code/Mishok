import json
import os
from datetime import datetime
import logging
from typing import Optional, Tuple, List, Any, Dict
import shutil
from datetime import timedelta

logger = logging.getLogger(__name__)

DATA_FILE = "data/mishok_data.json"
BACKUP_DIR = "data/backups"

def ensure_data_file():
    if not os.path.exists(DATA_FILE):
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        default_data = {
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
            "records": []
        }
        save_data(default_data)
        logger.info(f"Создан новый файл данных: {DATA_FILE}")
        return default_data
    else:
        try:
            data = load_data_raw()
            needs_fix = False
            
            required_keys = ["users", "chats", "global_stats", "timestamps", "records"]
            for key in required_keys:
                if key not in data:
                    logger.warning(f"В файле данных отсутствует ключ: {key}")
                    needs_fix = True
            
            if "user_stats" in data and "users" not in data:
                logger.warning("Обнаружена старая структура данных (user_stats)")
                needs_fix = True
            
            if needs_fix:
                logger.info("Файл данных требует исправления структуры")
                return fix_data_structure(data)
            else:
                logger.info(f"Файл данных найден и структура корректна: {DATA_FILE}")
                return data
                
        except Exception as e:
            logger.error(f"Ошибка проверки файла данных: {e}")
            return create_new_data_file()

def repair_data_structure():
    data = load_data()
    
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
    
    for user_id, user_data in data["users"].items():
        user_data.setdefault("username", f"User_{user_id}")
        user_data.setdefault("total_shleps", user_data.get("count", 0))
        user_data.setdefault("max_damage", 0)
        user_data.setdefault("last_shlep", None)
        user_data.setdefault("damage_history", [])
        user_data.setdefault("chat_stats", {})
        
        if "count" in user_data:
            del user_data["count"]
    
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

def repair_data_structure_and_load():
    try:
        backup_database()
        
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        
        repair_data_structure()
        
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка восстановления данных: {e}")
        return create_new_data_file()

def load_data_raw():
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка загрузки данных: {e}")
        return {}

def fix_data_structure(old_data):
    logger.info("Исправление структуры данных...")
    
    new_data = {
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
        "records": []
    }
    
    if "user_stats" in old_data:
        for user_id_str, user_info in old_data["user_stats"].items():
            new_data["users"][user_id_str] = {
                "username": user_info.get("username", f"User_{user_id_str}"),
                "total_shleps": user_info.get("count", user_info.get("total_shleps", 0)),
                "max_damage": 0,
                "last_shlep": user_info.get("last_shlep"),
                "damage_history": [],
                "chat_stats": {}
            }
    elif "users" in old_data:
        for user_id_str, user_info in old_data["users"].items():
            new_data["users"][user_id_str] = {
                "username": user_info.get("username", f"User_{user_id_str}"),
                "total_shleps": user_info.get("total_shleps", user_info.get("count", 0)),
                "max_damage": user_info.get("max_damage", 0),
                "last_shlep": user_info.get("last_shlep"),
                "damage_history": user_info.get("damage_history", []),
                "chat_stats": user_info.get("chat_stats", {})
            }
    
    if "chat_stats" in old_data:
        for chat_id_str, chat_info in old_data["chat_stats"].items():
            new_data["chats"][chat_id_str] = {
                "total_shleps": chat_info.get("total_shleps", 0),
                "users": {},
                "max_damage": chat_info.get("max_damage", 0),
                "max_damage_user": chat_info.get("max_damage_user"),
                "max_damage_date": chat_info.get("max_damage_date")
            }
            
            if "users" in chat_info:
                seen_users = {}
                for uid, user_data in chat_info["users"].items():
                    if uid not in seen_users:
                        seen_users[uid] = {
                            "username": user_data.get("username", f"User_{uid}"),
                            "total_shleps": user_data.get("count", user_data.get("total_shleps", 0)),
                            "max_damage": user_data.get("max_damage", 0)
                        }
                    else:
                        seen_users[uid]["total_shleps"] += user_data.get("count", user_data.get("total_shleps", 0))
                
                new_data["chats"][chat_id_str]["users"] = seen_users
    
    if "global_stats" in old_data:
        new_data["global_stats"] = {
            "total_shleps": old_data["global_stats"].get("total_shleps", 0),
            "last_shlep": old_data["global_stats"].get("last_shlep"),
            "max_damage": old_data["global_stats"].get("max_damage", 0),
            "max_damage_user": old_data["global_stats"].get("max_damage_user"),
            "max_damage_date": old_data["global_stats"].get("max_damage_date"),
            "total_users": len(new_data["users"])
        }
    else:
        total_shleps = sum(user.get("total_shleps", 0) for user in new_data["users"].values())
        new_data["global_stats"]["total_shleps"] = total_shleps
        new_data["global_stats"]["total_users"] = len(new_data["users"])
    
    save_data(new_data)
    logger.info("Структура данных исправлена")
    return new_data

def create_new_data_file():
    default_data = {
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
        "records": []
    }
    save_data(default_data)
    logger.info(f"Создан новый файл данных: {DATA_FILE}")
    return default_data

def load_data():
    try:
        ensure_data_file()
        
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        needs_repair = False
        
        required_keys = ["users", "chats", "global_stats", "timestamps", "records"]
        for key in required_keys:
            if key not in data:
                needs_repair = True
                break
        
        if needs_repair:
            logger.warning("Обнаружена поврежденная структура данных, восстанавливаю...")
            return repair_data_structure_and_load()
        
        if "timestamps" in data:
            for key, value in data["timestamps"].items():
                if "users" in value and isinstance(value["users"], list):
                    value["users"] = set(value["users"])
        
        return data
    except Exception as e:
        logger.error(f"Ошибка загрузки данных: {e}")
        return repair_data_structure_and_load()

def save_data(data):
    try:
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        
        data_copy = json.loads(json.dumps(data, default=str))
        
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

def add_shlep(user_id: int, username: str, damage: int, chat_id: Optional[int] = None) -> Tuple[int, int, int]:
    data = load_data()
    now = datetime.now().isoformat()
    
    user_id_str = str(user_id)
    
    if user_id_str not in data["users"]:
        data["users"][user_id_str] = {
            "username": username,
            "total_shleps": 0,
            "max_damage": 0,
            "last_shlep": now,
            "damage_history": [],
            "chat_stats": {}
        }
        data["global_stats"]["total_users"] = len(data["users"])
    
    user = data["users"][user_id_str]
    
    user["username"] = username
    user.setdefault("total_shleps", 0)
    user.setdefault("max_damage", 0)
    user.setdefault("last_shlep", now)
    user.setdefault("damage_history", [])
    user.setdefault("chat_stats", {})
    
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
    
    data["global_stats"]["total_shleps"] += 1
    data["global_stats"]["last_shlep"] = now
    
    if damage > data["global_stats"]["max_damage"]:
        data["global_stats"]["max_damage"] = damage
        data["global_stats"]["max_damage_user"] = username
        data["global_stats"]["max_damage_date"] = now
    
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

def get_stats() -> Tuple[int, Optional[datetime], int, Optional[str], Optional[datetime]]:
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

def get_top_users(limit: int = 10) -> List[Tuple[str, int]]:
    data = load_data()
    
    users_list = []
    for user_id, user_data in data["users"].items():
        username = user_data.get("username", f"Игрок_{user_id}")
        total = user_data.get("total_shleps", 0)
        users_list.append((username, total))
    
    users_list.sort(key=lambda x: x[1], reverse=True)
    return users_list[:limit]

def get_user_stats(user_id: int) -> Tuple[Optional[str], int, Optional[datetime]]:
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

def get_chat_stats(chat_id: int) -> Dict[str, Any]:
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

def get_chat_top_users(chat_id: int, limit: int = 10) -> List[Tuple[str, int]]:
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

def backup_database():
    try:
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(BACKUP_DIR, f"mishok_backup_{timestamp}.json")
        
        shutil.copy2(DATA_FILE, backup_file)
        
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
    data = load_data()
    
    if "timestamps" not in data:
        return {"daily": [], "hourly": {}, "active_users": 0}
    
    timestamps = data["timestamps"]
    now = datetime.now()
    
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
    
    hourly_stats = {}
    for i in range(24):
        hour_key = now.strftime(f"%Y-%m-%d {i:02d}:00")
        if hour_key in timestamps:
            hourly_stats[f"{i:02d}:00"] = timestamps[hour_key]["count"]
        else:
            hourly_stats[f"{i:02d}:00"] = 0
    
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

def get_user_activity(user_id: int, days: int = 14) -> Dict[str, Any]:
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
    
    daily_stats = []
    for i in range(days):
        date = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        daily_stats.append({
            "date": date,
            "count": daily_counts.get(date, 0)
        })
    
    daily_stats.reverse()
    
    formatted_hourly = {}
    for hour in range(24):
        hour_key = f"{hour:02d}:00"
        formatted_hourly[hour_key] = hourly_counts.get(hour_key, 0)
    
    return {
        "daily": daily_stats,
        "hourly": formatted_hourly,
        "total": len(user_history)
    }

def check_data_integrity():
    data = load_data()
    
    errors = []
    warnings = []
    
    required_keys = ["users", "chats", "global_stats", "timestamps", "records"]
    for key in required_keys:
        if key not in data:
            errors.append(f"Отсутствует обязательный ключ: {key}")
    
    for chat_id, chat_data in data.get("chats", {}).items():
        user_ids = list(chat_data.get("users", {}).keys())
        if len(user_ids) != len(set(user_ids)):
            warnings.append(f"Чат {chat_id}: обнаружены дубликаты пользователей")
    
    for user_id, user_data in data.get("users", {}).items():
        required_user_keys = ["username", "total_shleps", "max_damage", "last_shlep", "damage_history", "chat_stats"]
        missing_keys = []
        for key in required_user_keys:
            if key not in user_data:
                missing_keys.append(key)
        
        if missing_keys:
            warnings.append(f"Пользователь {user_id}: отсутствуют ключи {missing_keys}")
    
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

def migrate_old_data():
    logger.info("Проверка структуры данных...")
    ensure_data_file()
    logger.info("Проверка завершена")

migrate_old_data()
logger.info("База данных готова к работе")
