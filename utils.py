import asyncio
import logging
from typing import Any, Dict
from datetime import datetime
from database import load_data

logger = logging.getLogger(__name__)

# ==================== КЭШИРОВАНИЕ ====================

class SimpleCache:
    """Простой in-memory кэш для хранения временных данных"""
    
    def __init__(self):
        self._cache = {}
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Any:
        """Получить значение по ключу"""
        async with self._lock:
            return self._cache.get(key)
    
    async def set(self, key: str, value: Any) -> bool:
        """Установить значение по ключу"""
        async with self._lock:
            self._cache[key] = value
            return True
    
    async def delete(self, key: str) -> bool:
        """Удалить значение по ключу"""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
            return True
    
    async def clear(self) -> bool:
        """Очистить весь кэш"""
        async with self._lock:
            self._cache.clear()
            return True

# Глобальный экземпляр кэша
cache = SimpleCache()

# ==================== СТАТИСТИКА ====================

def get_comparison_stats(user_id: int) -> Dict[str, Any]:
    """Сравнивает статистику пользователя с другими игроками"""
    try:
        data = load_data()
        all_users = data.get("users", {})
        
        if not all_users:
            return {
                "total_users": 0,
                "avg_shleps": 0,
                "rank": 1,
                "percentile": 100
            }
        
        user_data = all_users.get(str(user_id))
        user_shleps = user_data.get("total_shleps", 0) if user_data else 0
        
        all_shleps = []
        for uid, udata in all_users.items():
            if "total_shleps" in udata:
                all_shleps.append(udata["total_shleps"])
        
        if not all_shleps:
            return {
                "total_users": len(all_users),
                "avg_shleps": 0,
                "rank": 1,
                "percentile": 100
            }
        
        total_users = len(all_shleps)
        avg_shleps = sum(all_shleps) / total_users
        
        sorted_shleps = sorted(all_shleps, reverse=True)
        
        try:
            rank = sorted_shleps.index(user_shleps) + 1
        except ValueError:
            rank = total_users + 1
        
        if total_users > 1:
            behind = total_users - rank
            percentile = (behind / (total_users - 1)) * 100
        else:
            percentile = 100
        
        return {
            "total_users": total_users,
            "avg_shleps": round(avg_shleps, 1),
            "rank": rank,
            "percentile": round(percentile, 1)
        }
    
    except Exception as e:
        logger.error(f"Ошибка сравнения статистики: {e}")
        return {
            "total_users": 0,
            "avg_shleps": 0,
            "rank": 1,
            "percentile": 100
        }

# ==================== ФОРМАТИРОВАНИЕ ====================

def format_file_size(bytes_size: int) -> str:
    """Форматирует размер файла в читаемый вид"""
    if bytes_size < 1024:
        return f"{bytes_size} B"
    elif bytes_size < 1024 * 1024:
        return f"{bytes_size/1024:.1f} KB"
    elif bytes_size < 1024 * 1024 * 1024:
        return f"{bytes_size/(1024*1024):.1f} MB"
    else:
        return f"{bytes_size/(1024*1024*1024):1f} GB"

def format_number(num: int) -> str:
    """Форматирует число с разделителями тысяч"""
    return f"{num:,}".replace(",", " ")

def create_progress_bar(progress: int, length: int = 10) -> str:
    """Создаёт текстовый прогресс-бар"""
    filled = min(int(progress * length / 100), length)
    return "█" * filled + "░" * (length - filled)

def escape_text(text: str) -> str:
    """Экранирует текст для MarkdownV1 (уже есть в bot.py, но добавлю для полноты)"""
    from telegram.helpers import escape_markdown
    return escape_markdown(text or "", version=1)
