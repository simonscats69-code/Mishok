import asyncio
from datetime import datetime, timedelta
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)

class Cache:
    def __init__(self, ttl_seconds: int = 300):
        """
        Инициализация кэша.
        
        Args:
            ttl_seconds: Время жизни записей в секундах (по умолчанию 5 минут)
        """
        self.cache = {}
        self.ttl = ttl_seconds
        self.hits = 0
        self.misses = 0
        logger.info(f"Кэш инициализирован с TTL={ttl_seconds} сек")
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Получить значение из кэша по ключу.
        
        Args:
            key: Ключ для поиска
            
        Returns:
            Значение или None, если не найдено или истек срок
        """
        if key in self.cache:
            data, timestamp = self.cache[key]
            if datetime.now() - timestamp < timedelta(seconds=self.ttl):
                self.hits += 1
                logger.debug(f"Кэш-попадание для ключа: {key}")
                return data
            else:
                # Удаляем просроченную запись
                del self.cache[key]
                logger.debug(f"Удалена просроченная запись: {key}")
        
        self.misses += 1
        logger.debug(f"Кэш-промах для ключа: {key}")
        return None
    
    async def set(self, key: str, value: Any) -> None:
        """
        Сохранить значение в кэш.
        
        Args:
            key: Ключ для сохранения
            value: Значение для сохранения
        """
        self.cache[key] = (value, datetime.now())
        logger.debug(f"Сохранено в кэш: {key}")
    
    async def delete(self, key: str) -> bool:
        """
        Удалить значение из кэша.
        
        Args:
            key: Ключ для удаления
            
        Returns:
            True если удалено, False если не найдено
        """
        if key in self.cache:
            del self.cache[key]
            logger.debug(f"Удалено из кэша: {key}")
            return True
        return False
    
    async def clear(self) -> None:
        """Очистить весь кэш."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
        logger.info("Кэш очищен")
    
    async def clear_expired(self) -> int:
        """
        Очистить просроченные записи.
        
        Returns:
            Количество удаленных записей
        """
        now = datetime.now()
        expired_keys = []
        
        for key, (_, timestamp) in self.cache.items():
            if now - timestamp >= timedelta(seconds=self.ttl):
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            logger.debug(f"Очищено {len(expired_keys)} просроченных записей")
        
        return len(expired_keys)
    
    def get_hit_rate(self) -> float:
        """
        Получить процент попаданий в кэш.
        
        Returns:
            Процент попаданий (от 0 до 100)
        """
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return (self.hits / total) * 100
    
    def get_stats(self) -> dict:
        """
        Получить статистику кэша.
        
        Returns:
            Словарь со статистикой
        """
        return {
            "total_entries": len(self.cache),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.get_hit_rate(),
            "ttl_seconds": self.ttl
        }
    
    async def cleanup_task(self, interval_seconds: int = 60):
        """
        Фоновая задача для очистки просроченных записей.
        
        Args:
            interval_seconds: Интервал очистки в секундах
        """
        while True:
            try:
                await asyncio.sleep(interval_seconds)
                cleared = await self.clear_expired()
                if cleared > 0:
                    logger.debug(f"Фоновая очистка: удалено {cleared} записей")
            except Exception as e:
                logger.error(f"Ошибка в фоновой задаче очистки кэша: {e}")

# Глобальный экземпляр кэша
cache = Cache(ttl_seconds=300)  # 5 минут по умолчанию
