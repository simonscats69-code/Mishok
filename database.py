import json, os, threading, time, atexit, signal
from datetime import datetime, timedelta
import shutil

DATA_DIR = "/bothost/storage" if os.path.exists("/bothost/storage") else "."
DATA_FILE = os.path.join(DATA_DIR, "mishok_data.json")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")

class SimpleDB:
    def __init__(self):
        self.global_stats = {'total_shleps':0,'last_shlep':None,'max_damage':0,'max_damage_user':None,'max_damage_date':None}
        self.user_stats, self.chat_stats, self.detailed_stats = {}, {}, {}
        os.makedirs(DATA_DIR, exist_ok=True); os.makedirs(BACKUP_DIR, exist_ok=True)
        self.load_data()
        atexit.register(self.save_data)
        signal.signal(signal.SIGTERM, self.handle_shutdown); signal.signal(signal.SIGINT, self.handle_shutdown)
        threading.Thread(target=self.auto_save_loop, daemon=True).start()
    
    def auto_save_loop(self):
        while True:
            time.sleep(300)
            try: self.save_data()
            except: pass
    
    def load_data(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.global_stats = data.get('global_stats', self.global_stats)
                    self.user_stats = {int(k):v for k,v in data.get('user_stats',{}).items()}
                    self.chat_stats = {int(k):v for k,v in data.get('chat_stats',{}).items()}
                    self.detailed_stats = {int(k):v for k,v in data.get('detailed_stats',{}).items()}
            except: pass
    
    def save_data(self):
        try:
            data = {'global_stats':self.global_stats,'user_stats':self.user_stats,'chat_stats':self.chat_stats,'detailed_stats':self.detailed_stats,'saved_at':datetime.now().isoformat()}
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except: pass
    
    def handle_shutdown(self, signum, frame):
        self.save_data(); exit(0)
    
    def add_shlep(self, user_id, username, damage=0, chat_id=None):
        now = datetime.now(); date_str = now.date().isoformat(); hour = now.hour
        self.global_stats['total_shleps'] += 1; self.global_stats['last_shlep'] = now.isoformat()
        if damage > self.global_stats['max_damage']:
            self.global_stats['max_damage'] = damage; self.global_stats['max_damage_user'] = username; self.global_stats['max_damage_date'] = now.isoformat()
        if user_id not in self.user_stats: self.user_stats[user_id] = {'username':username,'count':0,'last_shlep':None}
        self.user_stats[user_id]['count'] += 1; self.user_stats[user_id]['last_shlep'] = now.isoformat(); self.user_stats[user_id]['username'] = username
        if user_id not in self.detailed_stats: self.detailed_stats[user_id] = {}
        if date_str not in self.detailed_stats[user_id]: self.detailed_stats[user_id][date_str] = {}
        if hour not in self.detailed_stats[user_id][date_str]: self.detailed_stats[user_id][date_str][hour] = 0
        self.detailed_stats[user_id][date_str][hour] += 1
        if chat_id:
            if chat_id not in self.chat_stats: self.chat_stats[chat_id] = {'total_shleps':0,'max_damage':0,'max_damage_user':None,'users':{}}
            self.chat_stats[chat_id]['total_shleps'] += 1
            if user_id not in self.chat_stats[chat_id]['users']: self.chat_stats[chat_id]['users'][user_id] = {'username':username,'count':0}
            self.chat_stats[chat_id]['users'][user_id]['count'] += 1
            if damage > self.chat_stats[chat_id]['max_damage']: self.chat_stats[chat_id]['max_damage'] = damage; self.chat_stats[chat_id]['max_damage_user'] = username
        return (self.global_stats['total_shleps'], self.user_stats[user_id]['count'], self.global_stats['max_damage'])
    
    def get_stats(self):
        s = self.global_stats
        last = datetime.fromisoformat(s['last_shlep']) if s['last_shlep'] else None
        maxd = datetime.fromisoformat(s['max_damage_date']) if s['max_damage_date'] else None
        return (s['total_shleps'], last, s['max_damage'], s['max_damage_user'], maxd)
    
    def get_top_users(self, limit=10):
        users = [(d['username'], d['count']) for d in self.user_stats.values()]
        users.sort(key=lambda x: x[1], reverse=True); return users[:limit]
    
    def get_user_stats(self, user_id):
        if user_id in self.user_stats:
            d = self.user_stats[user_id]; last = datetime.fromisoformat(d['last_shlep']) if d['last_shlep'] else None
            return (d['username'], d['count'], last)
        self.user_stats[user_id] = {'username':f"Игрок_{user_id}",'count':0,'last_shlep':None}
        return (f"Игрок_{user_id}", 0, None)
    
    def get_chat_stats(self, chat_id):
        if chat_id not in self.chat_stats: return None
        s = self.chat_stats[chat_id]; return {'total_shleps':s['total_shleps'],'max_damage':s['max_damage'],'max_damage_user':s['max_damage_user'],'total_users':len(s['users']),'active_today':0}
    
    def get_chat_top_users(self, chat_id, limit=10):
        if chat_id not in self.chat_stats: return []
        users = [(d['username'], d['count']) for d in self.chat_stats[chat_id]['users'].values()]
        users.sort(key=lambda x: x[1], reverse=True); return users[:limit]
    
    def get_detailed_stats(self, user_id, days=30):
        result = {'daily_activity':{},'hourly_distribution':[0]*24,'summary':{}}
        if user_id not in self.detailed_stats: return result
        end, start = datetime.now().date(), datetime.now().date() - timedelta(days=days-1)
        cur = start; dates = self.detailed_stats[user_id]
        while cur <= end:
            date_str = cur.isoformat(); daily = sum(dates.get(date_str,{}).values()) if date_str in dates else 0
            result['daily_activity'][date_str] = daily; cur += timedelta(days=1)
        for date_str, hours in dates.items():
            for h, c in hours.items():
                if 0 <= h < 24: result['hourly_distribution'][h] += c
        total = sum(sum(h.values()) for h in dates.values()); active = len(dates)
        result['summary'] = {'active_days':active,'total_shleps':total,'last_active':max(dates.keys()) if active>0 else None,'daily_avg':round(total/active,1) if active>0 else 0}
        return result
    
    def get_global_trends(self):
        now = datetime.now(); today = now.date().isoformat(); yesterday = (now-timedelta(days=1)).date().isoformat()
        active_24h, shleps_24h, active_today = set(), 0, set()
        for uid, dates in self.detailed_stats.items():
            for date_str, hours in dates.items():
                daily = sum(hours.values())
                if date_str == today: active_today.add(uid)
                if date_str in [today, yesterday]: active_24h.add(uid); shleps_24h += daily
        return {'active_users_24h':len(active_24h),'shleps_24h':shleps_24h,'active_today':len(active_today),'current_hour':now.hour,'shleps_this_hour':sum(hours.get(now.hour,0) for dates in self.detailed_stats.values() for d,hours in dates.items() if d==today)}
    
    def get_comparison_data(self):
        return {'total_users':len(self.user_stats),'user_counts':[d['count'] for d in self.user_stats.values()],'total_shleps':self.global_stats['total_shleps']}
    
    def backup_database(self):
        try:
            if not os.path.exists(DATA_FILE): return False, "Нет файла"
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup = os.path.join(BACKUP_DIR, f"mishok_data_{ts}.json")
            shutil.copy2(DATA_FILE, backup)
            backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.startswith("mishok_data_")])
            if len(backups) > 10:
                for f in backups[:-10]: os.remove(os.path.join(BACKUP_DIR, f))
            return True, backup
        except Exception as e: return False, str(e)

db = SimpleDB()
init_db = lambda: None
add_shlep = db.add_shlep; get_stats = db.get_stats; get_top_users = db.get_top_users; get_user_stats = db.get_user_stats
get_chat_stats = db.get_chat_stats; get_chat_top_users = db.get_chat_top_users; get_detailed_stats = db.get_detailed_stats
get_global_trends = db.get_global_trends; get_comparison_data = db.get_comparison_data; backup_database = db.backup_database
