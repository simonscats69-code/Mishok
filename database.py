import psycopg2
import os
from config import DATABASE_URL
from contextlib import contextmanager

@contextmanager
def get_connection():
    conn = psycopg2.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """Инициализация всех таблиц"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Существующие таблицы
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
            
            # Таблица для достижений
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_achievements (
                    user_id BIGINT,
                    achievement_id INT,
                    achieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, achievement_id)
                )
            """)
            
            # Таблица для ежедневных задач
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
            
            # Таблица для очков (наград)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_points (
                    user_id BIGINT PRIMARY KEY,
                    points INT DEFAULT 0,
                    last_updated TIMESTAMP
                )
            """)
            
            # Инициализируем глобальную статистику
            cur.execute("SELECT COUNT(*) FROM global_stats")
            if cur.fetchone()[0] == 0:
                cur.execute("INSERT INTO global_stats (total_shleps) VALUES (0)")
            
            conn.commit()

# Остальные функции остаются прежними
def add_shlep(user_id: int, username: str):
    """Добавить шлёпок в статистику"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            from datetime import datetime
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
            return cur.fetchone()

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
            from datetime import datetime
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
            
            conn.commit()
            return cur.fetchone()[0]
