import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import random
import math

logger = logging.getLogger(__name__)

def format_number(num: int) -> str:
    try:
        return f"{num:,}".replace(",", " ")
    except:
        return str(num)

def calculate_level(shlep_count: int) -> Dict[str, Any]:
    if shlep_count <= 0:
        return {
            "level": 1,
            "progress": 0,
            "next_level_at": 10,
            "shleps_to_next": 10
        }
    
    level = (shlep_count // 10) + 1
    progress = (shlep_count % 10) * 10
    next_level_at = (level * 10)
    shleps_to_next = next_level_at - shlep_count
    
    return {
        "level": level,
        "progress": progress,
        "next_level_at": next_level_at,
        "shleps_to_next": shleps_to_next
    }

def calculate_damage_range(level: int) -> tuple:
    base_min = 10
    base_max = 25
    
    if level <= 100:
        min_dmg = int(base_min * (1.02 ** min(level - 1, 100)))
        max_dmg = int(base_max * (1.08 ** min(level - 1, 100)))
    elif level <= 1000:
        min_dmg = base_min + 100 * 2 + (level - 100) * 1
        max_dmg = base_max + 100 * 3 + (level - 100) * 2
    else:
        min_dmg = base_min + 1000 * 2 + (level - 1000) * 0.5
        max_dmg = base_max + 1000 * 3 + (level - 1000) * 1
    
    if max_dmg <= min_dmg:
        max_dmg = min_dmg + 10
    
    return (min_dmg, max_dmg)

def generate_progress_bar(percentage: int, length: int = 10) -> str:
    filled = int(percentage / 100 * length)
    empty = length - filled
    
    filled_char = "█"
    empty_char = "░"
    
    return filled_char * filled + empty_char * empty

def format_time_ago(timestamp: datetime) -> str:
    if not timestamp:
        return "никогда"
    
    now = datetime.now()
    diff = now - timestamp
    
    if diff.days > 365:
        years = diff.days // 365
        return f"{years} год{'а' if years % 10 in [2,3,4] and years % 100 not in [12,13,14] else 'ов'}"
    elif diff.days > 30:
        months = diff.days // 30
        return f"{months} месяц{'а' if months % 10 in [2,3,4] and months % 100 not in [12,13,14] else 'ев'}"
    elif diff.days > 0:
        return f"{diff.days} день{'дня' if diff.days % 10 in [2,3,4] and diff.days % 100 not in [12,13,14] else 'дней'}"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} час{'а' if hours % 10 in [2,3,4] and hours % 100 not in [12,13,14] else 'ов'}"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} минут{'у' if minutes % 10 == 1 and minutes % 100 != 11 else 'ы' if minutes % 10 in [2,3,4] and minutes % 100 not in [12,13,14] else ''}"
    else:
        return "только что"

def safe_get(data: Dict, key: str, default: Any = None) -> Any:
    try:
        keys = key.split(".")
        current = data
        
        for k in keys:
            if isinstance(current, dict):
                current = current.get(k)
                if current is None:
                    return default
            else:
                return default
        
        return current if current is not None else default
    except:
        return default

def calculate_percentage(part: int, whole: int) -> float:
    if whole == 0:
        return 0.0
    return round((part / whole) * 100, 2)

def validate_username(username: str) -> str:
    if not username or not isinstance(username, str):
        return "Аноним"
    
    username = username.strip()
    
    if len(username) > 32:
        username = username[:32]
    
    username = username.replace("@", "(at)").replace("#", "").replace("/", "")
    
    return username if username else "Аноним"

def create_progress_bar(progress: float, length: int = 10) -> str:
    filled = int(progress * length)
    empty = length - filled
    return "█" * filled + "░" * empty

def format_file_size(bytes_size: int) -> str:
    if bytes_size < 1024:
        return f"{bytes_size} B"
    elif bytes_size < 1024 * 1024:
        return f"{bytes_size/1024:.1f} KB"
    elif bytes_size < 1024 * 1024 * 1024:
        return f"{bytes_size/(1024*1024):.1f} MB"
    else:
        return f"{bytes_size/(1024*1024*1024):.1f} GB"

def get_timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def create_backup_filename(prefix: str = "backup") -> str:
    timestamp = get_timestamp()
    return f"{prefix}_{timestamp}.json"

def safe_json_dump(data: Any, filepath: str) -> bool:
    try:
        import json
        temp_file = filepath + ".tmp"
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        import os
        os.replace(temp_file, filepath)
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения JSON: {e}")
        return False

def get_system_info() -> Dict[str, Any]:
    import platform
    import sys
    import os
    
    return {
        "python_version": platform.python_version(),
        "system": platform.system(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cwd": os.getcwd(),
        "script_dir": os.path.dirname(os.path.abspath(__file__)),
        "pid": os.getpid()
    }
