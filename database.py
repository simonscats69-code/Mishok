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
    """Инициализация базы данных"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Таблица для глобальной статистики
            cur.execute("""
                CREATE TABLE IF NOT EXISTS global_stats (
                    id SERIAL PRIMARY KEY,
                    total_shleps BIGINT DEFAULT 0,
                    last_shlep TIMESTAMP
                )
            """)
            
            # Таблица для пользователей
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_stats (
                    user_id BIGINT PRIMARY KEY,
                    username VARCHAR(100),
                    shlep_count INT DEFAULT 0,
                    last_shlep TIMESTAMP
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
