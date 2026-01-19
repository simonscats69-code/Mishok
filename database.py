import json
import os
from datetime import datetime
import logging
from typing import Optional, Tuple, List, Any, Dict
import shutil
from datetime import timedelta

logger = logging.getLogger(__name__)

DATA_FILE = "mishok_data.json"
BACKUP_DIR = "backups"

def ensure_data_file():
    """Создаёт файл данных, если его нет"""
    if not os.path.exists(DATA_FILE):
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
    else:
        logger.info(f"Файл данных найден: {DATA_FILE}")

def load_data():
    """Загружает данные из файла"""
    try:
        ensure_data_file()
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Миграция для старых версий
        if "global_stats" not in data:
            data["global_stats"] = {
                "total_shleps": 0,
                "last_shlep": None,
                "max_damage": 0,
                "max_damage_user": None,
                "max_damage_date": None,
                "total_users": len(data.get("users", {}))
            }
        
        # Конвертируем списки обратно в множества
        if "timestamps" in data:
            for key, value in data["timestamps"].items():
                if "users" in value and isinstance(value["users"], list):
                    value["users"] = set(value["users"])
        
        return data
    except Exception as e:
        logger.error(f"Ошибка загрузки данных: {e}")
        return {"users": {}, "chats": {}, "global_stats": {}, "timestamps": {}, "records": []}

def save_data(data):
    """Сохраняет данные в файл"""
    try:
        # Конвертируем множества в списки для JSON
        data_copy = json.loads(json.dumps(data, default=str))
        
        if "timestamps" in data_copy:
            for key, value in data_copy["timestamps"].items():
                if "users" in value:
                    if hasattr(value["users"], '__iter__'):
                        value["users"] = list(value["users"])
                    elif isinstance(value["users"], set):
                        value["users"] = list(value["users"])
        
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data_copy, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения данных: {e}")
        return False

def add_shlep(user_id: int, username: str, damage: int, chat_id: Optional[int] = None) -> Tuple[int, int, int]:
    """
    Добавляет шлёпок в статистику
    
    Returns: (total_shleps, user_count, user_max_damage)
    """
    data = load_data()
    now = datetime.now().isoformat()
    
    # Инициализация пользователя
    if str(user_id) not in data["users"]:
        data["users"][str(user_id)] = {
            "username": username,
            "total_shleps": 0,
            "max_damage": 0,
            "last_shlep": now,
            "damage_history": [],
            "chat_stats": {}
        }
        data["global_stats"]["total_users"] = len(data["users"])
    
    user = data["users"][str(user_id)]
    user["username"] = username
    user["total_shleps"] += 1
    user["last_shlep"] = now
    
    if damage > user["max_damage"]:
        user["max_damage"] = damage
    
    # Добавляем в историю урона
    if "damage_history" not in user:
        user["damage_history"] = []
    user["damage_history"].append({
        "damage": damage,
        "timestamp": now,
        "chat_id": chat_id
    })
    
    # Ограничиваем историю последними 100 записями
    if len(user["damage_history"]) > 100:
        user["damage_history"] = user["damage_history"][-100:]
    
    # Статистика по чатам
    if chat_id:
        if str(chat_id) not in data["chats"]:
            data["chats"][str(chat_id)] = {
                "total_shleps": 0,
                "users": {},
                "max_damage": 0,
                "max_damage_user": None,
                "max_damage_date": None
            }
        
        chat = data["chats"][str(chat_id)]
        chat["total_shleps"] += 1
        
        if str(user_id) not in chat["users"]:
            chat["users"][str(user_id)] = {
                "username": username,
                "total_shleps": 0,
                "max_damage": 0
            }
        
        chat_user = chat["users"][str(user_id)]
        chat_user["username"] = username
        chat_user["total_shleps"] += 1
        
        if damage > chat_user["max_damage"]:
            chat_user["max_damage"] = damage
        
        if damage > chat["max_damage"]:
            chat["max_damage"] = damage
            chat["max_damage_user"] = username
            chat["max_damage_date"] = now
    
    # Глобальная статистика
    data["global_stats"]["total_shleps"] += 1
    data["global_stats"]["last_shlep"] = now
    
    if damage > data["global_stats"]["max_damage"]:
        data["global_stats"]["max_damage"] = damage
        data["global_stats"]["max_damage_user"] = username
        data["global_stats"]["max_damage_date"] = now
    
    # Сохраняем timestamp для активностей
    if "timestamps" not in data:
        data["timestamps"] = {}
    
    date_key = datetime.now().strftime("%Y-%m-%d")
    hour_key = datetime.now().strftime("%Y-%m-%d %H:00")
    
    if date_key not in data["timestamps"]:
        data["timestamps"][date_key] = {"count": 0, "users": set()}
    if hour_key not in data["timestamps"]:
        data["timestamps"][hour_key] = {"count": 0, "users": set()}
    
    data["timestamps"][date_key]["count"] += 1
    data["timestamps"][date_key]["users"].add(str(user_id))
    data["timestamps"][hour_key]["count"] += 1
    data["timestamps"][hour_key]["users"].add(str(user_id))
    
    # Запись рекордов
    if damage >= 30:  # Только значительные уроны
        record = {
            "user_id": user_id,
            "username": username,
            "damage": damage,
            "timestamp": now,
            "chat_id": chat_id
        }
        if "records" not in data:
            data["records"] = []
        data["records"].append(record)
        
        # Ограничиваем 100 последними рекордами
        if len(data["records"]) > 100:
            data["records"] = data["records"][-100:]
    
    save_data(data)
    
    return (
        data["global_stats"]["total_shleps"],
        user["total_shleps"],
        user["max_damage"]
    )

def get_stats() -> Tuple[int, Optional[datetime], int, Optional[str], Optional[datetime]]:
    """Возвращает глобальную статистику"""
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
    """Возвращает топ пользователей по количеству шлёпков"""
    data = load_data()
    
    users_list = []
    for user_id, user_data in data["users"].items():
        username = user_data.get("username", f"Игрок_{user_id}")
        total = user_data.get("total_shleps", 0)
        users_list.append((username, total))
    
    users_list.sort(key=lambda x: x[1], reverse=True)
    return users_list[:limit]

def get_user_stats(user_id: int) -> Tuple[Optional[str], int, Optional[datetime]]:
    """Возвращает статистику пользователя"""
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
    """Возвращает статистику чата"""
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
    """Возвращает топ пользователей в чате"""
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
    """Создаёт резервную копию базы данных"""
    try:
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
        
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
    """Возвращает статистику активностей"""
    data = load_data()
    
    if "timestamps" not in data:
        return {"daily": [], "hourly": {}, "active_users": 0}
    
    timestamps = data["timestamps"]
    now = datetime.now()
    
    # Активность по дням
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
    
    # Активность по часам
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

def get_user_activity(user_id: int, days: int = 14) -> Dict[str, Any]:
    """Возвращает активность пользователя"""
    data = load_data()
    
    user_data = data["users"].get(str(user_id))
    if not user_data or "damage_history" not in user_data:
        return {"daily": [], "hourly": {}, "total": 0}
    
    # Анализируем историю урона
    now = datetime.now()
    user_history = user_data["damage_history"]
    
    # Активность по дням
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
    
    # Форматируем результат
    daily_stats = []
    for i in range(days):
        date = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        daily_stats.append({
            "date": date,
            "count": daily_counts.get(date, 0)
        })
    
    daily_stats.reverse()
    
    # Форматируем почасовую статистику
    formatted_hourly = {}
    for hour in range(24):
        hour_key = f"{hour:02d}:00"
        formatted_hourly[hour_key] = hourly_counts.get(hour_key, 0)
    
    return {
        "daily": daily_stats,
        "hourly": formatted_hourly,
        "total": len(user_history)
    }

# Инициализация при импорте
ensure_data_file()
logger.info("База данных готова к работе")
