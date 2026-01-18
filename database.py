import psycopg2
import os
from config import DATABASE_URL
from contextlib import contextmanager
from datetime import datetime

@contextmanager
def get_connection():
    """Получить соединение с базой данных"""
    conn = psycopg2.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """Инициализация всех таблиц"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            # ===== ОСНОВНЫЕ ТАБЛИЦЫ =====
            
            # Глобальная статистика
            cur.execute("""
                CREATE TABLE IF NOT EXISTS global_stats (
                    id SERIAL PRIMARY KEY,
                    total_shleps BIGINT DEFAULT 0,
                    last_shlep TIMESTAMP
                )
            """)
            
            # Статистика пользователей
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_stats (
                    user_id BIGINT PRIMARY KEY,
                    username VARCHAR(100),
                    shlep_count INT DEFAULT 0,
                    last_shlep TIMESTAMP
                )
            """)
            
            # Очки пользователей
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_points (
                    user_id BIGINT PRIMARY KEY,
                    points INT DEFAULT 0,
                    last_updated TIMESTAMP
                )
            """)
            
            # ===== СИСТЕМА ДОСТИЖЕНИЙ =====
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_achievements (
                    user_id BIGINT,
                    achievement_id INT,
                    achieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, achievement_id)
                )
            """)
            
            # ===== СИСТЕМА УРОВНЕЙ =====
            
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
                CREATE TABLE IF NOT EXISTS level_ups (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    level INT,
                    reward INT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # ===== СИСТЕМА НАВЫКОВ =====
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_skills (
                    user_id BIGINT,
                    skill_id VARCHAR(50),
                    level INT DEFAULT 0,
                    PRIMARY KEY (user_id, skill_id)
                )
            """)
            
            # ===== ДЕТАЛЬНАЯ СТАТИСТИКА =====
            
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
                CREATE TABLE IF NOT EXISTS shlep_sessions (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    shlep_count INT,
                    avg_speed FLOAT,
                    max_combo INT
                )
            """)
            
            # ===== РЕКОРДЫ =====
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS records (
                    record_type VARCHAR(50) PRIMARY KEY,
                    user_id BIGINT,
                    value FLOAT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # ===== ГЛОБАЛЬНЫЕ ЦЕЛИ =====
            
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
            
            # ===== СОБЫТИЯ =====
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS active_events (
                    event_type VARCHAR(50) PRIMARY KEY,
                    multiplier FLOAT,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    description TEXT
                )
            """)
            
            # ===== ЕЖЕДНЕВНЫЕ ЗАДАНИЯ =====
            
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
            
            # Инициализируем глобальную статистику
            cur.execute("SELECT COUNT(*) FROM global_stats")
            if cur.fetchone()[0] == 0:
                cur.execute("INSERT INTO global_stats (total_shleps) VALUES (0)")
            
            conn.commit()

def add_shlep(user_id: int, username: str):
    """Добавить шлёпок в статистику"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            now = datetime.now()
            
            # Обновляем глобальную статистику
            cur.execute("""
                UPDATE global_stats 
                SET total_shleps = total_shleps + 1, last_shlep = %s
                WHERE id = 1
                RETURNING total_shleps
            """, (now,))
            total = cur.fetchone()[0]
            
            # Обновляем статистику пользователя
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
            
            conn.commit()
            return total, user_count

def get_stats():
    """Получить глобальную статистику"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT total_shleps, last_shlep FROM global_stats WHERE id = 1")
            result = cur.fetchone()
            if result:
                return result
            return (0, None)

def get_top_users(limit=10):
    """Топ пользователей по шлёпкам"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT username, shlep_count 
                FROM user_stats 
                ORDER BY shlep_count DESC 
                LIMIT %s
            """, (limit,))
            return cur.fetchall()

def add_points(user_id: int, points: int):
    """Добавить очки пользователю"""
    with get_connection() as conn:
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
    """Получить очки пользователя"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT points FROM user_points WHERE user_id = %s", (user_id,))
            result = cur.fetchone()
            return result[0] if result else 0

def get_user_stats(user_id: int):
    """Получить статистику пользователя"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT username, shlep_count, last_shlep 
                FROM user_stats 
                WHERE user_id = %s
            """, (user_id,))
            return cur.fetchone()
