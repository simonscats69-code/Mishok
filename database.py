import json
import os
import threading
import time
import atexit
import signal
from datetime import datetime, timedelta
import shutil

# =================== НАСТРОЙКА ПУТЕЙ ДЛЯ BOTHOST ===================
# Используем папку 'data' для постоянного хранения
# Эта папка должна быть добавлена в .gitignore

def get_storage_path():
    """
    Определяем путь для хранения данных.
    Приоритет: папка 'data' -> текущая директория
    """
    # Основная папка для данных (не отслеживается в Git)
    data_dir = "data"
    
    # Проверяем существование и доступность папки 'data'
    if os.path.exists(data_dir):
        if os.path.isdir(data_dir):
            # Проверяем возможность записи
            test_file = os.path.join(data_dir, ".write_test")
            try:
                with open(test_file, "w") as f:
                    f.write("test")
                os.remove(test_file)
                print(f"✅ [Database] Используем папку '{data_dir}' для постоянного хранения")
                return data_dir
            except Exception as e:
                print(f"⚠️ [Database] Папка '{data_dir}' доступна, но запись невозможна: {e}")
        else:
            print(f"⚠️ [Database] '{data_dir}' существует, но это не папка")
    else:
        # Пытаемся создать папку 'data'
        try:
            os.makedirs(data_dir, exist_ok=True)
            print(f"✅ [Database] Создана папка '{data_dir}' для постоянного хранения")
            return data_dir
        except Exception as e:
            print(f"⚠️ [Database] Не удалось создать папку '{data_dir}': {e}")
    
    # Резервный вариант: текущая директория
    print("⚠️ [Database] Используем текущую директорию (данные могут не сохраниться при обновлении)")
    return "."

# Определяем пути
STORAGE_PATH = get_storage_path()
DATA_FILE = os.path.join(STORAGE_PATH, "mishok_data.json")
BACKUP_DIR = os.path.join(STORAGE_PATH, "backups")

print(f"📁 [Database] Файл данных: {DATA_FILE}")
print(f"📁 [Database] Папка для бэкапов: {BACKUP_DIR}")

class SimpleDB:
    def __init__(self):
        self.global_stats = {
            'total_shleps': 0,
            'last_shlep': None,
            'max_damage': 0,
            'max_damage_user': None,
            'max_damage_date': None
        }
        self.user_stats = {}
        self.chat_stats = {}
        self.detailed_stats = {}
        
        # Создаем директории (если не существуют)
        os.makedirs(STORAGE_PATH, exist_ok=True)
        os.makedirs(BACKUP_DIR, exist_ok=True)
        
        self.load_data()
        
        # Регистрируем обработчики для корректного завершения
        atexit.register(self.save_data)
        signal.signal(signal.SIGTERM, self.handle_shutdown)
        signal.signal(signal.SIGINT, self.handle_shutdown)
        
        # Запускаем фоновый поток для автосохранения
        threading.Thread(target=self.auto_save_loop, daemon=True).start()
        
        print(f"✅ [Database] База данных инициализирована. Всего шлёпков: {self.global_stats['total_shleps']}")
    
    def auto_save_loop(self):
        """Фоновое автосохранение каждые 5 минут"""
        while True:
            time.sleep(300)  # 5 минут
            try:
                self.save_data()
                print("💾 [Database] Автосохранение выполнено")
            except Exception as e:
                print(f"⚠️ [Database] Ошибка автосохранения: {e}")
    
    def load_data(self):
        """Загрузка данных из файла"""
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                self.global_stats = data.get('global_stats', self.global_stats)
                
                # Преобразуем ключи строк в int для совместимости
                self.user_stats = {int(k): v for k, v in data.get('user_stats', {}).items()}
                self.chat_stats = {int(k): v for k, v in data.get('chat_stats', {}).items()}
                self.detailed_stats = {int(k): v for k, v in data.get('detailed_stats', {}).items()}
                
                saved_at = data.get('saved_at', 'неизвестно')
                print(f"✅ [Database] Данные загружены (сохранены: {saved_at})")
                print(f"   👥 Пользователей: {len(self.user_stats)}")
                print(f"   👊 Всего шлёпков: {self.global_stats['total_shleps']}")
                
            except Exception as e:
                print(f"❌ [Database] Ошибка загрузки данных: {e}")
                # Создаем резервную копию поврежденного файла
                try:
                    backup_name = f"corrupted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    backup_path = os.path.join(BACKUP_DIR, backup_name)
                    shutil.copy2(DATA_FILE, backup_path)
                    print(f"📦 [Database] Создана резервная копия поврежденного файла: {backup_path}")
                except:
                    pass
        else:
            print("📝 [Database] Файл данных не найден, начинаем с чистого листа")
    
    def save_data(self):
        """Сохранение данных в файл"""
        try:
            data = {
                'global_stats': self.global_stats,
                'user_stats': self.user_stats,
                'chat_stats': self.chat_stats,
                'detailed_stats': self.detailed_stats,
                'saved_at': datetime.now().isoformat()
            }
            
            # Создаем временный файл для безопасной записи
            temp_file = DATA_FILE + '.tmp'
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # Заменяем старый файл новым
            if os.path.exists(DATA_FILE):
                os.replace(temp_file, DATA_FILE)
            else:
                os.rename(temp_file, DATA_FILE)
            
            print(f"💾 [Database] Данные сохранены ({self.global_stats['total_shleps']} шлёпков)")
            return True
            
        except Exception as e:
            print(f"❌ [Database] Ошибка сохранения данных: {e}")
            return False
    
    def handle_shutdown(self, signum, frame):
        """Обработчик завершения работы"""
        print(f"🔄 [Database] Завершение работы (сигнал: {signum})...")
        self.save_data()
        print("👋 [Database] Данные сохранены, завершаем работу")
        exit(0)
    
    def add_shlep(self, user_id, username, damage=0, chat_id=None):
        """Добавление нового шлёпка"""
        now = datetime.now()
        date_str = now.date().isoformat()
        hour = now.hour
        
        # Обновляем глобальную статистику
        self.global_stats['total_shleps'] += 1
        self.global_stats['last_shlep'] = now.isoformat()
        
        if damage > self.global_stats['max_damage']:
            self.global_stats['max_damage'] = damage
            self.global_stats['max_damage_user'] = username
            self.global_stats['max_damage_date'] = now.isoformat()
        
        # Обновляем статистику пользователя
        if user_id not in self.user_stats:
            self.user_stats[user_id] = {
                'username': username,
                'count': 0,
                'last_shlep': None
            }
        
        self.user_stats[user_id]['count'] += 1
        self.user_stats[user_id]['last_shlep'] = now.isoformat()
        self.user_stats[user_id]['username'] = username
        
        # Детальная статистика
        if user_id not in self.detailed_stats:
            self.detailed_stats[user_id] = {}
        
        if date_str not in self.detailed_stats[user_id]:
            self.detailed_stats[user_id][date_str] = {}
        
        if hour not in self.detailed_stats[user_id][date_str]:
            self.detailed_stats[user_id][date_str][hour] = 0
        
        self.detailed_stats[user_id][date_str][hour] += 1
        
        # Статистика чата (если передан chat_id)
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
        
        # Автосохранение при каждом шлёпке
        self.save_data()
        
        return (
            self.global_stats['total_shleps'],
            self.user_stats[user_id]['count'],
            self.global_stats['max_damage']
        )
    
    def get_stats(self):
        """Получение глобальной статистики"""
        s = self.global_stats
        last = datetime.fromisoformat(s['last_shlep']) if s['last_shlep'] else None
        maxd = datetime.fromisoformat(s['max_damage_date']) if s['max_damage_date'] else None
        
        return (
            s['total_shleps'],
            last,
            s['max_damage'],
            s['max_damage_user'],
            maxd
        )
    
    def get_top_users(self, limit=10):
        """Топ пользователей"""
        users = [(data['username'], data['count']) for data in self.user_stats.values()]
        users.sort(key=lambda x: x[1], reverse=True)
        return users[:limit]
    
    def get_user_stats(self, user_id):
        """Статистика пользователя"""
        if user_id in self.user_stats:
            d = self.user_stats[user_id]
            last = datetime.fromisoformat(d['last_shlep']) if d['last_shlep'] else None
            return (d['username'], d['count'], last)
        
        # Если пользователя нет, создаем запись
        self.user_stats[user_id] = {
            'username': f"Игрок_{user_id}",
            'count': 0,
            'last_shlep': None
        }
        return (f"Игрок_{user_id}", 0, None)
    
    def get_chat_stats(self, chat_id):
        """Статистика чата"""
        if chat_id not in self.chat_stats:
            return None
        
        s = self.chat_stats[chat_id]
        return {
            'total_shleps': s['total_shleps'],
            'max_damage': s['max_damage'],
            'max_damage_user': s['max_damage_user'],
            'total_users': len(s['users']),
            'active_today': 0  # Можно расширить при необходимости
        }
    
    def get_chat_top_users(self, chat_id, limit=10):
        """Топ пользователей в чате"""
        if chat_id not in self.chat_stats:
            return []
        
        users = [
            (data['username'], data['count']) 
            for data in self.chat_stats[chat_id]['users'].values()
        ]
        users.sort(key=lambda x: x[1], reverse=True)
        return users[:limit]
    
    def get_detailed_stats(self, user_id, days=30):
        """Детальная статистика пользователя"""
        result = {
            'daily_activity': {},
            'hourly_distribution': [0] * 24,
            'summary': {}
        }
        
        if user_id not in self.detailed_stats:
            return result
        
        end = datetime.now().date()
        start = end - timedelta(days=days - 1)
        cur = start
        dates = self.detailed_stats[user_id]
        
        # Дневная активность
        while cur <= end:
            date_str = cur.isoformat()
            daily = sum(dates.get(date_str, {}).values()) if date_str in dates else 0
            result['daily_activity'][date_str] = daily
            cur += timedelta(days=1)
        
        # Часовое распределение
        for date_str, hours in dates.items():
            for h, c in hours.items():
                if 0 <= h < 24:
                    result['hourly_distribution'][h] += c
        
        # Сводка
        total = sum(sum(h.values()) for h in dates.values())
        active = len(dates)
        
        result['summary'] = {
            'active_days': active,
            'total_shleps': total,
            'last_active': max(dates.keys()) if active > 0 else None,
            'daily_avg': round(total / active, 1) if active > 0 else 0
        }
        
        return result
    
    def get_global_trends(self):
        """Глобальные тренды"""
        now = datetime.now()
        today = now.date().isoformat()
        yesterday = (now - timedelta(days=1)).date().isoformat()
        
        active_24h = set()
        shleps_24h = 0
        active_today = set()
        
        for uid, dates in self.detailed_stats.items():
            for date_str, hours in dates.items():
                daily = sum(hours.values())
                
                if date_str == today:
                    active_today.add(uid)
                
                if date_str in [today, yesterday]:
                    active_24h.add(uid)
                    shleps_24h += daily
        
        # Шлёпки в текущем часу
        shleps_this_hour = 0
        for dates in self.detailed_stats.values():
            if today in dates:
                shleps_this_hour += dates[today].get(now.hour, 0)
        
        return {
            'active_users_24h': len(active_24h),
            'shleps_24h': shleps_24h,
            'active_today': len(active_today),
            'current_hour': now.hour,
            'shleps_this_hour': shleps_this_hour
        }
    
    def get_comparison_data(self):
        """Данные для сравнения"""
        return {
            'total_users': len(self.user_stats),
            'user_counts': [d['count'] for d in self.user_stats.values()],
            'total_shleps': self.global_stats['total_shleps']
        }
    
    def backup_database(self):
        """Создание резервной копии базы данных"""
        try:
            if not os.path.exists(DATA_FILE):
                return False, "Файл данных не найден"
            
            # Создаем имя файла с timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(BACKUP_DIR, f"mishok_data_backup_{timestamp}.json")
            
            # Копируем файл
            shutil.copy2(DATA_FILE, backup_file)
            
            # Удаляем старые бэкапы (оставляем последние 10)
            backups = []
            for f in os.listdir(BACKUP_DIR):
                if f.startswith("mishok_data_backup_") and f.endswith(".json"):
                    backups.append(f)
            
            backups.sort()
            if len(backups) > 10:
                for f in backups[:-10]:
                    os.remove(os.path.join(BACKUP_DIR, f))
            
            return True, backup_file
            
        except Exception as e:
            return False, str(e)

# Создаем глобальный экземпляр базы данных
db = SimpleDB()

# Экспортируем функции для использования в других модулях
init_db = lambda: None  # Для обратной совместимости
add_shlep = db.add_shlep
get_stats = db.get_stats
get_top_users = db.get_top_users
get_user_stats = db.get_user_stats
get_chat_stats = db.get_chat_stats
get_chat_top_users = db.get_chat_top_users
get_detailed_stats = db.get_detailed_stats
get_global_trends = db.get_global_trends
get_comparison_data = db.get_comparison_data
backup_database = db.backup_database
