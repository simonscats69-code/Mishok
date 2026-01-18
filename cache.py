import asyncio
from datetime import datetime, timedelta

class SimpleCache:
    def __init__(self, ttl: int = 300):
        self.cache = {}
        self.ttl = ttl
        self.hits = 0
        self.misses = 0
    
    async def get(self, key: str):
        if key in self.cache:
            value, timestamp = self.cache[key]
            if datetime.now() - timestamp < timedelta(seconds=self.ttl):
                self.hits += 1
                return value
        
        self.misses += 1
        return None
    
    async def set(self, key: str, value):
        self.cache[key] = (value, datetime.now())
    
    async def delete(self, key: str):
        if key in self.cache:
            del self.cache[key]
            return True
        return False
    
    async def clear_expired(self):
        now = datetime.now()
        expired = []
        
        for key, (_, timestamp) in self.cache.items():
            if now - timestamp >= timedelta(seconds=self.ttl):
                expired.append(key)
        
        for key in expired:
            del self.cache[key]
        
        return len(expired)
    
    async def clear(self):
        self.cache.clear()
        self.hits = 0
        self.misses = 0
    
    def get_stats(self):
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        
        return {
            'total_entries': len(self.cache),
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': round(hit_rate, 1),
            'ttl_seconds': self.ttl
        }

# Глобальный кэш
cache = SimpleCache()
