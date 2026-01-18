import os
from contextlib import contextmanager
from datetime import datetime

from config import DATABASE_URL

try:
    import psycopg2
    from psycopg2.pool import SimpleConnectionPool
    PSYCOPG2_AVAILABLE = True
    CONNECTION_POOL = None
except ImportError:
    PSYCOPG2_AVAILABLE = False
    CONNECTION_POOL = None

class FakeDatabase:
    def __init__(self):
        self.global_stats = {
            'total_shleps': 0, 
            'last_shlep': None,
            'max_damage': 0,
            'max_damage_user_id': None,
            'max_damage_username': None,
            'max_damage_date': None
        }
        self.user_stats = {}
    
    def add_shlep(self, user_id: int, username: str, damage: int = 0):
        now = datetime.now()
        self.global_stats['total_shleps'] += 1
        self.global_stats['last_shlep'] = now
        
        if damage > self.global_stats['max_damage']:
            self.global_stats['max_damage'] = damage
            self.global_stats['max_damage_user_id'] = user_id
            self.global_stats['max_damage_username'] = username
            self.global_stats['max_damage_date'] = now
        
        if user_id not in self.user_stats:
            self.user_stats[user_id] = {'username': username, 'shlep_count': 0, 'last_shlep': None}
        
        self.user_stats[user_id]['shlep_count'] += 1
        self.user_stats[user_id]['last_shlep'] = now
        self.user_stats[user_id]['username'] = username
        
        return self.global_stats['total_shleps'], self.user_stats[user_id]['shlep_count'], self.global_stats['max_damage']

fake_db = FakeDatabase()

def init_connection_pool():
    """Инициализация пула соединений для PostgreSQL"""
    global CONNECTION_POOL
    if PSYCOPG2_AVAILABLE and DATABASE_URL:
        try:
            CONNECTION_POOL = SimpleConnectionPool(
                1, 10,  # minconn, maxconn
                dsn=DATABASE_URL
            )
            print("Пул соединений PostgreSQL инициализирован")
        except Exception as e:
            print(f"Ошибка инициализации пула соединений: {e}")
            CONNECTION_POOL = None

@contextmanager
def get_connection():
    if not PSYCOPG2_AVAILABLE or not DATABASE_URL:
        class StubConnection:
            def cursor(self): 
                return StubCursor()
            def commit(self): 
                pass
            def close(self): 
                pass
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
        
        class StubCursor:
            def __init__(self):
                self.result = None
            
            def execute(self, query, params=None):
                query_lower = query.lower().strip()
                
                if "insert into global_stats" in query_lower:
                    fake_db.global_stats = {
                        'total_shleps': 0, 
                        'last_shlep': None,
                        'max_damage': 0,
                        'max_damage_user_id': None,
                        'max_damage_username': None,
                        'max_damage_date': None
                    }
                elif "update global_stats" in query_lower and "returning total_shleps" in query_lower:
                    fake_db.global_stats['last_shlep'] = params[0] if params else datetime.now()
                    self.result = [(fake_db.global_stats['total_shleps'],)]
                elif "select total_shleps, last_shlep, max_damage, max_damage_username, max_damage_date from global_stats" in query_lower:
                    stats = fake_db.global_stats
                    self.result = [(
                        stats['total_shleps'], 
                        stats['last_shlep'],
                        stats['max_damage'],
                        stats['max_damage_username'],
                        stats['max_damage_date']
                    )]
                elif "insert into user_stats" in query_lower or "update user_stats" in query_lower:
                    if "returning shlep_count" in query_lower:
                        user_id = params[0]
                        self.result = [(fake_db.user_stats.get(user_id, {}).get('shlep_count', 1),)]
                elif "select username, shlep_count from user_stats" in query_lower:
                    users = []
                    for uid, data in fake_db.user_stats.items():
                        users.append((data['username'], data['shlep_count']))
                    users.sort(key=lambda x: x[1], reverse=True)
                    limit = params[0] if params else 10
                    self.result = users[:limit]
                elif "select username, shlep_count, last_shlep from user_stats" in query_lower:
                    user_id = params[0]
                    data = fake_db.user_stats.get(user_id)
                    if data:
                        self.result = [(data['username'], data['shlep_count'], data['last_shlep'])]
                    else:
                        self.result = [(f"Игрок_{user_id}", 0, None)]
                
                return self
            
            def fetchone(self):
                if self.result and len(self.result) > 0:
                    return self.result[0]
                return None
            
            def fetchall(self):
                return self.result or []
            
            def __enter__(self):
                return self
            
            def __exit__(self, *args):
                pass
        
        yield StubConnection()
        return
    
    try:
        if CONNECTION_POOL:
            conn = CONNECTION_POOL.getconn()
            try:
                yield conn
            finally:
                CONNECTION_POOL.putconn(conn)
        else:
            conn = psycopg2.connect(DATABASE_URL)
            try:
                yield conn
            finally:
                conn.close()
    except Exception as e:
        print(f"Ошибка подключения к БД: {e}")
        yield None

def init_db():
    init_connection_pool()  # Инициализируем пул соединений
    
    with get_connection() as conn:
        if conn is None:
            print("БД не инициализирована")
            return
        
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS global_stats (
                    id SERIAL PRIMARY KEY,
                    total_shleps BIGINT DEFAULT 0,
                    last_shlep TIMESTAMP,
                    max_damage INT DEFAULT 0,
                    max_damage_user_id BIGINT,
                    max_damage_username VARCHAR(100),
                    max_damage_date TIMESTAMP
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_stats (
                    user_id BIGINT PRIMARY KEY,
                    username VARCHAR(100),
                    shlep_count INT DEFAULT 0,
                    last_shlep TIMESTAMP
                )
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_stats_shlep_count 
                ON user_stats(shlep_count DESC)
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_stats_user_id 
                ON user_stats(user_id)
            """)
            
            cur.execute("SELECT COUNT(*) FROM global_stats")
            if cur.fetchone()[0] == 0:
                cur.execute("INSERT INTO global_stats (total_shleps) VALUES (0)")
            
            conn.commit()
            print("База данных инициализирована с индексами")

def add_shlep(user_id: int, username: str, damage: int = 0):
    if not DATABASE_URL:
        return fake_db.add_shlep(user_id, username, damage)
    
    with get_connection() as conn:
        if conn is None:
            return (0, 0, 0)
        
        with conn.cursor() as cur:
            now = datetime.now()
            
            cur.execute("""
                UPDATE global_stats 
                SET total_shleps = total_shleps + 1, last_shlep = %s
                WHERE id = 1
                RETURNING total_shleps
            """, (now,))
            total = cur.fetchone()[0]
            
            cur.execute("""
                INSERT INTO user_stats (user_id, username, shlep_count, last_shlep)
                VALUES (%s, %s, 1, %s)
                ON CONFLICT (user_id) 
                DO UPDATE SET 
                    shlep_count = user_stats.shlep_count + 1,
                    last_shlep = %s,
                    username = EXCLUDED.username
                RETURNING shlep_count
            """, (user_id, username, now, now))
            user_count = cur.fetchone()[0]
            
            cur.execute("SELECT max_damage FROM global_stats WHERE id = 1")
            current_max_damage = cur.fetchone()[0] or 0
            
            if damage > current_max_damage:
                cur.execute("""
                    UPDATE global_stats 
                    SET max_damage = %s,
                        max_damage_user_id = %s,
                        max_damage_username = %s,
                        max_damage_date = %s
                    WHERE id = 1
                """, (damage, user_id, username, now))
            
            conn.commit()
            return total, user_count, current_max_damage

def get_stats():
    if not DATABASE_URL:
        stats = fake_db.global_stats
        return (
            stats['total_shleps'], 
            stats['last_shlep'],
            stats['max_damage'],
            stats['max_damage_username'],
            stats['max_damage_date']
        )
    
    with get_connection() as conn:
        if conn is None:
            return (0, None, 0, None, None)
        
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    total_shleps, 
                    last_shlep,
                    max_damage,
                    max_damage_username,
                    max_damage_date
                FROM global_stats 
                WHERE id = 1
            """)
            result = cur.fetchone()
            return result if result else (0, None, 0, None, None)

def get_top_users(limit=10):
    if not DATABASE_URL:
        users = []
        for uid, data in fake_db.user_stats.items():
            users.append((data['username'], data['shlep_count']))
        users.sort(key=lambda x: x[1], reverse=True)
        return users[:limit]
    
    with get_connection() as conn:
        if conn is None:
            return []
        
        with conn.cursor() as cur:
            cur.execute("""
                SELECT username, shlep_count 
                FROM user_stats 
                ORDER BY shlep_count DESC 
                LIMIT %s
            """, (limit,))
            return cur.fetchall()

def get_user_stats(user_id: int):
    if not DATABASE_URL:
        data = fake_db.user_stats.get(user_id)
        if data:
            return (data['username'], data['shlep_count'], data['last_shlep'])
        return (f"Игрок_{user_id}", 0, None)
    
    with get_connection() as conn:
        if conn is None:
            return (f"Игрок_{user_id}", 0, None)
        
        with conn.cursor() as cur:
            cur.execute("""
                SELECT username, shlep_count, last_shlep 
                FROM user_stats 
                WHERE user_id = %s
            """, (user_id,))
            result = cur.fetchone()
            if result:
                return result
            cur.execute("""
                INSERT INTO user_stats (user_id, username, shlep_count)
                VALUES (%s, %s, 0)
                ON CONFLICT (user_id) DO NOTHING
                RETURNING username, shlep_count, last_shlep
            """, (user_id, f"Игрок_{user_id}"))
            conn.commit()
            return (f"Игрок_{user_id}", 0, None)

def close_connection_pool():
    """Закрытие пула соединений при завершении работы"""
    global CONNECTION_POOL
    if CONNECTION_POOL:
        CONNECTION_POOL.closeall()
        print("Пул соединений PostgreSQL закрыт")
