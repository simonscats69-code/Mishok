import os
from contextlib import contextmanager
from datetime import datetime

from config import DATABASE_URL

try:
    import psycopg2
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    print("⚠️ psycopg2 не установлен, используется заглушка БД")

@contextmanager
def get_connection():
    if not PSYCOPG2_AVAILABLE or not DATABASE_URL or "your_database_url" in DATABASE_URL:
        class StubConnection:
            def cursor(self): 
                return StubCursor()
            def commit(self): 
                pass
            def close(self): 
                pass
        
        class StubCursor:
            def execute(self, query, params=None):
                return None
            def fetchone(self):
                return (0, None)
            def fetchall(self):
                return []
            def __enter__(self):
                return self
            def __exit__(self, exc_type, exc_val, exc_tb):
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
    with get_connection() as conn:
        if conn is None:
            return (0, None)
        
        with conn.cursor() as cur:
            cur.execute("SELECT total_shleps, last_shlep FROM global_stats WHERE id = 1")
            result = cur.fetchone()
            return result if result else (0, None)

def get_top_users(limit=10):
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
    with get_connection() as conn:
        if conn is None:
            return 0
        
        with conn.cursor() as cur:
            cur.execute("SELECT points FROM user_points WHERE user_id = %s", (user_id,))
            result = cur.fetchone()
            return result[0] if result else 0

def get_user_stats(user_id: int):
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
