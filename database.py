import json
import atexit
import signal
import os
import threading
import time
from datetime import datetime, timedelta

if os.path.exists("/bothost/storage"):
    DATA_DIR = "/bothost/storage"
else:
    DATA_DIR = "."

DATA_FILE = os.path.join(DATA_DIR, "mishok_data.json")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")

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
        
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(BACKUP_DIR, exist_ok=True)
        
        self.load_data()
        atexit.register(self.save_data)
        signal.signal(signal.SIGTERM, self.handle_shutdown)
        signal.signal(signal.SIGINT, self.handle_shutdown)
        
        self.auto_save_thread = threading.Thread(target=self.auto_save_loop, daemon=True)
        self.auto_save_thread.start()
    
    def auto_save_loop(self):
        while True:
            time.sleep(300)
            try:
                self.save_data()
            except:
                pass
    
    def load_data(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.global_stats = data.get('global_stats', self.global_stats)
                    self.user_stats = {int(k): v for k, v in data.get('user_stats', {}).items()}
                    self.chat_stats = {int(k): v for k, v in data.get('chat_stats', {}).items()}
                    self.detailed_stats = {int(k): v for k, v in data.get('detailed_stats', {}).items()}
            except:
                pass
    
    def save_data(self):
        try:
            data = {
                'global_stats': self.global_stats,
                'user_stats': self.user_stats,
                'chat_stats': self.chat_stats,
                'detailed_stats': self.detailed_stats,
                'saved_at': datetime.now().isoformat()
            }
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except:
            pass
    
    def handle_shutdown(self, signum, frame):
        self.save_data()
        exit(0)
    
    def add_shlep(self, user_id, username, damage=0, chat_id=None):
        now = datetime.now()
        date_str = now.date().isoformat()
        hour = now.hour
        
        self.global_stats['total_shleps'] += 1
        self.global_stats['last_shlep'] = now.isoformat()
        
        if damage > self.global_stats['max_damage']:
            self.global_stats['max_damage'] = damage
            self.global_stats['max_damage_user'] = username
            self.global_stats['max_damage_date'] = now.isoformat()
        
        if user_id not in self.user_stats:
            self.user_stats[user_id] = {'username': username, 'count': 0, 'last_shlep': None}
        
        self.user_stats[user_id]['count'] += 1
        self.user_stats[user_id]['last_shlep'] = now.isoformat()
        self.user_stats[user_id]['username'] = username
        
        if user_id not in self.detailed_stats:
            self.detailed_stats[user_id] = {}
        if date_str not in self.detailed_stats[user_id]:
            self.detailed_stats[user_id][date_str] = {}
        if hour not in self.detailed_stats[user_id][date_str]:
            self.detailed_stats[user_id][date_str][hour] = 0
        self.detailed_stats[user_id][date_str][hour] += 1
        
        if chat_id:
            if chat_id not in self.chat_stats:
                self.chat_stats[chat_id] = {
                    'total_shleps': 0, 'max_damage': 0, 'max_damage_user': None, 'users': {}
                }
            self.chat_stats[chat_id]['total_shleps'] += 1
            
            if user_id not in self.chat_stats[chat_id]['users']:
                self.chat_stats[chat_id]['users'][user_id] = {'username': username, 'count': 0}
            self.chat_stats[chat_id]['users'][user_id]['count'] += 1
            
            if damage > self.chat_stats[chat_id]['max_damage']:
                self.chat_stats[chat_id]['max_damage'] = damage
                self.chat_stats[chat_id]['max_damage_user'] = username
        
        return (self.global_stats['total_shleps'], self.user_stats[user_id]['count'], self.global_stats['max_damage'])
    
    def get_stats(self):
        stats = self.global_stats
        last = datetime.fromisoformat(stats['last_shlep']) if stats['last_shlep'] else None
        max_date = datetime.fromisoformat(stats['max_damage_date']) if stats['max_damage_date'] else None
        return (stats['total_shleps'], last, stats['max_damage'], stats['max_damage_user'], max_date)
    
    def get_top_users(self, limit=10):
        users = [(data['username'], data['count']) for data in self.user_stats.values()]
        users.sort(key=lambda x: x[1], reverse=True)
        return users[:limit]
    
    def get_user_stats(self, user_id):
        if user_id in self.user_stats:
            data = self.user_stats[user_id]
            last = datetime.fromisoformat(data['last_shlep']) if data['last_shlep'] else None
            return (data['username'], data['count'], last)
        self.user_stats[user_id] = {'username': f"Игрок_{user_id}", 'count': 0, 'last_shlep': None}
        return (f"Игрок_{user_id}", 0, None)
    
    def get_chat_stats(self, chat_id):
        if chat_id not in self.chat_stats:
            return None
        stats = self.chat_stats[chat_id]
        return {
            'total_shleps': stats['total_shleps'],
            'max_damage': stats['max_damage'],
            'max_damage_user': stats['max_damage_user'],
            'total_users': len(stats['users']),
            'active_today': 0
        }
    
    def get_chat_top_users(self, chat_id, limit=10):
        if chat_id not in self.chat_stats:
            return []
        users = [(data['username'], data['count']) for data in self.chat_stats[chat_id]['users'].values()]
        users.sort(key=lambda x: x[1], reverse=True)
        return users[:limit]
    
    def get_detailed_stats(self, user_id, days=30):
        result = {'daily_activity': {}, 'hourly_distribution': [0]*24, 'summary': {}}
        
        if user_id not in self.detailed_stats:
            return result
        
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days-1)
        
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.isoformat()
            daily_total = 0
            if user_id in self.detailed_stats and date_str in self.detailed_stats[user_id]:
                daily_total = sum(self.detailed_stats[user_id][date_str].values())
            result['daily_activity'][date_str] = daily_total
            current_date += timedelta(days=1)
        
        for date_str, hours in self.detailed_stats.get(user_id, {}).items():
            for hour, count in hours.items():
                if 0 <= hour < 24:
                    result['hourly_distribution'][hour] += count
        
        total_shleps = sum(sum(hours.values()) for hours in self.detailed_stats.get(user_id, {}).values())
        active_days = len(self.detailed_stats.get(user_id, {}))
        result['summary'] = {
            'active_days': active_days,
            'total_shleps': total_shleps,
            'last_active': max(self.detailed_stats.get(user_id, {}).keys()) if active_days > 0 else None,
            'daily_avg': round(total_shleps / active_days, 1) if active_days > 0 else 0
        }
        
        return result
    
    def get_global_trends(self):
        now = datetime.now()
        today = now.date().isoformat()
        yesterday = (now - timedelta(days=1)).date().isoformat()
        
        active_users_24h = set()
        shleps_24h = 0
        active_today = set()
        
        for user_id, dates in self.detailed_stats.items():
            for date_str, hours in dates.items():
                daily_total = sum(hours.values())
                if date_str == today:
                    active_today.add(user_id)
                if date_str in [today, yesterday]:
                    active_users_24h.add(user_id)
                    shleps_24h += daily_total
        
        return {
            'active_users_24h': len(active_users_24h),
            'shleps_24h': shleps_24h,
            'active_today': len(active_today),
            'current_hour': now.hour,
            'shleps_this_hour': sum(
                hours.get(now.hour, 0) 
                for dates in self.detailed_stats.values() 
                for date_str, hours in dates.items() 
                if date_str == today
            )
        }
    
    def get_comparison_data(self):
        return {
            'total_users': len(self.user_stats),
            'user_counts': [data['count'] for data in self.user_stats.values()],
            'total_shleps': self.global_stats['total_shleps']
        }
    
    def backup_database(self):
        try:
            if not os.path.exists(DATA_FILE):
                return False, "Файл данных не найден"
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(BACKUP_DIR, f"mishok_data_{timestamp}.json")
            
            import shutil
            shutil.copy2(DATA_FILE, backup_file)
            
            backup_files = sorted([f for f in os.listdir(BACKUP_DIR) if f.startswith("mishok_data_")])
            if len(backup_files) > 10:
                for old_file in backup_files[:-10]:
                    os.remove(os.path.join(BACKUP_DIR, old_file))
            
            return True, backup_file
        except Exception as e:
            return False, str(e)

db = SimpleDB()

def init_db():
    pass

def add_shlep(user_id, username, damage=0, chat_id=None):
    return db.add_shlep(user_id, username, damage, chat_id)

def get_stats():
    return db.get_stats()

def get_top_users(limit=10):
    return db.get_top_users(limit)

def get_user_stats(user_id):
    return db.get_user_stats(user_id)

def get_chat_stats(chat_id):
    return db.get_chat_stats(chat_id)

def get_chat_top_users(chat_id, limit=10):
    return db.get_chat_top_users(chat_id, limit)

def get_detailed_stats(user_id, days=30):
    return db.get_detailed_stats(user_id, days)

def get_global_trends():
    return db.get_global_trends()

def get_comparison_data():
    return db.get_comparison_data()

def backup_database():
    return db.backup_database()
