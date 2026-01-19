import json
import atexit
import signal
import os
from datetime import datetime
from typing import Tuple, Optional, Dict, Any

DATA_FILE = "mishok_data.json"

# ========== IN-MEMORY БАЗА ==========
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
        
        self.load_data()
        atexit.register(self.save_data)
        signal.signal(signal.SIGTERM, self.handle_shutdown)
        signal.signal(signal.SIGINT, self.handle_shutdown)
    
    # ========== СОХРАНЕНИЕ/ЗАГРУЗКА ==========
    def load_data(self):
        """Загружает данные из файла при старте"""
        try:
            if os.path.exists(DATA_FILE):
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.global_stats = data.get('global_stats', self.global_stats)
                    self.user_stats = {int(k): v for k, v in data.get('user_stats', {}).items()}
                    self.chat_stats = {int(k): v for k, v in data.get('chat_stats', {}).items()}
                print(f"✅ Загружено {len(self.user_stats)} пользователей")
        except Exception as e:
            print(f"⚠️ Ошибка загрузки: {e}")
    
    def save_data(self):
        """Сохраняет данные в файл при остановке"""
        try:
            data = {
                'global_stats': self.global_stats,
                'user_stats': self.user_stats,
                'chat_stats': self.chat_stats,
                'saved_at': datetime.now().isoformat()
            }
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"💾 Данные сохранены: {len(self.user_stats)} пользователей")
        except Exception as e:
            print(f"❌ Ошибка сохранения: {e}")
    
    def handle_shutdown(self, signum, frame):
        """Обработчик завершения работы"""
        print(f"\n🛑 Получен сигнал {signum}, сохраняем данные...")
        self.save_data()
        exit(0)
    
    # ========== ОСНОВНЫЕ МЕТОДЫ ==========
    def add_shlep(self, user_id: int, username: str, damage: int = 0, chat_id: int = None) -> Tuple[int, int, int]:
        """Добавляет шлёпок"""
        now = datetime.now()
        
        # Глобальная статистика
        self.global_stats['total_shleps'] += 1
        self.global_stats['last_shlep'] = now.isoformat()
        
        if damage > self.global_stats['max_damage']:
            self.global_stats['max_damage'] = damage
            self.global_stats['max_damage_user'] = username
            self.global_stats['max_damage_date'] = now.isoformat()
        
        # Статистика пользователя
        if user_id not in self.user_stats:
            self.user_stats[user_id] = {
                'username': username,
                'count': 0,
                'last_shlep': None
            }
        
        self.user_stats[user_id]['count'] += 1
        self.user_stats[user_id]['last_shlep'] = now.isoformat()
        self.user_stats[user_id]['username'] = username
        
        # Статистика чата
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
    
    def get_stats(self) -> Tuple[int, Optional[datetime], int, Optional[str], Optional[datetime]]:
        """Глобальная статистика"""
        stats = self.global_stats
        last_shlep = datetime.fromisoformat(stats['last_shlep']) if stats['last_shlep'] else None
        max_date = datetime.fromisoformat(stats['max_damage_date']) if stats['max_damage_date'] else None
        
        return (
            stats['total_shleps'],
            last_shlep,
            stats['max_damage'],
            stats['max_damage_user'],
            max_date
        )
    
    def get_top_users(self, limit: int = 10) -> list:
        """Топ пользователей"""
        users = [(data['username'], data['count']) for data in self.user_stats.values()]
        users.sort(key=lambda x: x[1], reverse=True)
        return users[:limit]
    
    def get_user_stats(self, user_id: int) -> Tuple[str, int, Optional[datetime]]:
        """Статистика пользователя"""
        if user_id in self.user_stats:
            data = self.user_stats[user_id]
            last_shlep = datetime.fromisoformat(data['last_shlep']) if data['last_shlep'] else None
            return (data['username'], data['count'], last_shlep)
        
        # Создаём запись если пользователя нет
        self.user_stats[user_id] = {
            'username': f"Игрок_{user_id}",
            'count': 0,
            'last_shlep': None
        }
        return (f"Игрок_{user_id}", 0, None)
    
    def get_chat_stats(self, chat_id: int) -> Optional[Dict[str, Any]]:
        """Статистика чата"""
        if chat_id not in self.chat_stats:
            return None
        
        stats = self.chat_stats[chat_id]
        return {
            'total_shleps': stats['total_shleps'],
            'max_damage': stats['max_damage'],
            'max_damage_user': stats['max_damage_user'],
            'total_users': len(stats['users']),
            'active_today': 0  # Упрощённо
        }
    
    def get_chat_top_users(self, chat_id: int, limit: int = 10) -> list:
        """Топ пользователей в чате"""
        if chat_id not in self.chat_stats:
            return []
        
        users = [(data['username'], data['count']) 
                for data in self.chat_stats[chat_id]['users'].values()]
        users.sort(key=lambda x: x[1], reverse=True)
        return users[:limit]
    
    # ========== ДОПОЛНИТЕЛЬНЫЕ МЕТОДЫ ==========
    def get_database_info(self) -> Dict[str, Any]:
        """Информация о базе"""
        return {
            'total_users': len(self.user_stats),
            'total_chats': len(self.chat_stats),
            'total_shleps': self.global_stats['total_shleps'],
            'data_file': DATA_FILE,
            'file_exists': os.path.exists(DATA_FILE)
        }
    
    def backup_now(self) -> bool:
        """Принудительное сохранение"""
        try:
            self.save_data()
            return True
        except:
            return False
    
    def clear_all(self) -> None:
        """Очистка всех данных (для тестов)"""
        self.global_stats = {
            'total_shleps': 0,
            'last_shlep': None,
            'max_damage': 0,
            'max_damage_user': None,
            'max_damage_date': None
        }
        self.user_stats.clear()
        self.chat_stats.clear()
        print("🗑️ Все данные очищены")

# ========== ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР ==========
db = SimpleDB()

# ========== ИНТЕРФЕЙС ДЛЯ ИМПОРТА ==========
def init_db():
    """Инициализация (уже в конструкторе)"""
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

def backup_database():
    """Создание бэкапа"""
    return db.backup_now()

def get_database_info():
    """Информация о БД"""
    return db.get_database_info()

# ========== ТЕСТ ==========
if __name__ == "__main__":
    print("🔍 Тест in-memory базы для BHost")
    print("=" * 50)
    
    # Тестовые данные
    db.add_shlep(123, "Тестовый", 15, 456)
    db.add_shlep(123, "Тестовый", 20, 456)
    db.add_shlep(789, "Другой", 30)
    
    info = db.get_database_info()
    print(f"👥 Пользователей: {info['total_users']}")
    print(f"💬 Чатов: {info['total_chats']}")
    print(f"👊 Шлёпков: {info['total_shleps']}")
    print(f"💾 Файл: {info['data_file']} ({'существует' if info['file_exists'] else 'не существует'})")
    
    print("\n🏆 Топ пользователей:")
    for i, (name, count) in enumerate(db.get_top_users(5), 1):
        print(f"  {i}. {name}: {count}")
    
    print("=" * 50)
    print("✅ База работает! Данные сохранятся при остановке.")
