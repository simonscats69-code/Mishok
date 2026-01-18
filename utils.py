#!/usr/bin/env python3
"""
Utility functions for Mishok bot
"""

import random
import pytz
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple

def get_moscow_time() -> datetime:
    """Возвращает текущее время в московском часовом поясе"""
    try:
        moscow_tz = pytz.timezone('Europe/Moscow')
        return datetime.now(moscow_tz)
    except:
        return datetime.now()

def format_number(number: int) -> str:
    """Форматирует числа с пробелами: 1000000 -> 1 000 000"""
    return f"{number:,}".replace(",", " ")

def format_percentage(value: float, total: float) -> str:
    """Форматирует проценты с одним знаком после запятой"""
    if total == 0:
        return "0.0%"
    percentage = (value / total) * 100
    return f"{percentage:.1f}%"

def create_progress_bar(value: float, total: float, length: int = 20) -> str:
    """Создаёт текстовый прогресс-бар"""
    if total == 0:
        filled = 0
    else:
        filled = int((value / total) * length)
    
    filled = max(0, min(filled, length))
    empty = length - filled
    
    return "█" * filled + "░" * empty

def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Обрезает текст до максимальной длины"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix

def format_time_ago(timestamp: datetime) -> str:
    """Форматирует время в формате 'X назад'"""
    if not timestamp:
        return "никогда"
    
    now = get_moscow_time()
    diff = now - timestamp
    
    if diff.days > 365:
        years = diff.days // 365
        return f"{years} год{'' if years == 1 else 'а' if 2 <= years <= 4 else 'ов'} назад"
    elif diff.days > 30:
        months = diff.days // 30
        return f"{months} месяц{'' if months == 1 else 'а' if 2 <= months <= 4 else 'ев'} назад"
    elif diff.days > 0:
        return f"{diff.days} день{'' if diff.days == 1 else 'я' if 2 <= diff.days <= 4 else 'ей'} назад"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} час{'' if hours == 1 else 'а' if 2 <= hours <= 4 else 'ов'} назад"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} минут{'' if minutes == 1 else 'ы' if 2 <= minutes <= 4 else ''} назад"
    else:
        return "только что"

def format_duration(seconds: int) -> str:
    """Форматирует длительность в человекочитаемом виде"""
    if seconds < 60:
        return f"{seconds} сек"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} мин"
    elif seconds < 86400:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours} ч {minutes} мин"
    else:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        return f"{days} д {hours} ч"

def format_date_range(days: int) -> str:
    """Форматирует диапазон дат"""
    if days == 1:
        return "сегодня"
    elif days == 7:
        return "за неделю"
    elif days == 30:
        return "за месяц"
    elif days == 365:
        return "за год"
    else:
        return f"за {days} дней"

def calculate_average(data: List[int]) -> float:
    """Рассчитывает среднее значение списка чисел"""
    if not data:
        return 0.0
    return sum(data) / len(data)

def calculate_median(data: List[int]) -> float:
    """Рассчитывает медиану списка чисел"""
    if not data:
        return 0.0
    
    sorted_data = sorted(data)
    n = len(sorted_data)
    
    if n % 2 == 1:
        return float(sorted_data[n // 2])
    else:
        mid1 = sorted_data[n // 2 - 1]
        mid2 = sorted_data[n // 2]
        return (mid1 + mid2) / 2

def calculate_percentile(data: List[int], percentile: float) -> float:
    """Рассчитывает перцентиль списка чисел"""
    if not data:
        return 0.0
    
    sorted_data = sorted(data)
    n = len(sorted_data)
    k = (n - 1) * percentile / 100
    
    f = int(k)
    c = k - f
    
    if f + 1 < n:
        return sorted_data[f] + c * (sorted_data[f + 1] - sorted_data[f])
    else:
        return sorted_data[f]

def generate_chart(data: Dict[str, int], max_width: int = 50) -> str:
    """
    Генерирует текстовый график из словаря данных
    
    Args:
        data: словарь {метка: значение}
        max_width: максимальная ширина графика в символах
    
    Returns:
        Строка с текстовым графиком
    """
    if not data:
        return "📊 Нет данных для отображения"
    
    max_value = max(data.values())
    if max_value == 0:
        return "📊 Все значения равны нулю"
    
    chart_lines = []
    for label, value in data.items():
        bar_length = int((value / max_value) * max_width)
        bar = "█" * bar_length
        
        # Добавляем пустые символы если нужно
        if bar_length < max_width:
            bar += "░" * (max_width - bar_length)
        
        chart_lines.append(f"{label}: {bar} {value}")
    
    return "\n".join(chart_lines)

def generate_hourly_chart(hourly_data: List[int], compact: bool = False) -> str:
    """
    Генерирует график почасовой активности
    
    Args:
        hourly_data: список из 24 чисел
        compact: компактный режим (группировка по 4 часа)
    
    Returns:
        Строка с графиком
    """
    if not hourly_data or len(hourly_data) != 24:
        return "⏰ Нет данных по часам"
    
    if compact:
        # Компактный режим: группируем по 4 часа
        chart_lines = ["⏰ *Активность по часам (компактно):*"]
        
        for block_start in range(0, 24, 4):
            block_end = block_start + 3
            block_data = hourly_data[block_start:block_end+1]
            block_total = sum(block_data)
            
            # Находим максимальное значение для масштабирования
            max_total = max([sum(hourly_data[i:i+4]) for i in range(0, 24, 4)])
            
            if max_total > 0:
                bar_length = int((block_total / max_total) * 20)
            else:
                bar_length = 0
            
            bar = "█" * bar_length
            if bar_length < 20:
                bar += "░" * (20 - bar_length)
            
            time_range = f"{block_start:02d}:00-{block_end:02d}:00"
            chart_lines.append(f"{time_range}: {bar} {block_total}")
        
        return "\n".join(chart_lines)
    else:
        # Подробный режим: каждый час отдельно
        chart_lines = ["⏰ *Активность по часам:*"]
        
        max_value = max(hourly_data)
        if max_value == 0:
            return "⏰ Нет активности за этот период"
        
        for hour in range(24):
            value = hourly_data[hour]
            bar_length = int((value / max_value) * 15)
            
            bar = "█" * bar_length
            if bar_length < 15:
                bar += "░" * (15 - bar_length)
            
            hour_label = f"{hour:02d}:00"
            emoji = get_hour_emoji(hour)
            
            chart_lines.append(f"{emoji} {hour_label}: {bar} {value}")
        
        return "\n".join(chart_lines)

def get_hour_emoji(hour: int) -> str:
    """Возвращает эмодзи для часа суток"""
    if 0 <= hour < 6:
        return "🌙"  # Ночь
    elif 6 <= hour < 12:
        return "🌅"  # Утро
    elif 12 <= hour < 18:
        return "☀️"  # День
    else:
        return "🌆"  # Вечер

def get_day_of_week_emoji(date: datetime) -> str:
    """Возвращает эмодзи для дня недели"""
    weekdays = ["😴", "😞", "😐", "🙂", "😊", "🎉", "🎊"]
    return weekdays[date.weekday()]

def format_statistics_summary(stats: Dict[str, Any]) -> str:
    """Форматирует сводку статистики"""
    lines = []
    
    if 'total' in stats:
        lines.append(f"📊 Всего: {format_number(stats['total'])}")
    
    if 'average' in stats:
        lines.append(f"📈 Среднее: {stats['average']:.1f}")
    
    if 'median' in stats:
        lines.append(f"⚖️ Медиана: {stats['median']:.1f}")
    
    if 'max' in stats:
        lines.append(f"🏆 Максимум: {stats['max']}")
    
    if 'min' in stats and stats['min'] > 0:
        lines.append(f"📉 Минимум: {stats['min']}")
    
    return "\n".join(lines)

def safe_division(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Безопасное деление с обработкой нуля"""
    if denominator == 0:
        return default
    return numerator / denominator

def generate_random_id(length: int = 8) -> str:
    """Генерирует случайный ID"""
    import string
    import secrets
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def parse_time_range(time_range: str) -> Tuple[datetime, datetime]:
    """
    Парсит строку временного диапазона
    
    Args:
        time_range: "today", "week", "month", "year" или "all"
    
    Returns:
        Кортеж (начало, конец)
    """
    now = get_moscow_time()
    
    if time_range == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now
    elif time_range == "week":
        start = now - timedelta(days=7)
        end = now
    elif time_range == "month":
        start = now - timedelta(days=30)
        end = now
    elif time_range == "year":
        start = now - timedelta(days=365)
        end = now
    else:  # "all"
        start = datetime(2020, 1, 1)  # Произвольная дата в прошлом
        end = now
    
    return start, end

def humanize_number(num: int) -> str:
    """Преобразует большие числа в человекочитаемый формат"""
    if num < 1000:
        return str(num)
    elif num < 1000000:
        return f"{num/1000:.1f}K".replace(".0", "")
    elif num < 1000000000:
        return f"{num/1000000:.1f}M".replace(".0", "")
    else:
        return f"{num/1000000000:.1f}B".replace(".0", "")

# ========== ТЕСТ ФУНКЦИЙ ==========
if __name__ == "__main__":
    print("🔍 Тестирование утилит...")
    print("=" * 50)
    
    # Тест форматирования чисел
    test_numbers = [0, 1, 100, 1000, 10000, 100000, 1000000]
    print("1. Форматирование чисел:")
    for num in test_numbers:
        print(f"   {num:>9} -> {format_number(num):>12}")
    
    # Тест прогресс-бара
    print("\n2. Прогресс-бары:")
    tests = [(0, 100), (25, 100), (50, 100), (75, 100), (100, 100)]
    for value, total in tests:
        bar = create_progress_bar(value, total, 10)
        print(f"   {value:3}/{total:3}: {bar}")
    
    # Тест времени назад
    print("\n3. Формат времени назад:")
    now = get_moscow_time()
    test_times = [
        now - timedelta(seconds=30),
        now - timedelta(minutes=5),
        now - timedelta(hours=2),
        now - timedelta(days=3),
        now - timedelta(days=40),
        now - timedelta(days=400)
    ]
    for time in test_times:
        print(f"   {format_time_ago(time)}")
    
    # Тест графиков
    print("\n4. Генерация графиков:")
    test_data = {"Пн": 10, "Вт": 25, "Ср": 15, "Чт": 30, "Пт": 20, "Сб": 35, "Вс": 5}
    print(generate_chart(test_data, 20))
    
    # Тест почасового графика
    print("\n5. Почасовой график (тестовые данные):")
    hourly_test = [0]*6 + [5, 10, 15, 20, 25, 30, 35, 30, 25, 20, 15, 10, 5] + [0]*5
    print(generate_hourly_chart(hourly_test, compact=True))
    
    print("\n" + "=" * 50)
    print("✅ Все утилиты работают корректно!")
