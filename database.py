import json
import os
from datetime import datetime, timedelta
import logging
from typing import Optional, Tuple, List, Any, Dict
import shutil
import threading
import time

logger = logging.getLogger(__name__)

from config import DATA_FILE, BACKUP_PATH, BACKUP_ENABLED, AUTOSAVE_INTERVAL
from texts import DATABASE_TEXTS

_in_memory_data = None
_data_lock = threading.Lock()
_last_save_time = time.time()
_data_modified = False

def create_default_data():
    return {
        "version": "3.0",
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
        "records": [],
        "votes": {}
    }

def ensure_data_file():
    try:
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        
        if not os.path.exists(DATA_FILE):
            default_data = create_default_data()
            save_data_to_disk(default_data)
            logger.info(DATABASE_TEXTS['file_created'].format(file=DATA_FILE))
            return default_data
        
        return load_data_from_disk()
        
    except Exception as e:
        logger.error(f"Ошибка загрузки файла данных: {e}")
        return create_default_data()

def convert_old_structure(data):
    logger.info(DATABASE_TEXTS['converting'])
    
    for user_id, user_data in data.get("users", {}).items():
        if "damage_history" in user_data:
            del user_data["damage_history"]
        
        if "chat_stats" in user_data:
            del user_data["chat_stats"]
    
    if "timestamps" in data:
        for key in list(data["timestamps"].keys()):
            if isinstance(data["timestamps"][key], dict) and "count" in data["timestamps"][key]:
                data["timestamps"][key] = data["timestamps"][key]["count"]
    
    if "records" in data and len(data["records"]) > 5:
        data["records"] = data["records"][-5:]
    
    data["version"] = "3.0"
    data["updated_at"] = datetime.now().isoformat()
    
    return data

def load_data_from_disk():
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        version = data.get("version", "1.0")
        
        if version != "3.0":
            logger.info(f"Конвертируем данные с версии {version} на 3.0")
            data = convert_old_structure(data)
            save_data_to_disk(data)
        
        logger.info(DATABASE_TEXTS['file_loaded'].format(file=DATA_FILE))
        logger.info(DATABASE_TEXTS['users_count'].format(count=len(data.get('users', {}))))
        logger.info(DATABASE_TEXTS['shleps_count'].format(count=data.get('global_stats', {}).get('total_shleps', 0)))
        
        return data
        
    except Exception as e:
        logger.error(f"Ошибка загрузки файла данных: {e}")
        return create_default_data()

def repair_data_structure():
    try:
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
        data.setdefault("votes", {})
        
        for user_id, user_data in data["users"].items():
            user_data.setdefault("username", f"User_{user_id}")
            user_data.setdefault("total_shleps", 0)
            user_data.setdefault("max_damage", 0)
            user_data.setdefault("last_shlep", None)
            user_data.setdefault("bonus_damage", 0)
            
            user_data.pop("damage_history", None)
            user_data.pop("chat_stats", None)
            user_data.pop("count", None)
        
        for chat_id, chat_data in data["chats"].items():
            chat_data.setdefault("total_shleps", 0)
            chat_data.setdefault("users", {})
            
            for user_id, user_data in chat_data["users"].items():
                user_data.setdefault("username", f"User_{user_id}")
                user_data.setdefault("total_shleps", 0)
                user_data.pop("max_damage", None)
        
        data["global_stats"]["total_users"] = len(data["users"])
        
        save_data(data)
        logger.info(DATABASE_TEXTS['structure_repaired'])
        return True
    except Exception as e:
        logger.error(DATABASE_TEXTS['repair_error'].format(error=e))
        return False

def load_data():
    global _in_memory_data
    
    with _data_lock:
        if _in_memory_data is None:
            _in_memory_data = ensure_data_file()
        return _in_memory_data.copy()

def save_data_to_disk(data):
    try:
        data["updated_at"] = datetime.now().isoformat()
        
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        
        temp_file = DATA_FILE + ".tmp"
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
        
        os.replace(temp_file, DATA_FILE)
        
        logger.debug(DATABASE_TEXTS['data_saved'].format(file=DATA_FILE))
        return True
    except Exception as e:
        logger.error(DATABASE_TEXTS['save_error'].format(error=e))
        return False

def schedule_save():
    global _data_modified, _last_save_time
    
    with _data_lock:
        current_time = time.time()
        
        if _data_modified and (current_time - _last_save_time) > AUTOSAVE_INTERVAL:
            
            if _in_memory_data:
                save_data_to_disk(_in_memory_data)
                if BACKUP_ENABLED and should_create_backup():
                    create_daily_backup()
            
            _data_modified = False
            _last_save_time = current_time
            logger.debug(DATABASE_TEXTS['autosave'].format(seconds=current_time - _last_save_time))
            return True
    
    return False

def should_create_backup():
    if not BACKUP_ENABLED:
        return False
    
    backup_marker = os.path.join(BACKUP_PATH, ".last_backup_date")
    
    try:
        if os.path.exists(backup_marker):
            with open(backup_marker, 'r') as f:
                last_backup_date = f.read().strip()
            
            if last_backup_date == datetime.now().strftime("%Y-%m-%d"):
                logger.debug(DATABASE_TEXTS['backup_skipped'])
                return False
    except:
        pass
    
    return True

def create_daily_backup():
    try:
        if not os.path.exists(DATA_FILE):
            return False
        
        os.makedirs(BACKUP_PATH, exist_ok=True)
        
        backup_marker = os.path.join(BACKUP_PATH, ".last_backup_date")
        today = datetime.now().strftime("%Y-%m-%d")
        
        try:
            if os.path.exists(backup_marker):
                with open(backup_marker, 'r') as f:
                    last_backup_date = f.read().strip()
                
                if last_backup_date == today:
                    logger.debug(DATABASE_TEXTS['backup_skipped'])
                    return False
        except:
            pass
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(BACKUP_PATH, f"daily_{timestamp}.json")
        
        shutil.copy2(DATA_FILE, backup_file)
        
        with open(backup_marker, 'w') as f:
            f.write(today)
        
        cleanup_backups(max_backups=5)
        
        size = os.path.getsize(backup_file)
        logger.info(DATABASE_TEXTS['daily_backup'].format(file=backup_file, size=size))
        
        return True
    except Exception as e:
        logger.error(DATABASE_TEXTS['daily_backup_error'].format(error=e))
        return False

def cleanup_backups(max_backups=5):
    try:
        if not os.path.exists(BACKUP_PATH):
            return
        
        backups = []
        for filename in os.listdir(BACKUP_PATH):
            if filename.endswith('.json') and filename.startswith('daily_'):
                filepath = os.path.join(BACKUP_PATH, filename)
                mtime = os.path.getmtime(filepath)
                backups.append((filepath, mtime, filename))
        
        backups.sort(key=lambda x: x[1], reverse=True)
        
        for backup in backups[max_backups:]:
            try:
                os.remove(backup[0])
                logger.debug(DATABASE_TEXTS['old_backup_deleted'].format(file=backup[2]))
            except Exception as e:
                logger.error(DATABASE_TEXTS['delete_backup_error'].format(file=backup[2], error=e))
                
    except Exception as e:
        logger.error(DATABASE_TEXTS['cleanup_error'].format(error=e))

def save_data(data):
    global _in_memory_data, _data_modified
    
    with _data_lock:
        _in_memory_data = data
        _data_modified = True
    
    schedule_save()
    
    return True

def create_safe_backup(description: str = "") -> Tuple[bool, str]:
    try:
        if not os.path.exists(DATA_FILE):
            return False, DATABASE_TEXTS['file_not_found'].format(file=DATA_FILE)
        
        os.makedirs(BACKUP_PATH, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        desc_part = f"_{description}" if description else ""
        backup_file = os.path.join(BACKUP_PATH, f"manual{desc_part}_{timestamp}.json")
        
        with _data_lock:
            if _in_memory_data:
                save_data_to_disk(_in_memory_data)
        
        shutil.copy2(DATA_FILE, backup_file)
        
        cleanup_manual_backups(max_backups=3)
        
        size = os.path.getsize(backup_file)
        logger.info(DATABASE_TEXTS['manual_backup'].format(file=backup_file, size=size))
        
        return True, backup_file
    except Exception as e:
        logger.error(DATABASE_TEXTS['manual_backup_error'].format(error=e))
        return False, str(e)

def cleanup_manual_backups(max_backups=3):
    try:
        if not os.path.exists(BACKUP_PATH):
            return
        
        manual_backups = []
        for filename in os.listdir(BACKUP_PATH):
            if filename.endswith('.json') and filename.startswith('manual'):
                filepath = os.path.join(BACKUP_PATH, filename)
                mtime = os.path.getmtime(filepath)
                manual_backups.append((filepath, mtime, filename))
        
        manual_backups.sort(key=lambda x: x[1], reverse=True)
        
        for backup in manual_backups[max_backups:]:
            try:
                os.remove(backup[0])
                logger.debug(DATABASE_TEXTS['manual_delete'].format(file=backup[2]))
            except Exception as e:
                logger.error(DATABASE_TEXTS['manual_delete_error'].format(file=backup[2], error=e))
                
    except Exception as e:
        logger.error(DATABASE_TEXTS['manual_cleanup_error'].format(error=e))

def get_backup_list(limit: int = 10) -> List[Dict]:
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
        logger.error(DATABASE_TEXTS['backup_list_error'].format(error=e))
        return []

def get_database_size() -> Dict[str, Any]:
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
        logger.error(DATABASE_TEXTS['db_size_error'].format(error=e))
        return {"exists": False, "size": 0, "error": str(e)}

def add_shlep(user_id: int, username: str, damage: int, chat_id: Optional[int] = None) -> Tuple[int, int, int]:
    try:
        global _in_memory_data, _data_modified
        
        with _data_lock:
            if _in_memory_data is None:
                _in_memory_data = ensure_data_file()
            
            data = _in_memory_data
            now = datetime.now().isoformat()
            user_id_str = str(user_id)
            
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
            
            data["global_stats"]["total_shleps"] += 1
            data["global_stats"]["last_shlep"] = now
            
            if damage > data["global_stats"]["max_damage"]:
                data["global_stats"]["max_damage"] = damage
                data["global_stats"]["max_damage_user"] = username
                data["global_stats"]["max_damage_date"] = now
            
            date_key = datetime.now().strftime("%Y-%m-%d")
            if date_key not in data["timestamps"]:
                data["timestamps"][date_key] = 0
            data["timestamps"][date_key] += 1
            
            if damage >= 50:
                record = {
                    "user_id": user_id,
                    "username": username,
                    "damage": damage,
                    "timestamp": now,
                    "chat_id": chat_id
                }
                data["records"].append(record)
                
                if len(data["records"]) > 5:
                    data["records"] = data["records"][-5:]
            
            _data_modified = True
            
            return (
                data["global_stats"]["total_shleps"],
                user["total_shleps"],
                user["max_damage"]
            )
            
    except Exception as e:
        logger.error(DATABASE_TEXTS['add_shlep_error'].format(error=e), exc_info=True)
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
        logger.error(DATABASE_TEXTS['get_stats_error'].format(error=e))
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
        logger.error(DATABASE_TEXTS['top_users_error'].format(error=e))
        return []

def get_user_stats(user_id: int) -> Tuple[Optional[str], int, Optional[datetime]]:
    try:
        data = load_data()
        
        user_id_str = str(user_id)
        user_data = data["users"].get(user_id_str)
        
        if not user_data:
            return (None, 0, None)
        
        # Получаем количество шлёпков
        shlep_count = user_data.get("total_shleps", 0)
        
        # Преобразуем в int, если нужно
        if isinstance(shlep_count, str):
            try:
                shlep_count = int(shlep_count)
            except:
                shlep_count = 0
        elif not isinstance(shlep_count, int):
            shlep_count = int(shlep_count) if shlep_count else 0
        
        # Получаем и преобразуем дату последнего шлёпка
        last_shlep = None
        last_shlep_str = user_data.get("last_shlep")
        
        if last_shlep_str:
            try:
                # Убираем возможный Z и приводим к ISO формату
                if 'Z' in last_shlep_str:
                    last_shlep_str = last_shlep_str.replace('Z', '+00:00')
                
                # Преобразуем строку в datetime
                last_shlep = datetime.fromisoformat(last_shlep_str)
            except Exception as e:
                logger.warning(f"Не удалось преобразовать дату для user {user_id}: {last_shlep_str}, ошибка: {e}")
                last_shlep = None
        
        return (
            user_data.get("username", f"User_{user_id}"),
            shlep_count,
            last_shlep
        )
    except Exception as e:
        logger.error(f"Ошибка в get_user_stats для user_id={user_id}: {e}")
        return (None, 0, None)

def get_chat_stats(chat_id: int) -> Dict[str, Any]:
    try:
        data = load_data()
        
        chat_data = data["chats"].get(str(chat_id))
        if not chat_data:
            return {}
        
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
        logger.error(DATABASE_TEXTS['chat_stats_error'].format(error=e))
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
        logger.error(DATABASE_TEXTS['chat_top_error'].format(error=e))
        return []

def backup_database():
    return create_safe_backup("command")

def check_data_integrity():
    try:
        data = load_data()
        
        errors = []
        warnings = []
        
        required_keys = ["users", "global_stats"]
        for key in required_keys:
            if key not in data:
                errors.append(f"Отсутствует ключ: {key}")
        
        total_from_users = sum(user.get("total_shleps", 0) for user in data.get("users", {}).values())
        total_in_global = data.get("global_stats", {}).get("total_shleps", 0)
        
        if total_from_users != total_in_global:
            warnings.append(f"Несоответствие счетчиков: {total_from_users} vs {total_in_global}")
        
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
        logger.error(DATABASE_TEXTS['integrity_error'].format(error=e))
        return {
            "errors": [f"Ошибка проверки: {str(e)}"],
            "warnings": [],
            "stats": {}
        }

def create_vote(chat_id: int, question: str, duration_minutes: int = 5) -> str:
    try:
        data = load_data()
        
        vote_id = f"{chat_id}_{int(datetime.now().timestamp())}"
        ends_at = datetime.now() + timedelta(minutes=duration_minutes)
        
        vote_data = {
            "id": vote_id,
            "chat_id": chat_id,
            "question": question,
            "created_at": datetime.now().isoformat(),
            "ends_at": ends_at.isoformat(),
            "votes_yes": [],
            "votes_no": [],
            "active": True,
            "message_id": None
        }
        
        data["votes"][vote_id] = vote_data
        save_data(data)
        
        return vote_id
    except Exception as e:
        logger.error(DATABASE_TEXTS['create_vote_error'].format(error=e))
        return ""

def get_vote(vote_id: str):
    try:
        data = load_data()
        return data["votes"].get(vote_id)
    except:
        return None

def get_active_chat_vote(chat_id: int):
    try:
        data = load_data()
        now = datetime.now()
        
        for vote_id, vote in data["votes"].items():
            if (vote.get("chat_id") == chat_id and 
                vote.get("active", False) and
                datetime.fromisoformat(vote["ends_at"]) > now):
                return vote
        return None
    except:
        return None

def add_user_vote(vote_id: str, user_id: int, vote_type: str) -> bool:
    try:
        data = load_data()
        vote = data["votes"].get(vote_id)
        
        if not vote or not vote.get("active", False):
            return False
        
        user_id_str = str(user_id)
        
        if user_id_str in vote["votes_yes"]:
            vote["votes_yes"].remove(user_id_str)
        if user_id_str in vote["votes_no"]:
            vote["votes_no"].remove(user_id_str)
        
        if vote_type == "yes":
            vote["votes_yes"].append(user_id_str)
        else:
            vote["votes_no"].append(user_id_str)
        
        save_data(data)
        return True
    except Exception as e:
        logger.error(DATABASE_TEXTS['add_vote_error'].format(error=e))
        return False

def finish_vote(vote_id: str):
    try:
        data = load_data()
        vote = data["votes"].get(vote_id)
        
        if vote:
            vote["active"] = False
            vote["finished_at"] = datetime.now().isoformat()
            save_data(data)
            return vote
        return None
    except Exception as e:
        logger.error(DATABASE_TEXTS['finish_vote_error'].format(error=e))
        return None

def cleanup_old_votes():
    try:
        data = load_data()
        now = datetime.now()
        to_delete = []
        
        for vote_id, vote in data["votes"].items():
            ends_at = datetime.fromisoformat(vote["ends_at"])
            if not vote.get("active", False) and (now - ends_at).days >= 1:
                to_delete.append(vote_id)
        
        for vote_id in to_delete:
            del data["votes"][vote_id]
        
        if to_delete:
            save_data(data)
            logger.info(DATABASE_TEXTS['cleanup_votes'].format(count=len(to_delete)))
    except Exception as e:
        logger.error(DATABASE_TEXTS['cleanup_votes_error'].format(error=e))

def update_vote_message_id(vote_id: str, message_id: int):
    try:
        data = load_data()
        vote = data["votes"].get(vote_id)
        
        if vote:
            vote["message_id"] = message_id
            save_data(data)
            return True
        return False
    except:
        return False

cleanup_old_votes()
logger.info(DATABASE_TEXTS['ready'])
