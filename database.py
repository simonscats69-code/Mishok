import os
from contextlib import contextmanager
from datetime import datetime

from config import DATABASE_URL

try:
    import psycopg2
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

class FakeDatabase:
    """Заглушка базы данных для работы без PostgreSQL"""
    def __init__(self):
        self.global_stats = {'total_shleps': 0, 'last_shlep': None}
        self.user_stats = {}
        self.user_points = {}
        self.user_achievements = {}
        self.user_xp = {}
        self.user_skills = {}
        self.detailed_stats = []
        self.records = {}
        self.global_goals = [
            {'id': 1, 'goal_name': 'Миллионный шлёпок 🎯', 'target_value': 1000000, 'current_value': 0, 'is_active': True},
            {'id': 2, 'goal_name': 'Неделя активности 📈', 'target_value': 50000, 'current_value': 0, 'is_active': True}
        ]
        self.user_daily_tasks = {}
    
    def add_shlep(self, user_id: int, username: str):
        now = datetime.now()
        self.global_stats['total_shleps'] += 1
        self.global_stats['last_shlep'] = now
        
        if user_id not in self.user_stats:
            self.user_stats[user_id] = {'username': username, 'shlep_count': 0, 'last_shlep': None}
        
        self.user_stats[user_id]['shlep_count'] += 1
        self.user_stats[user_id]['last_shlep'] = now
        self.user_stats[user_id]['username'] = username
        
        for goal in self.global_goals:
            if goal['is_active']:
                goal['current_value'] += 1
        
        return self.global_stats['total_shleps'], self.user_stats[user_id]['shlep_count']

fake_db = FakeDatabase()

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
                    fake_db.global_stats = {'total_shleps': 0, 'last_shlep': None}
                elif "update global_stats" in query_lower and "returning total_shleps" in query_lower:
                    fake_db.global_stats['last_shlep'] = params[0] if params else datetime.now()
                    self.result = [(fake_db.global_stats['total_shleps'],)]
                elif "select total_shleps, last_shlep from global_stats" in query_lower:
                    self.result = [(fake_db.global_stats['total_shleps'], fake_db.global_stats['last_shlep'])]
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
                elif "select points from user_points" in query_lower:
                    user_id = params[0]
                    self.result = [(fake_db.user_points.get(user_id, 0),)]
                elif "insert into user_points" in query_lower or "update user_points" in query_lower:
                    if "returning points" in query_lower:
                        user_id = params[0]
                        points = params[1]
                        fake_db.user_points[user_id] = fake_db.user_points.get(user_id, 0) + points
                        self.result = [(fake_db.user_points[user_id],)]
                elif "select username, shlep_count, last_shlep from user_stats" in query_lower:
                    user_id = params[0]
                    data = fake_db.user_stats.get(user_id)
                    if data:
                        self.result = [(data['username'], data['shlep_count'], data['last_shlep'])]
                    else:
                        self.result = []
                
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
        conn = psycopg2.connect(DATABASE_URL)
        try:
            yield conn
        finally:
            conn.close()
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}")
        yield None

def init_db():
    with get_connection() as conn:
        if conn is None:
            print("⚠️ БД не инициализирована (нет соединения)")
            return
        
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS global_stats (
                    id SERIAL PRIMARY KEY,
                    total_shleps BIGINT DEFAULT 0,
                    last_shlep TIMESTAMP
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
                CREATE TABLE IF NOT EXISTS user_points (
                    user_id BIGINT PRIMARY KEY,
                    points INT DEFAULT 0,
                    last_updated TIMESTAMP
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_achievements (
                    user_id BIGINT,
                    achievement_id INT,
                    achieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, achievement_id)
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_xp (
                    user_id BIGINT PRIMARY KEY,
                    xp BIGINT DEFAULT 0,
                    last_updated TIMESTAMP
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS xp_history (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    xp_amount INT,
                    reason VARCHAR(100),
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_skills (
                    user_id BIGINT,
                    skill_id VARCHAR(50),
                    level INT DEFAULT 0,
                    PRIMARY KEY (user_id, skill_id)
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS detailed_stats (
                    user_id BIGINT,
                    stat_date DATE,
                    hour INT,
                    shlep_count INT DEFAULT 0,
                    PRIMARY KEY (user_id, stat_date, hour)
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS records (
                    record_type VARCHAR(50) PRIMARY KEY,
                    user_id BIGINT,
                    value FLOAT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS global_goals (
                    id SERIAL PRIMARY KEY,
                    goal_name VARCHAR(100),
                    target_value BIGINT,
                    current_value BIGINT DEFAULT 0,
                    reward_type VARCHAR(50),
                    reward_value INT,
                    is_active BOOLEAN DEFAULT TRUE,
                    start_date DATE,
                    end_date DATE
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS active_events (
                    event_type VARCHAR(50) PRIMARY KEY,
                    multiplier FLOAT,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    description TEXT
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_daily_tasks (
                    user_id BIGINT,
                    task_date DATE,
                    task_id INT,
                    progress INT DEFAULT 0,
                    completed BOOLEAN DEFAULT FALSE,
                    PRIMARY KEY (user_id, task_date, task_id)
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS shlep_sessions (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    end_time TIMESTAMP,
                    shlep_count INT DEFAULT 0,
                    avg_speed FLOAT
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS level_ups (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    level INT,
                    reward INT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS goal_completions (
                    id SERIAL PRIMARY KEY,
                    goal_id INT,
                    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    reward_type VARCHAR(50),
                    reward_value INT
                )
            """)
            
            cur.execute("SELECT COUNT(*) FROM global_stats")
            if cur.fetchone()[0] == 0:
                cur.execute("INSERT INTO global_stats (total_shleps) VALUES (0)")
            
            cur.execute("SELECT COUNT(*) FROM global_goals")
            if cur.fetchone()[0] == 0:
                cur.execute("""
                    INSERT INTO global_goals 
                    (goal_name, target_value, current_value, reward_type, reward_value, is_active)
                    VALUES 
                    ('Миллионный шлёпок 🎯', 1000000, 0, 'points', 10000, TRUE),
                    ('Неделя активности 📈', 50000, 0, 'multiplier', 150, TRUE)
                """)
            
            conn.commit()
            print("✅ База данных инициализирована")

def add_shlep(user_id: int, username: str):
    if not DATABASE_URL:
        return fake_db.add_shlep(user_id, username)
    
    with get_connection() as conn:
        if conn is None:
            return (0, 0)
        
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
            
            cur.execute("""
                UPDATE global_goals 
                SET current_value = current_value + 1
                WHERE is_active = TRUE
            """)
            
            conn.commit()
            return total, user_count

def get_stats():
    if not DATABASE_URL:
        return (fake_db.global_stats['total_shleps'], fake_db.global_stats['last_shlep'])
    
    with get_connection() as conn:
        if conn is None:
            return (0, None)
        
        with conn.cursor() as cur:
            cur.execute("SELECT total_shleps, last_shlep FROM global_stats WHERE id = 1")
            result = cur.fetchone()
            return result if result else (0, None)

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

def add_points(user_id: int, points: int):
    if not DATABASE_URL:
        fake_db.user_points[user_id] = fake_db.user_points.get(user_id, 0) + points
        return fake_db.user_points[user_id]
    
    with get_connection() as conn:
        if conn is None:
            return 0
        
        with conn.cursor() as cur:
            now = datetime.now()
            
            cur.execute("""
                INSERT INTO user_points (user_id, points, last_updated)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id) 
                DO UPDATE SET 
                    points = user_points.points + EXCLUDED.points,
                    last_updated = EXCLUDED.last_updated
                RETURNING points
            """, (user_id, points, now))
            
            result = cur.fetchone()
            conn.commit()
            return result[0] if result else 0

def get_user_points(user_id: int):
    if not DATABASE_URL:
        return fake_db.user_points.get(user_id, 0)
    
    with get_connection() as conn:
        if conn is None:
            return 0
        
        with conn.cursor() as cur:
            cur.execute("SELECT points FROM user_points WHERE user_id = %s", (user_id,))
            result = cur.fetchone()
            return result[0] if result else 0

def get_user_stats(user_id: int):
    if not DATABASE_URL:
        data = fake_db.user_stats.get(user_id)
        if data:
            return (data['username'], data['shlep_count'], data['last_shlep'])
        return (None, 0, None)
    
    with get_connection() as conn:
        if conn is None:
            return (None, 0, None)
        
        with conn.cursor() as cur:
            cur.execute("""
                SELECT username, shlep_count, last_shlep 
                FROM user_stats 
                WHERE user_id = %s
            """, (user_id,))
            return cur.fetchone()

def get_connection_for_system():
    return get_connection()

def execute_query(query, params=None):
    with get_connection() as conn:
        if conn is None:
            return None
        
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            if query.strip().upper().startswith('SELECT'):
                return cur.fetchall()
            conn.commit()
            return None

def test_connection():
    if not DATABASE_URL:
        return True, "✅ Используется заглушка БД (без PostgreSQL)"
    
    try:
        with get_connection() as conn:
            if conn is None:
                return False, "БД не настроена (используется заглушка)"
            
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                result = cur.fetchone()
                return True, "✅ Соединение с БД успешно"
    except Exception as e:
        return False, f"❌ Ошибка соединения: {e}"
