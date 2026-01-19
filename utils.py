import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import random
import math

logger = logging.getLogger(__name__)

def format_number(num: int) -> str:
    """Форматирует число с разделителями пробелами"""
    try:
        return f"{num:,}".replace(",", " ")
    except:
        return str(num)

def calculate_level(shlep_count: int) -> Dict[str, Any]:
    """Рассчитывает уровень на основе количества шлёпков"""
    if shlep_count <= 0:
        return {
            "level": 1,
            "progress": 0,
            "next_level_at": 10,
            "shleps_to_next": 10
        }
    
    # Уровень увеличивается каждые 10 шлёпков
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
    """Рассчитывает диапазон урона на основе уровня"""
    base_min = 10
    base_max = 25
    
    if level <= 100:
        # Для первых 100 уровней быстрый рост
        min_dmg = int(base_min * (1.02 ** min(level - 1, 100)))
        max_dmg = int(base_max * (1.08 ** min(level - 1, 100)))
    elif level <= 1000:
        # Для 100-1000 уровней средний рост
        min_dmg = base_min + 100 * 2 + (level - 100) * 1
        max_dmg = base_max + 100 * 3 + (level - 100) * 2
    else:
        # После 1000 уровней медленный рост
        min_dmg = base_min + 1000 * 2 + (level - 1000) * 0.5
        max_dmg = base_max + 1000 * 3 + (level - 1000) * 1
    
    # Гарантируем, что максимум больше минимума
    if max_dmg <= min_dmg:
        max_dmg = min_dmg + 10
    
    return (min_dmg, max_dmg)

def generate_progress_bar(percentage: int, length: int = 10) -> str:
    """Генерирует прогресс-бар"""
    filled = int(percentage / 100 * length)
    empty = length - filled
    
    # Используем разные символы для лучшего отображения
    filled_char = "█"
    empty_char = "░"
    
    return filled_char * filled + empty_char * empty

def format_time_ago(timestamp: datetime) -> str:
    """Форматирует время в формате 'сколько времени назад'"""
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
    """Безопасное получение значения из словаря"""
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

def chunk_list(lst: List, chunk_size: int) -> List[List]:
    """Разделяет список на части"""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Обрезает текст до указанной длины"""
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix

def is_valid_user_id(user_id: Any) -> bool:
    """Проверяет, является ли user_id валидным"""
    try:
        return isinstance(user_id, (int, str)) and str(user_id).isdigit() and int(user_id) > 0
    except:
        return False

def get_random_color() -> str:
    """Возвращает случайный цвет в HEX формате"""
    return f"#{random.randint(0, 0xFFFFFF):06x}"

def parse_time_string(time_str: str) -> Optional[timedelta]:
    """Парсит строку времени вида '1h30m' в timedelta"""
    try:
        hours = 0
        minutes = 0
        
        if 'h' in time_str:
            hours_part = time_str.split('h')[0]
            hours = int(hours_part) if hours_part.isdigit() else 0
        
        if 'm' in time_str:
            minutes_part = time_str.split('h')[1] if 'h' in time_str else time_str
            minutes_part = minutes_part.split('m')[0]
            minutes = int(minutes_part) if minutes_part.isdigit() else 0
        
        return timedelta(hours=hours, minutes=minutes)
    except:
        return None

def format_duration(seconds: int) -> str:
    """Форматирует длительность в секундах в читаемый вид"""
    if seconds < 60:
        return f"{seconds} сек"
    
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} мин"
    
    hours = minutes // 60
    minutes = minutes % 60
    
    if hours < 24:
        return f"{hours} ч {minutes} мин"
    
    days = hours // 24
    hours = hours % 24
    
    return f"{days} д {hours} ч"

def calculate_xp_for_next_level(current_level: int) -> int:
    """Рассчитывает XP для следующего уровня"""
    # Квадратичная прогрессия
    return int(100 * (current_level ** 1.5))

def generate_random_name() -> str:
    """Генерирует случайное смешное имя"""
    prefixes = ["Лысый", "Шлёпковый", "Медвежий", "Блестящий", "Электрический"]
    suffixes = ["Мишок", "Шлёп", "Бамбук", "Молния", "Фонарь"]
    
    return f"{random.choice(prefixes)} {random.choice(suffixes)}"

def escape_markdown_v2(text: str) -> str:
    """Экранирует спецсимволы для MarkdownV2"""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return ''.join(f'\\{c}' if c in escape_chars else c for c in text)

def validate_username(username: str) -> str:
    """Очищает и валидирует имя пользователя"""
    if not username or not isinstance(username, str):
        return "Аноним"
    
    # Убираем лишние пробелы
    username = username.strip()
    
    # Ограничиваем длину
    if len(username) > 32:
        username = username[:32]
    
    # Заменяем опасные символы
    username = username.replace("@", "(at)").replace("#", "").replace("/", "")
    
    return username if username else "Аноним"

def calculate_percentage(part: int, whole: int) -> float:
    """Рассчитывает процент"""
    if whole == 0:
        return 0.0
    return round((part / whole) * 100, 2)

def format_size(size_bytes: int) -> str:
    """Форматирует размер в байтах в читаемый вид"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    
    size_kb = size_bytes / 1024
    if size_kb < 1024:
        return f"{size_kb:.1f} KB"
    
    size_mb = size_kb / 1024
    if size_mb < 1024:
        return f"{size_mb:.1f} MB"
    
    size_gb = size_mb / 1024
    return f"{size_gb:.1f} GB"

def is_weekend() -> bool:
    """Проверяет, выходной ли сегодня"""
    today = datetime.now().weekday()
    return today >= 5  # 5 = суббота, 6 = воскресенье

def get_current_season() -> str:
    """Возвращает текущий сезон"""
    month = datetime.now().month
    
    if month in [12, 1, 2]:
        return "❄️ Зима"
    elif month in [3, 4, 5]:
        return "🌱 Весна"
    elif month in [6, 7, 8]:
        return "☀️ Лето"
    else:
        return "🍂 Осень"

def generate_session_id() -> str:
    """Генерирует уникальный ID сессии"""
    import uuid
    return str(uuid.uuid4())[:8]

def log_execution_time(func):
    """Декоратор для логирования времени выполнения"""
    import time
    from functools import wraps
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        logger.debug(f"{func.__name__} выполнена за {end_time - start_time:.3f} секунд")
        return result
    
    return wrapper

async def async_log_execution_time(func):
    """Асинхронный декоратор для логирования времени выполнения"""
    import time
    from functools import wraps
    
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        result = await func(*args, **kwargs)
        end_time = time.time()
        
        logger.debug(f"{func.__name__} выполнена за {end_time - start_time:.3f} секунд")
        return result
    
    return wrapper
