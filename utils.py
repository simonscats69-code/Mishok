import random
import pytz
from datetime import datetime

def get_moscow_time() -> datetime:
    try:
        moscow_tz = pytz.timezone('Europe/Moscow')
        return datetime.now(moscow_tz)
    except:
        return datetime.now()

def format_number(number: int) -> str:
    return f"{number:,}".replace(",", " ")

def format_percentage(value: float, total: float) -> str:
    if total == 0:
        return "0.0%"
    percentage = (value / total) * 100
    return f"{percentage:.1f}%"

def create_progress_bar(value: float, total: float, length: int = 20) -> str:
    if total == 0:
        filled = 0
    else:
        filled = int((value / total) * length)
    
    filled = max(0, min(filled, length))
    empty = length - filled
    
    return "█" * filled + "░" * empty

def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix
