import json
import os
from datetime import datetime, timedelta
import logging
from typing import Optional, Tuple, List, Any, Dict
import shutil
import random

logger = logging.getLogger(__name__)

from config import DATA_FILE, VOTES_FILE, BACKUP_PATH, BACKUP_ENABLED, BACKUP_RETENTION_DAYS, MAX_USER_HISTORY

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.dirname(DATA_FILE)
BACKUP_DIR = BACKUP_PATH

def ensure_votes_file():
    try:
        if not os.path.exists(VOTES_FILE):
            os.makedirs(os.path.dirname(VOTES_FILE), exist_ok=True)
            with open(VOTES_FILE, 'w', encoding='utf-8') as f:
                json.dump({}, f)
    except Exception as e:
        logger.error(f"Ошибка создания файла голосований: {e}")

def save_vote_data(vote_data):
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
    ensure_votes_file()
    try:
        with open(VOTES_FILE, 'r', encoding='utf-8') as f:
            all_votes = json.load(f)
        return all_votes.get(vote_id)
    except Exception as e:
        logger.error(f"Ошибка чтения голосования: {e}")
        return None

def get_all_votes():
    ensure_votes_file()
    try:
        with open(VOTES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка чтения всех голосований: {e}")
        return {}

def delete_vote_data(vote_id):
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
                    finished_at_str = vote_data.get("finished_at")
                    
                    if finished and finished_at_str:
                        finished_at = datetime.fromisoformat(finished_at_str)
                        if (now - finished_at).days > 1:
                            expired.append(vote_id)
                    elif not finished and now > ends_at + timedelta(days=1):
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

def restore_from_backup():
    try:
        if not os.path.exists(BACKUP_DIR):
            logger.warning("Директория бэкапов не существует")
            return create_default_data()
        
        backups = []
        for filename in os.listdir(BACKUP_DIR):
            if filename.endswith('.json') and 'backup' in filename:
                filepath = os.path.join(BACKUP_DIR, filename)
                mtime = os.path.getmtime(filepath)
                backups.append((filepath, mtime))
        
        if backups:
            backups.sort(key=lambda x: x[1], reverse=True)
            latest_backup = backups[0][0]
            
            logger.info(f"Восстанавливаю из бэкапа: {latest_backup}")
            
            with open(latest_backup, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            save_data(data)
            logger.info("Восстановление завершено")
            return data
        
        logger.warning("Бэкапы не найдены")
        return create_default_data()
        
    except Exception as e:
        logger.error(f"Ошибка восстановления из бэкапа: {e}")
        return create_default_data()

def create_default_data():
    return {
        "version": "2.0",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
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

def convert_old_structure(data):
    if "user_stats" in data and "users" not in data:
        data["users"] = data.pop("user_stats")
        for user_id, user_data in data["users"].items():
            if "count" in user_data:
                user_data["total_shleps"] = user_data.pop("count")
            user_data.setdefault("max_damage", 0)
            user_data.setdefault("last_shlep", None)
            user_data.setdefault("damage_history", [])
            user_data.setdefault("chat_stats", {})
            user_data.setdefault("bonus_damage", 0)
    
    data["version"] = "2.0"
    data["updated_at"] = datetime.now().isoformat()
    
    return data

def ensure_data_file():
    try:
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        
        if not os.path.exists(DATA_FILE):
            default_data = create_default_data()
            save_data(default_data)
            logger.info(f"Создан новый файл данных: {DATA_FILE}")
            return default_data
        
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if "user_stats" in data and "users" not in data:
            logger.info("Обнаружена старая структура, конвертирую...")
            data = convert_old_structure(data)
            save_data(data)
        
        logger.info(f"Загружен файл данных: {DATA_FILE}")
        logger.info(f"   Пользователей: {len(data.get('users', {}))}")
        logger.info(f"   Шлёпков: {data.get('global_stats', {}).get('total_shleps', 0)}")
        
        return data
        
    except Exception as e:
        logger.error(f"Ошибка загрузки файла данных: {e}")
        return restore_from_backup()

def create_new_data_file():
    default_data = create_default_data()
    save_data(default_data)
    logger.info(f"Создан новый файл данных: {DATA_FILE}")
    return default_data

def repair_data_structure():
    try:
        data = load_data_raw()
        
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
            user_data.setdefault("bonus_damage", 0)
            
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
    except Exception as e:
        logger.error(f"Ошибка восстановления структуры данных: {e}")
        return False

def load_data_raw():
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка загрузки данных: {e}")
        return {}

def load_data():
    try:
        ensure_data_file()
        
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
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
        
        if "timestamps" in data:
            for key, value in data["timestamps"].items():
                if "users" in value and isinstance(value["users"], list):
                    value["users"] = set(value["users"])
        
        return data
    except Exception as e:
        logger.error(f"Ошибка загрузки данных: {e}")
        return load_data_raw()

def create_auto_backup():
    try:
        if not BACKUP_ENABLED:
            return
        
        os.makedirs(BACKUP_DIR, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(BACKUP_DIR, f"auto_backup_{timestamp}.json")
        
        if os.path.exists(DATA_FILE):
            shutil.copy2(DATA_FILE, backup_file)
            
            cleanup_old_backups()
            
            logger.debug(f"Автобэкап создан: {backup_file}")
    except Exception as e:
        logger.error(f"Ошибка создания автобэкапа: {e}")

def cleanup_old_backups():
    try:
        if not os.path.exists(BACKUP_DIR):
            return
        
        now = datetime.now()
        for filename in os.listdir(BACKUP_DIR):
            if filename.endswith('.json'):
                filepath = os.path.join(BACKUP_DIR, filename)
                mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                
                if (now - mtime).days > BACKUP_RETENTION_DAYS:
                    os.remove(filepath)
                    logger.debug(f"Удален старый бэкап: {filename}")
                    
    except Exception as e:
        logger.error(f"Ошибка очистки бэкапов: {e}")

def save_data(data):
    try:
        data["updated_at"] = datetime.now().isoformat()
        
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        
        data_copy = json.loads(json.dumps(data, default=str))
        
        if "timestamps" in data_copy:
            for key, value in data_copy["timestamps"].items():
                if "users" in value:
                    if hasattr(value["users"], '__iter__'):
                        value["users"] = list(value["users"])
        
        temp_file = DATA_FILE + ".tmp"
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(data_copy, f, ensure_ascii=False, indent=2)
        
        os.replace(temp_file, DATA_FILE)
        
        if BACKUP_ENABLED:
            create_auto_backup()
        
        logger.debug(f"Данные сохранены: {DATA_FILE}")
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения данных: {e}")
        return False

def add_shlep(user_id: int, username: str, damage: int, chat_id: Optional[int] = None) -> Tuple[int, int, int]:
    try:
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
        
        if len(user["damage_history"]) > MAX_USER_HISTORY:
            user["damage_history"] = user["damage_history"][-MAX_USER_HISTORY:]
        
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
        
    except Exception as e:
        logger.error(f"Ошибка в add_shlep: {e}", exc_info=True)
        return (0, 0, 0)

def get_stats() -> Tuple[int, Optional[datetime], int, Optional[str], Optional[datetime]]:
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
    try:
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
    except Exception as e:
        logger.error(f"Ошибка в get_activity_stats: {e}")
        return {"daily": [], "hourly": {}, "active_users": 0}

def get_user_activity(user_id: int, days: int = 14) -> Dict[str, Any]:
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
    except Exception as e:
        logger.error(f"Ошибка в get_user_activity: {e}")
        return {"daily": [], "hourly": {}, "total": 0}

def check_data_integrity():
    try:
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
    except Exception as e:
        logger.error(f"Ошибка в check_data_integrity: {e}")
        return {
            "errors": [f"Ошибка проверки: {str(e)}"],
            "warnings": [],
            "stats": {}
        }

logger.info("База данных готова к работе")

cleanup_expired_votes()
