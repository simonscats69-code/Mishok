import random
import math
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
import pytz

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

def generate_animation() -> str:
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

def calculate_xp_for_level(level: int, base_xp: int = 100, multiplier: float = 1.5) -> int:
    if level <= 1:
        return 0
    return int(base_xp * (multiplier ** (level - 2)))

def calculate_level_from_xp(xp: int, base_xp: int = 100, multiplier: float = 1.5) -> Tuple[int, int, int]:
    level = 1
    xp_needed = calculate_xp_for_level(level + 1, base_xp, multiplier)
    xp_remaining = xp
    
    while xp_remaining >= xp_needed:
        xp_remaining -= xp_needed
        level += 1
        xp_needed = calculate_xp_for_level(level + 1, base_xp, multiplier)
    
    return level, xp_remaining, xp_needed

def calculate_percentage(value: float, total: float) -> float:
    if total == 0:
        return 0.0
    return (value / total) * 100

def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix

def split_into_chunks(text: str, chunk_size: int = 4000) -> List[str]:
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
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    for char in special_chars:
        text = text.replace(char, '\\' + char)
    
    return text

def create_table(headers: List[str], rows: List[List[str]], align: List[str] = None) -> str:
    if not rows:
        return "Нет данных"
    
    if align is None:
        align = ['L'] * len(headers)
    
    col_widths = []
    for i in range(len(headers)):
        max_width = len(str(headers[i]))
        for row in rows:
            if i < len(row):
                max_width = max(max_width, len(str(row[i])))
        col_widths.append(max_width + 2)
    
    result = []
    
    header_line = "│"
    for i, header in enumerate(headers):
        header_line += f" {header:{'<' if align[i] == 'L' else '>' if align[i] == 'R' else '^'}{col_widths[i] - 2}} │"
    result.append(header_line)
    
    separator = "├" + "┼".join(["─" * (w - 2) for w in col_widths]) + "┤"
    result.append(separator)
    
    for row in rows:
        row_line = "│"
        for i, cell in enumerate(row):
            if i < len(col_widths):
                row_line += f" {str(cell):{'<' if align[i] == 'L' else '>' if align[i] == 'R' else '^'}{col_widths[i] - 2}} │"
        result.append(row_line)
    
    return "\n".join(result)

def weighted_choice(choices: List[Tuple[Any, float]]) -> Any:
    total = sum(weight for _, weight in choices)
    r = random.uniform(0, total)
    
    current = 0
    for value, weight in choices:
        current += weight
        if r <= current:
            return value
    
    return choices[0][0] if choices else None

def chance(probability: float) -> bool:
    return random.random() < probability

def random_range(min_val: float, max_val: float) -> float:
    return random.uniform(min_val, max_val)

class SimpleCache:
    def __init__(self, ttl_seconds: int = 300):
        self.cache = {}
        self.ttl = ttl_seconds
    
    def get(self, key: str) -> Any:
        if key in self.cache:
            value, timestamp = self.cache[key]
            import time
            if time.time() - timestamp < self.ttl:
                return value
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Any) -> None:
        import time
        self.cache[key] = (value, time.time())
    
    def clear(self) -> None:
        self.cache.clear()
    
    def size(self) -> int:
        return len(self.cache)
