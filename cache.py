import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Optional, Dict, Tuple
import json

logger = logging.getLogger(__name__)

class Cache:
    """Простой кэш с TTL (временем жизни)"""
    
    def __init__(self):
        self._cache: Dict[str, Tuple[Any, datetime]] = {}
        self._lock = asyncio.Lock()
        self._default_ttl = timedelta(minutes=5)  # 5 минут по умолчанию
        
    async def get(self, key: str) -> Any:
        """Получить значение из кэша"""
        async with self._lock:
            if key not in self._cache:
                return None
                
            value, expires = self._cache[key]
            
            # Проверяем, не истёк ли срок
            if datetime.now() > expires:
                del self._cache[key]
                return None
                
            return value
    
    async def set(self, key: str, value: Any, ttl: Optional[timedelta] = None) -> bool:
        """Установить значение в кэш"""
        async with self._lock:
            try:
                expires = datetime.now() + (ttl or self._default_ttl)
                self._cache[key] = (value, expires)
                return True
            except Exception as e:
                logger.error(f"Ошибка установки кэша {key}: {e}")
                return False
    
    async def delete(self, key: str) -> bool:
        """Удалить значение из кэша"""
        async with self._lock:
            try:
                if key in self._cache:
                    del self._cache[key]
                return True
            except Exception as e:
                logger.error(f"Ошибка удаления кэша {key}: {e}")
                return False
    
    async def clear(self) -> bool:
        """Очистить весь кэш"""
        async with self._lock:
            try:
                self._cache.clear()
                logger.info("Кэш полностью очищен")
                return True
            except Exception as e:
                logger.error(f"Ошибка очистки кэша: {e}")
                return False
    
    async def exists(self, key: str) -> bool:
        """Проверить существование ключа"""
        async with self._lock:
            if key not in self._cache:
                return False
                
            value, expires = self._cache[key]
            if datetime.now() > expires:
                del self._cache[key]
                return False
                
            return True
    
    async def get_or_set(self, key: str, fetch_func, ttl: Optional[timedelta] = None) -> Any:
        """
        Получить значение из кэша или установить его
        
        Args:
            key: Ключ кэша
            fetch_func: Функция для получения значения, если его нет в кэше
            ttl: Время жизни кэша
        """
        # Пытаемся получить из кэша
        cached = await self.get(key)
        if cached is not None:
            return cached
        
        # Если нет в кэше, получаем через функцию
        try:
            value = await fetch_func() if asyncio.iscoroutinefunction(fetch_func) else fetch_func()
            await self.set(key, value, ttl)
            return value
        except Exception as e:
            logger.error(f"Ошибка получения данных для кэша {key}: {e}")
            raise
    
    async def get_stats(self) -> Dict[str, Any]:
        """Получить статистику кэша"""
        async with self._lock:
            now = datetime.now()
            valid_keys = 0
            expired_keys = 0
            
            for key, (_, expires) in self._cache.items():
                if now > expires:
                    expired_keys += 1
                else:
                    valid_keys += 1
            
            return {
                "total_keys": len(self._cache),
                "valid_keys": valid_keys,
                "expired_keys": expired_keys,
                "default_ttl_seconds": self._default_ttl.total_seconds(),
                "memory_usage": self._estimate_memory_usage()
            }
    
    def _estimate_memory_usage(self) -> int:
        """Примерная оценка использования памяти"""
        try:
            return sum(len(str(k)) + len(json.dumps(v[0])) for k, v in self._cache.items())
        except:
            return 0
    
    async def cleanup(self):
        """Очистка просроченных записей"""
        async with self._lock:
            now = datetime.now()
            expired_keys = []
            
            for key, (_, expires) in self._cache.items():
                if now > expires:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._cache[key]
            
            if expired_keys:
                logger.debug(f"Очищено {len(expired_keys)} просроченных записей кэша")
    
    async def set_multi(self, items: Dict[str, Any], ttl: Optional[timedelta] = None) -> bool:
        """Установить несколько значений"""
        async with self._lock:
            try:
                expires = datetime.now() + (ttl or self._default_ttl)
                for key, value in items.items():
                    self._cache[key] = (value, expires)
                return True
            except Exception as e:
                logger.error(f"Ошибка установки множества кэша: {e}")
                return False
    
    async def get_multi(self, keys: list) -> Dict[str, Any]:
        """Получить несколько значений"""
        async with self._lock:
            result = {}
            now = datetime.now()
            
            for key in keys:
                if key in self._cache:
                    value, expires = self._cache[key]
                    if now <= expires:
                        result[key] = value
                    else:
                        del self._cache[key]
            
            return result
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Инвалидировать ключи по паттерну
        
        Args:
            pattern: Строка, которая должна содержаться в ключе
            
        Returns:
            Количество удалённых ключей
        """
        async with self._lock:
            keys_to_delete = [key for key in self._cache.keys() if pattern in key]
            
            for key in keys_to_delete:
                del self._cache[key]
            
            if keys_to_delete:
                logger.info(f"Инвалидировано {len(keys_to_delete)} ключей по паттерну '{pattern}'")
            
            return len(keys_to_delete)

# Глобальный экземпляр кэша
cache = Cache()

# Периодическая очистка кэша
async def start_cache_cleanup():
    """Запуск периодической очистки кэша"""
    while True:
        try:
            await asyncio.sleep(300)  # Каждые 5 минут
            await cache.cleanup()
        except Exception as e:
            logger.error(f"Ошибка в cleanup кэша: {e}")

# Запуск очистки в фоне
async def init_cache():
    """Инициализация кэша"""
    import asyncio as aio
    task = aio.create_task(start_cache_cleanup())
    logger.info("Кэш инициализирован и запущена фоновая очистка")
    return task
