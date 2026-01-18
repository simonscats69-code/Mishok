import os
from datetime import datetime
from contextlib import contextmanager

DATABASE_URL = os.getenv("DATABASE_URL", "")

# ========== ПРОСТАЯ IN-MEMORY БАЗА ==========
class SimpleDB:
    def __init__(self):
        self.global_stats = {
            'total_shleps': 0,
            'last_shlep': None,
            'max_damage': 0,
            'max_damage_user': None,
            'max_damage_date': None
        }
        self.user_stats = {}  # user_id -> {username, count, last_shlep}
        self.chat_stats = {}  # chat_id -> {total, max_damage, max_user, users}
    
    def add_shlep(self, user_id: int, username: str, damage: int = 0, chat_id: int = None):
        now = datetime.now()
        
        # Обновляем глобальную статистику
        self.global_stats['total_shleps'] += 1
        self.global_stats['last_shlep'] = now
        
        if damage > self.global_stats['max_damage']:
            self.global_stats['max_damage'] = damage
            self.global_stats['max_damage_user'] = username
            self.global_stats['max_damage_date'] = now
        
        # Обновляем статистику пользователя
        if user_id not in self.user_stats:
            self.user_stats[user_id] = {
                'username': username,
                'count': 0,
                'last_shlep': None
            }
        
        self.user_stats[user_id]['count'] += 1
        self.user_stats[user_id]['last_shlep'] = now
        self.user_stats[user_id]['username'] = username
        
        # Обновляем статистику чата (если указан)
        if chat_id:
            if chat_id not in self.chat_stats:
                self.chat_stats[chat_id] = {
                    'total_shleps': 0,
                    'max_damage': 0,
                    'max_damage_user': None,
                    'users': {}
                }
            
            self.chat_stats[chat_id]['total_shleps'] += 1
            
            if user_id not in self.chat_stats[chat_id]['users']:
                self.chat_stats[chat_id]['users'][user_id] = {
                    'username': username,
                    'count': 0
                }
            
            self.chat_stats[chat_id]['users'][user_id]['count'] += 1
            
            if damage > self.chat_stats[chat_id]['max_damage']:
                self.chat_stats[chat_id]['max_damage'] = damage
                self.chat_stats[chat_id]['max_damage_user'] = username
        
        return (
            self.global_stats['total_shleps'],
            self.user_stats[user_id]['count'],
            self.global_stats['max_damage']
        )
    
    def get_stats(self):
        stats = self.global_stats
        return (
            stats['total_shleps'],
            stats['last_shlep'],
            stats['max_damage'],
            stats['max_damage_user'],
            stats['max_damage_date']
        )
    
    def get_top_users(self, limit=10):
        users = []
        for user_id, data in self.user_stats.items():
            users.append((data['username'], data['count']))
        
        users.sort(key=lambda x: x[1], reverse=True)
        return users[:limit]
    
    def get_user_stats(self, user_id: int):
        if user_id in self.user_stats:
            data = self.user_stats[user_id]
            return (data['username'], data['count'], data['last_shlep'])
        return (f"Игрок_{user_id}", 0, None)
    
    def get_chat_stats(self, chat_id: int):
        if chat_id in self.chat_stats:
            stats = self.chat_stats[chat_id]
            return {
                'total_shleps': stats['total_shleps'],
                'max_damage': stats['max_damage'],
                'max_damage_user': stats['max_damage_user'],
                'total_users': len(stats['users']),
                'active_today': 0  # Упрощенная версия
            }
        return None
    
    def get_chat_top_users(self, chat_id: int, limit=10):
        if chat_id not in self.chat_stats:
            return []
        
        users = []
        for user_id, data in self.chat_stats[chat_id]['users'].items():
            users.append((data['username'], data['count']))
        
        users.sort(key=lambda x: x[1], reverse=True)
        return users[:limit]

# Глобальный экземпляр базы
db = SimpleDB()

# ========== ИНТЕРФЕЙС ДЛЯ ИМПОРТА ==========
def init_db():
    """Инициализация базы (ничего не делает для in-memory)"""
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
