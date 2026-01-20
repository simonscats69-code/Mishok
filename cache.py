import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Optional, Dict

logger = logging.getLogger(__name__)

class Cache:
    def __init__(self):
        self._cache: Dict[str, tuple] = {}
        self._lock = asyncio.Lock()
        self._default_ttl = timedelta(minutes=5)
        
    async def get(self, key: str) -> Any:
        async with self._lock:
            if key not in self._cache:
                return None
                
            value, expires = self._cache[key]
            
            if datetime.now() > expires:
                del self._cache[key]
                return None
                
            return value
    
    async def set(self, key: str, value: Any, ttl: Optional[timedelta] = None) -> bool:
        async with self._lock:
            try:
                expires = datetime.now() + (ttl or self._default_ttl)
                self._cache[key] = (value, expires)
                return True
            except Exception as e:
                logger.error(f"Ошибка установки кэша {key}: {e}")
                return False
    
    async def delete(self, key: str) -> bool:
        async with self._lock:
            try:
                if key in self._cache:
                    del self._cache[key]
                return True
            except Exception as e:
                logger.error(f"Ошибка удаления кэша {key}: {e}")
                return False
    
    async def clear(self) -> bool:
        async with self._lock:
            try:
                self._cache.clear()
                logger.info("Кэш полностью очищен")
                return True
            except Exception as e:
                logger.error(f"Ошибка очистки кэша: {e}")
                return False
    
    async def exists(self, key: str) -> bool:
        async with self._lock:
            if key not in self._cache:
                return False
                
            value, expires = self._cache[key]
            if datetime.now() > expires:
                del self._cache[key]
                return False
                
            return True

cache = Cache()
