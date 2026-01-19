from datetime import datetime, timedelta

class SimpleCache:
    def __init__(self, ttl=300):
        self.cache, self.ttl, self.hits, self.misses = {}, ttl, 0, 0
    
    async def get(self, key):
        if key in self.cache:
            val, ts = self.cache[key]
            if datetime.now()-ts < timedelta(seconds=self.ttl):
                self.hits += 1; return val
        self.misses += 1; return None
    
    async def set(self, key, value):
        self.cache[key] = (value, datetime.now())
    
    async def delete(self, key):
        if key in self.cache: del self.cache[key]; return True
        return False
    
    async def clear_expired(self):
        now, expired = datetime.now(), []
        for k, (_, ts) in self.cache.items():
            if now-ts >= timedelta(seconds=self.ttl): expired.append(k)
        for k in expired: del self.cache[k]
        return len(expired)
    
    async def clear(self):
        self.cache.clear(); self.hits = 0; self.misses = 0
    
    def get_stats(self):
        total = self.hits+self.misses
        rate = (self.hits/total*100) if total>0 else 0
        return {'total_entries':len(self.cache),'hits':self.hits,'misses':self.misses,'hit_rate':round(rate,1),'ttl_seconds':self.ttl}

cache = SimpleCache()
