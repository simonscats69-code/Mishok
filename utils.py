"""
🛠️ Утилиты и вспомогательные функции для бота "Мишок Лысый"
"""

import random
import math
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
import pytz
import time

# ========== РАБОТА СО ВРЕМЕНЕМ ==========

def get_moscow_time() -> datetime:
    """
    Получить текущее московское время
    
    Returns:
        datetime: Текущее время в часовом поясе Москвы
    """
    try:
        moscow_tz = pytz.timezone('Europe/Moscow')
        return datetime.now(moscow_tz)
    except:
        # Fallback на локальное время
        return datetime.now()


def format_datetime(dt: datetime, format_str: str = "%d.%m.%Y %H:%M") -> str:
    """
    Форматировать дату и время
    
    Args:
        dt: Объект datetime
        format_str: Строка формата
        
    Returns:
        str: Отформатированная строка
    """
    if dt is None:
        return "никогда"
    return dt.strftime(format_str)


def format_time_remaining(target_time: Optional[datetime] = None) -> str:
    """
    Форматировать оставшееся время до события
    
    Args:
        target_time: Время события (если None - до конца дня)
        
    Returns:
        str: Отформатированное оставшееся время
    """
    now = get_moscow_time()
    
    if target_time is None:
        # До конца дня
        end_of_day = datetime.combine(now.date() + timedelta(days=1), datetime.min.time())
        end_of_day = pytz.timezone('Europe/Moscow').localize(end_of_day)
        remaining = end_of_day - now
    else:
        # До указанного времени
        remaining = target_time - now
    
    if remaining.total_seconds() <= 0:
        return "00:00"
    
    hours = int(remaining.total_seconds() // 3600)
    minutes = int((remaining.total_seconds() % 3600) // 60)
    
    return f"{hours:02d}:{minutes:02d}"


def is_new_day(last_date: Optional[datetime]) -> bool:
    """
    Проверить, наступил ли новый день
    
    Args:
        last_date: Последняя дата
        
    Returns:
        bool: True если наступил новый день
    """
    if last_date is None:
        return True
    
    now = get_moscow_time()
    return now.date() > last_date.date()


def get_time_of_day(hour: int) -> str:
    """
    Получить название времени суток по часу
    
    Args:
        hour: Час (0-23)
        
    Returns:
        str: Название времени суток с эмодзи
    """
    if 0 <= hour <= 5:
        return "ночью 🌙"
    elif 6 <= hour <= 11:
        return "утром 🌅"
    elif 12 <= hour <= 17:
        return "днём ☀️"
    elif 18 <= hour <= 23:
        return "вечером 🌆"
    else:
        return "в неизвестное время"


# ========== ФОРМАТИРОВАНИЕ ==========

def format_number(number: int) -> str:
    """
    Форматировать число с разделителями тысяч
    
    Args:
        number: Число для форматирования
        
    Returns:
        str: Отформатированная строка
    """
    return f"{number:,}".replace(",", " ")


def format_percentage(value: float, total: float) -> str:
    """
    Форматировать процентное значение
    
    Args:
        value: Текущее значение
        total: Общее значение
        
    Returns:
        str: Процент в формате "XX.X%"
    """
    if total == 0:
        return "0.0%"
    percentage = (value / total) * 100
    return f"{percentage:.1f}%"


def format_duration(seconds: int) -> str:
    """
    Форматировать длительность
    
    Args:
        seconds: Количество секунд
        
    Returns:
        str: Отформатированная длительность
    """
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


def create_progress_bar(value: float, total: float, length: int = 20) -> str:
    """
    Создать текстовый прогресс-бар
    
    Args:
        value: Текущее значение
        total: Общее значение
        length: Длина прогресс-бара
        
    Returns:
        str: Текстовый прогресс-бар
    """
    if total == 0:
        filled = 0
    else:
        filled = int((value / total) * length)
    
    filled = max(0, min(filled, length))
    empty = length - filled
    
    return "█" * filled + "░" * empty


# ========== ГЕНЕРАЦИЯ КОНТЕНТА ==========

def generate_animation() -> str:
    """
    Сгенерировать ASCII-анимацию лысины
    
    Returns:
        str: ASCII-арт анимации
    """
    frames = [
        """
        ┌─────────┐
        │   ● ●   │
        │  /━━━━━\│
        │  │     ││
        │  └─────┘│
        └─────────┘
        """,
        """
        ┌─────────┐
        │   ● ●   │
        │  /━━━━━\│
        │  │  •  ││
        │  └─────┘│
        └─────────┘
        """,
        """
        ┌─────────┐
        │   ● ●   │
        │  /━━━━━\│
        │  │  ○  ││
        │  └─────┘│
        └─────────┘
        """,
        """
        ┌─────────┐
        │   ● ●   │
        │  /━━━━━\│
        │  │  ◉  ││
        │  └─────┘│
        └─────────┘
        """,
        """
        ┌─────────┐
        │   ● ●   │
        │  /━━━━━\│
        │  │  ⚫  ││
        │  └─────┘│
        └─────────┘
        """
    ]
    
    return random.choice(frames)


def generate_random_name() -> str:
    """
    Сгенерировать случайное смешное имя
    
    Returns:
        str: Случайное имя
    """
    first_parts = ["Лыс", "Шлёп", "Балд", "Гол", "Блеск", "Хлоп", "Бам", "Бах"]
    second_parts = ["ыш", "ок", "ун", "ышко", "астый", "атель", "ух", "ам"]
    
    return random.choice(first_parts) + random.choice(second_parts)


def generate_shlep_sound() -> str:
    """
    Сгенерировать звук шлёпка
    
    Returns:
        str: Звук шлёпка с эмодзи
    """
    sounds = [
        ("ХЛОП! 👏", 0.3),
        ("БАЦ! 💥", 0.25),
        ("ШЛЁП! 👋", 0.2),
        ("БУМ! 🔊", 0.15),
        ("ПУХ! 💨", 0.1),
    ]
    
    # Взвешенный случайный выбор
    total = sum(weight for _, weight in sounds)
    r = random.uniform(0, total)
    
    current = 0
    for sound, weight in sounds:
        current += weight
        if r <= current:
            return sound
    
    return "ХЛОП! 👏"


def generate_compliment() -> str:
    """
    Сгенерировать комплимент для игрока
    
    Returns:
        str: Случайный комплимент
    """
    compliments = [
        "Ты шлёпаешь как профессионал! 🏆",
        "Идеальный удар! 💯",
        "От такого шлёпка мог бы позавидовать сам чемпион! 🥇",
        "Лысина сияет от твоих ударов! ✨",
        "Ты рождён для этого! 🎯",
        "С каждым шлёпком ты становишься лучше! 📈",
        "Это было эпично! 🤩",
        "Мишок в восторге от твоей техники! 👴👍",
        "Шлёпок мирового уровня! 🌍",
        "Ты делаешь это в совершенстве! 💪",
    ]
    
    return random.choice(compliments)


# ========== МАТЕМАТИЧЕСКИЕ ФУНКЦИИ ==========

def calculate_xp_for_level(level: int, base_xp: int = 100, multiplier: float = 1.5) -> int:
    """
    Рассчитать необходимое количество XP для уровня
    
    Args:
        level: Уровень
        base_xp: Базовое количество XP
        multiplier: Множитель сложности
        
    Returns:
        int: Необходимое количество XP
    """
    if level <= 1:
        return 0
    return int(base_xp * (multiplier ** (level - 2)))


def calculate_level_from_xp(xp: int, base_xp: int = 100, multiplier: float = 1.5) -> Tuple[int, int, int]:
    """
    Рассчитать уровень на основе XP
    
    Args:
        xp: Количество XP
        base_xp: Базовое количество XP
        multiplier: Множитель сложности
        
    Returns:
        Tuple: (текущий уровень, XP до след. уровня, XP для след. уровня)
    """
    level = 1
    xp_needed = calculate_xp_for_level(level + 1, base_xp, multiplier)
    xp_remaining = xp
    
    while xp_remaining >= xp_needed:
        xp_remaining -= xp_needed
        level += 1
        xp_needed = calculate_xp_for_level(level + 1, base_xp, multiplier)
    
    return level, xp_remaining, xp_needed


def calculate_percentage(value: float, total: float) -> float:
    """
    Рассчитать процент
    
    Args:
        value: Значение
        total: Общее значение
        
    Returns:
        float: Процент (0-100)
    """
    if total == 0:
        return 0.0
    return (value / total) * 100


def calculate_average(values: List[float]) -> float:
    """
    Рассчитать среднее значение
    
    Args:
        values: Список значений
        
    Returns:
        float: Среднее значение
    """
    if not values:
        return 0.0
    return sum(values) / len(values)


def calculate_median(values: List[float]) -> float:
    """
    Рассчитать медиану
    
    Args:
        values: Список значений
        
    Returns:
        float: Медиана
    """
    if not values:
        return 0.0
    
    sorted_values = sorted(values)
    n = len(sorted_values)
    
    if n % 2 == 1:
        return sorted_values[n // 2]
    else:
        return (sorted_values[n // 2 - 1] + sorted_values[n // 2]) / 2


# ========== РАБОТА С ТЕКСТОМ ==========

def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Обрезать текст до максимальной длины
    
    Args:
        text: Исходный текст
        max_length: Максимальная длина
        suffix: Суффикс для обрезанного текста
        
    Returns:
        str: Обрезанный текст
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def split_into_chunks(text: str, chunk_size: int = 4000) -> List[str]:
    """
    Разделить текст на части для отправки в Telegram
    
    Args:
        text: Исходный текст
        chunk_size: Максимальный размер части
        
    Returns:
        List[str]: Список частей текста
    """
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    current_chunk = ""
    
    for paragraph in text.split('\n'):
        if len(current_chunk) + len(paragraph) + 1 > chunk_size:
            chunks.append(current_chunk.strip())
            current_chunk = paragraph
        else:
            if current_chunk:
                current_chunk += '\n' + paragraph
            else:
                current_chunk = paragraph
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks


def escape_markdown(text: str) -> str:
    """
    Экранировать специальные символы Markdown
    
    Args:
        text: Исходный текст
        
    Returns:
        str: Экранированный текст
    """
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    for char in special_chars:
        text = text.replace(char, '\\' + char)
    
    return text


def create_table(headers: List[str], rows: List[List[str]], align: List[str] = None) -> str:
    """
    Создать текстовую таблицу
    
    Args:
        headers: Заголовки столбцов
        rows: Строки данных
        align: Выравнивание (L/R/C)
        
    Returns:
        str: Текстовая таблица
    """
    if not rows:
        return "Нет данных"
    
    if align is None:
        align = ['L'] * len(headers)
    
    # Определяем ширину столбцов
    col_widths = []
    for i in range(len(headers)):
        max_width = len(str(headers[i]))
        for row in rows:
            if i < len(row):
                max_width = max(max_width, len(str(row[i])))
        col_widths.append(max_width + 2)  # +2 для отступов
    
    # Создаём таблицу
    result = []
    
    # Заголовок
    header_line = "│"
    for i, header in enumerate(headers):
        header_line += f" {header:{'<' if align[i] == 'L' else '>' if align[i] == 'R' else '^'}{col_widths[i] - 2}} │"
    result.append(header_line)
    
    # Разделитель
    separator = "├" + "┼".join(["─" * (w - 2) for w in col_widths]) + "┤"
    result.append(separator)
    
    # Данные
    for row in rows:
        row_line = "│"
        for i, cell in enumerate(row):
            if i < len(col_widths):
                row_line += f" {str(cell):{'<' if align[i] == 'L' else '>' if align[i] == 'R' else '^'}{col_widths[i] - 2}} │"
        result.append(row_line)
    
    return "\n".join(result)


# ========== ВЕРОЯТНОСТЬ И СЛУЧАЙНОСТЬ ==========

def weighted_choice(choices: List[Tuple[Any, float]]) -> Any:
    """
    Выбор с учётом весов
    
    Args:
        choices: Список кортежей (значение, вес)
        
    Returns:
        Any: Выбранное значение
    """
    total = sum(weight for _, weight in choices)
    r = random.uniform(0, total)
    
    current = 0
    for value, weight in choices:
        current += weight
        if r <= current:
            return value
    
    return choices[0][0] if choices else None


def chance(probability: float) -> bool:
    """
    Проверить вероятность
    
    Args:
        probability: Вероятность (0-1)
        
    Returns:
        bool: True если вероятность сработала
    """
    return random.random() < probability


def random_range(min_val: float, max_val: float) -> float:
    """
    Случайное число в диапазоне
    
    Args:
        min_val: Минимальное значение
        max_val: Максимальное значение
        
    Returns:
        float: Случайное число
    """
    return random.uniform(min_val, max_val)


# ========== КЭШИРОВАНИЕ И ОПТИМИЗАЦИЯ ==========

class SimpleCache:
    """
    Простой кэш с TTL (Time To Live)
    """
    
    def __init__(self, ttl_seconds: int = 300):
        self.cache = {}
        self.ttl = ttl_seconds
    
    def get(self, key: str) -> Any:
        """
        Получить значение из кэша
        
        Args:
            key: Ключ
            
        Returns:
            Any: Значение или None если истёк срок
        """
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return value
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Any) -> None:
        """
        Установить значение в кэш
        
        Args:
            key: Ключ
            value: Значение
        """
        self.cache[key] = (value, time.time())
    
    def clear(self) -> None:
        """Очистить кэш"""
        self.cache.clear()
    
    def size(self) -> int:
        """
        Получить размер кэша
        
        Returns:
            int: Количество элементов
        """
        return len(self.cache)


# ========== ВАЛИДАЦИЯ И ПРОВЕРКИ ==========

def is_valid_user_id(user_id: Any) -> bool:
    """
    Проверить валидность ID пользователя
    
    Args:
        user_id: ID пользователя
        
    Returns:
        bool: True если валидный
    """
    if not isinstance(user_id, (int, str)):
        return False
    
    try:
        user_id_int = int(user_id)
        return user_id_int > 0
    except (ValueError, TypeError):
        return False


def is_valid_username(username: str) -> bool:
    """
    Проверить валидность имени пользователя
    
    Args:
        username: Имя пользователя
        
    Returns:
        bool: True если валидное
    """
    if not username:
        return False
    
    # Проверка длины
    if len(username) < 1 or len(username) > 32:
        return False
    
    # Проверка символов (только буквы, цифры, подчёркивания)
    import re
    pattern = r'^[a-zA-Z0-9_]+$'
    
    return bool(re.match(pattern, username))


def validate_number(value: Any, min_val: float = None, max_val: float = None) -> Optional[float]:
    """
    Валидировать число
    
    Args:
        value: Значение
        min_val: Минимальное значение
        max_val: Максимальное значение
        
    Returns:
        Optional[float]: Валидное число или None
    """
    try:
        num = float(value)
        
        if min_val is not None and num < min_val:
            return None
        
        if max_val is not None and num > max_val:
            return None
        
        return num
    except (ValueError, TypeError):
        return None


# ========== ТЕСТОВЫЕ ФУНКЦИИ ==========

def test_utils() -> Dict[str, Any]:
    """
    Протестировать все утилиты
    
    Returns:
        Dict: Результаты тестов
    """
    results = {}
    
    # Тест времени
    results['moscow_time'] = get_moscow_time()
    results['time_remaining'] = format_time_remaining()
    
    # Тест форматирования
    results['formatted_number'] = format_number(1234567)
    results['percentage'] = format_percentage(75, 100)
    results['progress_bar'] = create_progress_bar(75, 100, 10)
    
    # Тест генерации
    results['animation'] = generate_animation()[:50] + "..."
    results['random_name'] = generate_random_name()
    results['shlep_sound'] = generate_shlep_sound()
    results['compliment'] = generate_compliment()
    
    # Тест математики
    results['xp_for_level_5'] = calculate_xp_for_level(5)
    results['level_from_xp'] = calculate_level_from_xp(500)
    results['average'] = calculate_average([1, 2, 3, 4, 5])
    
    # Тест текста
    results['truncated'] = truncate_text("Очень длинный текст, который нужно обрезать", 20)
    
    # Тест вероятности
    results['weighted_choice'] = weighted_choice([("A", 0.5), ("B", 0.3), ("C", 0.2)])
    results['chance_test'] = chance(0.5)
    
    # Тест кэша
    cache = SimpleCache(ttl_seconds=60)
    cache.set("test_key", "test_value")
    results['cache_get'] = cache.get("test_key")
    results['cache_size'] = cache.size()
    
    # Тест валидации
    results['valid_user_id'] = is_valid_user_id(123456)
    results['invalid_user_id'] = is_valid_user_id(-1)
    results['valid_username'] = is_valid_username("test_user")
    results['invalid_username'] = is_valid_username("invalid@user")
    
    return results


if __name__ == "__main__":
    # Тестирование при прямом запуске
    test_results = test_utils()
    print("✅ Результаты тестирования утилит:")
    for key, value in test_results.items():
        print(f"  {key}: {value}")
    
    print(f"\n✅ Всего протестировано {len(test_results)} функций")
