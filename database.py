#!/usr/bin/env python3
"""
Database module for Mishok bot - SQLite implementation
"""

import os
import sqlite3
import json
import shutil
from datetime import datetime
from typing import Optional, Tuple, Dict, Any, List

# ========== КОНСТАНТЫ ==========
SQLITE_FILE = "mishok.db"
BACKUP_DIR = "db_backups"
OLD_DATA_FILE = "old_data.json"

# ========== УТИЛИТЫ БЭКАПА ==========
def ensure_backup_dir():
    """Создаёт директорию для бэкапов"""
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)

def create_backup():
    """Создаёт резервную копию базы"""
    ensure_backup_dir()
    
    if not os.path.exists(SQLITE_FILE):
        return False
    
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(BACKUP_DIR, f"mishok_backup_{timestamp}.db")
        shutil.copy2(SQLITE_FILE, backup_file)
        
        # Удаляем старые бэкапы (оставляем последние 7)
        backups = sorted(
            [f for f in os.listdir(BACKUP_DIR) if f.endswith('.db')],
            reverse=True
        )
        
        for old_backup in backups[7:]:
            os.remove(os.path.join(BACKUP_DIR, old_backup))
        
        return True
    except Exception as e:
        print(f"⚠️ Ошибка при создании бэкапа: {e}")
        return False

# ========== SQLite БАЗА ДАННЫХ ==========
class Database:
    def __init__(self):
        self.conn = None
        self.init_database()
        create_backup()
        self.migrate_old_data()
    
    def get_connection(self):
        """Получает соединение с БД"""
        if self.conn is None:
            self.conn = sqlite3.connect(SQLITE_FILE, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
        return self.conn
    
    def init_database(self):
        """Инициализирует таблицы"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Основные таблицы
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shleps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                damage INTEGER DEFAULT 10,
                chat_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS global_stats (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                total_shleps INTEGER DEFAULT 0,
                last_shlep TIMESTAMP,
                max_damage INTEGER DEFAULT 0,
                max_damage_user TEXT,
                max_damage_date TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                chat_id INTEGER PRIMARY KEY,
                total_shleps INTEGER DEFAULT 0,
                max_damage INTEGER DEFAULT 0,
                max_damage_user TEXT,
                last_activity TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_users (
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                shlep_count INTEGER DEFAULT 0,
                last_shlep TIMESTAMP,
                PRIMARY KEY (chat_id, user_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Индексы для скорости
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_shleps_user ON shleps(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_shleps_chat ON shleps(chat_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_shleps_date ON shleps(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_users ON chat_users(chat_id, user_id)")
        
        # Создаём запись глобальной статистики
        cursor.execute("INSERT OR IGNORE INTO global_stats (id) VALUES (1)")
        
        conn.commit()
    
    def migrate_old_data(self):
        """Мигрирует данные из старой in-memory системы"""
        if not os.path.exists(OLD_DATA_FILE):
            return 0
        
        try:
            with open(OLD_DATA_FILE, 'r', encoding='utf-8') as f:
                old_data = json.load(f)
            
            migrated = 0
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Мигрируем пользователей
            user_stats = old_data.get('user_stats', {})
            for user_id_str, data in user_stats.items():
                try:
                    user_id = int(user_id_str)
                    username = data.get('username', f'Игрок_{user_id}')
                    count = data.get('count', 0)
                    
                    if count > 0:
                        # Добавляем пользователя
                        cursor.execute("""
                            INSERT OR IGNORE INTO users (user_id, username) 
                            VALUES (?, ?)
                        """, (user_id, username))
                        
                        # Добавляем шлёпки
                        for _ in range(min(count, 1000)):  # Ограничиваем на случай огромных чисел
                            cursor.execute("""
                                INSERT INTO shleps (user_id, damage, created_at)
                                VALUES (?, 10, datetime('now', '-? minutes'))
                            """, (user_id, _))
                        
                        migrated += 1
                except (ValueError, KeyError):
                    continue
            
            # Обновляем глобальную статистику
            global_stats = old_data.get('global_stats', {})
            total = global_stats.get('total_shleps', 0)
            max_damage = global_stats.get('max_damage', 0)
            max_user = global_stats.get('max_damage_user', '')
            
            if total > 0:
                cursor.execute("""
                    UPDATE global_stats 
                    SET total_shleps = ?,
                        max_damage = ?,
                        max_damage_user = ?
                    WHERE id = 1
                """, (total, max_damage, max_user))
            
            conn.commit()
            
            # Переименовываем старый файл
            os.rename(OLD_DATA_FILE, f"{OLD_DATA_FILE}.migrated")
            print(f"✅ Мигрировано {migrated} пользователей из старой системы")
            return migrated
            
        except Exception as e:
            print(f"⚠️ Ошибка миграции: {e}")
            return 0
    
    # ========== ОСНОВНЫЕ МЕТОДЫ (совместимые со старым интерфейсом) ==========
    
    def add_shlep(self, user_id: int, username: str, damage: int = 0, chat_id: int = None):
        """Добавляет шлёпок - основной метод"""
        conn = self.get_connection()
        cursor = conn.cursor()
        now = datetime.now()
        
        try:
            # 1. Обновляем/добавляем пользователя
            cursor.execute("""
                INSERT OR REPLACE INTO users (user_id, username, last_active)
                VALUES (?, ?, ?)
            """, (user_id, username, now))
            
            # 2. Добавляем запись о шлёпке
            cursor.execute("""
                INSERT INTO shleps (user_id, damage, chat_id, created_at)
                VALUES (?, ?, ?, ?)
            """, (user_id, damage, chat_id, now))
            
            # 3. Обновляем глобальную статистику
            cursor.execute("""
                UPDATE global_stats 
                SET total_shleps = total_shleps + 1,
                    last_shlep = ?
                WHERE id = 1
            """, (now,))
            
            # 4. Проверяем рекорд урона
            cursor.execute("SELECT max_damage, max_damage_user FROM global_stats WHERE id = 1")
            row = cursor.fetchone()
            current_max = row['max_damage'] if row else 0
            
            if damage > current_max:
                cursor.execute("""
                    UPDATE global_stats 
                    SET max_damage = ?,
                        max_damage_user = ?,
                        max_damage_date = ?
                    WHERE id = 1
                """, (damage, username, now))
            
            # 5. Обновляем статистику чата (если указан)
            if chat_id:
                # Общая статистика чата
                cursor.execute("""
                    INSERT OR REPLACE INTO chats (chat_id, total_shleps, last_activity)
                    VALUES (?, 
                        COALESCE((SELECT total_shleps FROM chats WHERE chat_id = ?), 0) + 1,
                        ?)
                """, (chat_id, chat_id, now))
                
                # Проверяем рекорд в чате
                cursor.execute("SELECT max_damage FROM chats WHERE chat_id = ?", (chat_id,))
                chat_row = cursor.fetchone()
                chat_max = chat_row['max_damage'] if chat_row else 0
                
                if damage > chat_max:
                    cursor.execute("""
                        UPDATE chats 
                        SET max_damage = ?,
                            max_damage_user = ?
                        WHERE chat_id = ?
                    """, (damage, username, chat_id))
                
                # Статистика пользователя в чате
                cursor.execute("""
                    INSERT OR REPLACE INTO chat_users (chat_id, user_id, shlep_count, last_shlep)
                    VALUES (?, ?, 
                        COALESCE((SELECT shlep_count FROM chat_users WHERE chat_id = ? AND user_id = ?), 0) + 1,
                        ?)
                """, (chat_id, user_id, chat_id, user_id, now))
            
            conn.commit()
            
            # Получаем обновлённые данные для возврата
            cursor.execute("SELECT total_shleps FROM global_stats WHERE id = 1")
            total_shleps = cursor.fetchone()['total_shleps']
            
            cursor.execute("SELECT COUNT(*) as user_count FROM shleps WHERE user_id = ?", (user_id,))
            user_count = cursor.fetchone()['user_count']
            
            cursor.execute("SELECT max_damage FROM global_stats WHERE id = 1")
            current_max_damage = cursor.fetchone()['max_damage']
            
            return (total_shleps, user_count, current_max_damage)
            
        except Exception as e:
            conn.rollback()
            print(f"❌ Ошибка add_shlep: {e}")
            return (0, 0, 0)
    
    def get_stats(self):
        """Возвращает глобальную статистику"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT total_shleps, last_shlep, max_damage, max_damage_user, max_damage_date
            FROM global_stats WHERE id = 1
        """)
        
        row = cursor.fetchone()
        if row:
            return (
                row['total_shleps'],
                datetime.fromisoformat(row['last_shlep']) if row['last_shlep'] else None,
                row['max_damage'],
                row['max_damage_user'],
                datetime.fromisoformat(row['max_damage_date']) if row['max_damage_date'] else None
            )
        return (0, None, 0, None, None)
    
    def get_top_users(self, limit=10):
        """Возвращает топ пользователей"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT u.username, COUNT(s.id) as count
            FROM users u
            LEFT JOIN shleps s ON u.user_id = s.user_id
            GROUP BY u.user_id, u.username
            ORDER BY count DESC
            LIMIT ?
        """, (limit,))
        
        return [(row['username'] or f"Игрок", row['count']) for row in cursor.fetchall()]
    
    def get_user_stats(self, user_id: int):
        """Статистика пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Получаем основную информацию
        cursor.execute("""
            SELECT u.username, COUNT(s.id) as count, MAX(s.created_at) as last_shlep
            FROM users u
            LEFT JOIN shleps s ON u.user_id = s.user_id
            WHERE u.user_id = ?
            GROUP BY u.user_id, u.username
        """, (user_id,))
        
        row = cursor.fetchone()
        if row and row['count'] > 0:
            last_shlep = datetime.fromisoformat(row['last_shlep']) if row['last_shlep'] else None
            return (row['username'] or f"Игрок_{user_id}", row['count'], last_shlep)
        
        # Если пользователя нет, создаём запись
        cursor.execute("""
            INSERT OR IGNORE INTO users (user_id, username)
            VALUES (?, ?)
        """, (user_id, f"Игрок_{user_id}"))
        conn.commit()
        
        return (f"Игрок_{user_id}", 0, None)
    
    def get_chat_stats(self, chat_id: int):
        """Статистика чата"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT total_shleps, max_damage, max_damage_user, last_activity
            FROM chats WHERE chat_id = ?
        """, (chat_id,))
        
        row = cursor.fetchone()
        if row:
            # Считаем уникальных пользователей
            cursor.execute("SELECT COUNT(DISTINCT user_id) as total_users FROM shleps WHERE chat_id = ?", (chat_id,))
            total_users = cursor.fetchone()['total_users']
            
            # Активные сегодня
            cursor.execute("""
                SELECT COUNT(DISTINCT user_id) as active_today 
                FROM shleps 
                WHERE chat_id = ? AND DATE(created_at) = DATE('now')
            """, (chat_id,))
            active_today = cursor.fetchone()['active_today']
            
            return {
                'total_shleps': row['total_shleps'],
                'max_damage': row['max_damage'],
                'max_damage_user': row['max_damage_user'],
                'total_users': total_users,
                'active_today': active_today
            }
        return None
    
    def get_chat_top_users(self, chat_id: int, limit=10):
        """Топ пользователей в чате"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT u.username, cu.shlep_count as count
            FROM chat_users cu
            JOIN users u ON cu.user_id = u.user_id
            WHERE cu.chat_id = ?
            ORDER BY cu.shlep_count DESC
            LIMIT ?
        """, (chat_id, limit))
        
        result = []
        for row in cursor.fetchall():
            result.append((row['username'] or "Игрок", row['count']))
        return result

# ========== ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР И ИНТЕРФЕЙС ==========
db = Database()

def init_db():
    """Инициализация базы (для совместимости)"""
    pass

def add_shlep(user_id: int, username: str, damage: int = 0, chat_id: int = None):
    return db.add_shlep(user_id, username, damage, chat_id)

def get_stats():
    return db.get_stats()

def get_top_users(limit=10):
    return db.get_top_users(limit)

def get_user_stats(user_id: int):
    return db.get_user_stats(user_id)

def get_chat_stats(chat_id: int):
    return db.get_chat_stats(chat_id)

def get_chat_top_users(chat_id: int, limit=10):
    return db.get_chat_top_users(chat_id, limit)

# Пустые функции для совместимости
def create_chat_vote(*args, **kwargs): return 1
def get_chat_vote(vote_id: int): return None
def update_chat_vote(vote_id: int, user_id: int, vote_type: str): return True
def assign_chat_role(*args, **kwargs): return True
def get_user_roles(chat_id: int, user_id: int): return []
def get_chat_roles_stats(chat_id: int): return {}

# ========== ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ ==========
def backup_database():
    """Создаёт бэкап базы данных"""
    return create_backup()

def get_database_info():
    """Возвращает информацию о базе данных"""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    info = {
        'file_size': os.path.getsize(SQLITE_FILE) if os.path.exists(SQLITE_FILE) else 0,
        'backup_count': len(os.listdir(BACKUP_DIR)) if os.path.exists(BACKUP_DIR) else 0
    }
    
    # Количество записей
    tables = ['users', 'shleps', 'chats', 'chat_users']
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
        info[f'{table}_count'] = cursor.fetchone()['count']
    
    return info

if __name__ == "__main__":
    print("🔍 Тестирование базы данных...")
    print(f"Файл БД: {SQLITE_FILE}")
    print(f"Размер: {os.path.getsize(SQLITE_FILE) if os.path.exists(SQLITE_FILE) else 0} байт")
    print(f"Бэкапы в: {BACKUP_DIR}")
