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
            
            # Таблица для достижений
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_achievements (
                    user_id BIGINT,
                    achievement_id INT,
                    achieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, achievement_id)
                )
            """)
            
            # Инициализируем глобальную статистику если пусто
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
