from datetime import datetime, timedelta
import pytz
import random

def get_moscow_time():
    """Получить текущее московское время"""
    moscow_tz = pytz.timezone('Europe/Moscow')
    return datetime.now(moscow_tz)

def is_new_day(last_date: datetime):
    """Проверить, наступил ли новый день"""
    if not last_date:
        return True
    now = get_moscow_time()
    return now.date() > last_date.date()

def format_time_remaining():
    """Форматирование времени до конца дня"""
    now = get_moscow_time()
    end_of_day = datetime.combine(now.date() + timedelta(days=1), datetime.min.time())
    end_of_day = moscow_tz.localize(end_of_day)
    remaining = end_of_day - now
    
    hours = remaining.seconds // 3600
    minutes = (remaining.seconds % 3600) // 60
    
    return f"{hours:02d}:{minutes:02d}"

def generate_animation():
    """Генерация ASCII-анимации лысины"""
    frames = [
        """
        ┌───────┐
        │   ●●  │
        │  ┌──┐ │
        │  │  │ │
        │  └──┘ │
        └───────┘
        """,
        """
        ┌───────┐
        │   ●●  │
        │  ┌┴─┐ │
        │  │  │ │
        │  └──┘ │
        └───────┘
        """,
        """
        ┌───────┐
        │   ●●  │
        │  ┌─┴┐ │
        │  │  │ │
        │  └──┘ │
        └───────┘
        """
    ]
    return random.choice(frames)
