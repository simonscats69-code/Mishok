import asyncio
from typing import Any

class SimpleCache:
    def __init__(self):
        self._cache = {}
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Any:
        async with self._lock:
            return self._cache.get(key)
    
    async def set(self, key: str, value: Any) -> bool:
        async with self._lock:
            self._cache[key] = value
            return True
    
    async def delete(self, key: str) -> bool:
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
            return True
    
    async def clear(self) -> bool:
        async with self._lock:
            self._cache.clear()
            return True

cache = SimpleCache()
