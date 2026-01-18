import random
from datetime import datetime, time, timedelta
from database import get_connection
from utils import get_moscow_time

class RecordsSystem:
    """Система рекордов"""
    def __init__(self):
        self.record_types = {
            'strongest_slap': 'Самый мощный шлёпок',
            'longest_combo': 'Самая длинная серия',
            'fastest_slap': 'Рекорд скорости',
            'daily_record': 'Дневной рекорд',
            'weekly_record': 'Недельный рекорд'
        }
    
    def check_strength_record(self, user_id: int, strength: float):
        """Проверить рекорд силы шлёпка"""
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT value, user_id FROM records 
                    WHERE record_type = 'strongest_slap'
                """)
                
                result = cur.fetchone()
                if not result or strength > result[0]:
                    # Новый рекорд!
                    cur.execute("""
                        INSERT INTO records (record_type, user_id, value)
                        VALUES ('strongest_slap', %s, %s)
                        ON CONFLICT (record_type) 
                        DO UPDATE SET user_id = EXCLUDED.user_id, 
                                     value = EXCLUDED.value,
                                     timestamp = NOW()
                    """, (user_id, strength))
                    conn.commit()
                    return True, strength
                
                return False, result[0]
    
    def check_speed_record(self, user_id: int, speed: float):
        """Проверить рекорд скорости (шлёпков в минуту)"""
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT value, user_id FROM records 
                    WHERE record_type = 'fastest_slap'
                """)
                
                result = cur.fetchone()
                if not result or speed > result[0]:
                    cur.execute("""
                        INSERT INTO records (record_type, user_id, value)
                        VALUES ('fastest_slap', %s, %s)
                        ON CONFLICT (record_type) 
                        DO UPDATE SET user_id = EXCLUDED.user_id, 
                                     value = EXCLUDED.value,
                                     timestamp = NOW()
                    """, (user_id, speed))
                    conn.commit()
                    return True, speed
                
                return False, result[0]
    
    def start_combo_session(self, user_id: int):
        """Начать сессию для отслеживания комбо"""
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO shlep_sessions (user_id, start_time, shlep_count)
                    VALUES (%s, NOW(), 0)
                    RETURNING id
                """, (user_id,))
                
                session_id = cur.fetchone()[0]
                conn.commit()
                return session_id
    
    def update_combo_session(self, session_id: int, shlep_count: int):
        """Обновить сессию комбо"""
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE shlep_sessions 
                    SET shlep_count = %s, 
                        end_time = NOW(),
                        avg_speed = %s
                    WHERE id = %s
                """, (shlep_count, shlep_count / 0.1, session_id))  # Предполагаем 0.1 минуты
                
                # Проверяем рекорд комбо
                cur.execute("""
                    SELECT value FROM records 
                    WHERE record_type = 'longest_combo'
                """)
                
                result = cur.fetchone()
                if not result or shlep_count > result[0]:
                    cur.execute("""
                        UPDATE records 
                        SET user_id = (SELECT user_id FROM shlep_sessions WHERE id = %s),
                            value = %s,
                            timestamp = NOW()
                        WHERE record_type = 'longest_combo'
                    """, (session_id, shlep_count))
                
                conn.commit()
    
    def get_all_records(self):
        """Получить все рекорды"""
        with get_connection() as conn:
            with conn.cursor() as cur:
                records = {}
                for record_type in self.record_types.keys():
                    cur.execute("""
                        SELECT r.user_id, r.value, r.timestamp, u.username
                        FROM records r
                        LEFT JOIN user_stats u ON r.user_id = u.user_id
                        WHERE r.record_type = %s
                    """, (record_type,))
                    
                    result = cur.fetchone()
                    if result:
                        records[record_type] = {
                            'user_id': result[0],
                            'value': result[1],
                            'timestamp': result[2],
                            'username': result[3] or f"User {result[0]}",
                            'name': self.record_types[record_type]
                        }
                
                return records

class EventSystem:
    """Система событий"""
    def __init__(self):
        self.events = {
            'happy_hour': {
                'name': 'Счастливый час 🎉',
                'multiplier': 2.0,
                'duration': 60,  # минут
                'description': 'Двойной опыт за все шлёпки!',
                'schedule': [(12, 0), (20, 0)]  # 12:00 и 20:00
            },
            'crazy_minute': {
                'name': 'Безумная минута 🤪',
                'multiplier': 3.0,
                'duration': 1,
                'description': 'Тройной опыт, но только 1 минута!',
                'schedule': [(15, 30)]  # 15:30
            },
            'quiet_hour': {
                'name': 'Тихий час 🤫',
                'multiplier': 0.5,
                'duration': 60,
                'description': 'Половина опыта за шлёпки',
                'schedule': [(3, 0)]  # 3:00 ночи
            }
        }
    
    def check_active_events(self):
        """Проверить активные события"""
        now = get_moscow_time()
        
        with get_connection() as conn:
            with conn.cursor() as cur:
                # Удаляем старые события
                cur.execute("DELETE FROM active_events WHERE end_time < %s", (now,))
                
                # Проверяем расписание
                active_events = []
                for event_id, event_info in self.events.items():
                    for hour, minute in event_info['schedule']:
                        event_time = time(hour, minute)
                        
                        # Если время события в пределах его длительности от текущего времени
                        event_start = datetime.combine(now.date(), event_time)
                        if event_start <= now <= event_start + timedelta(minutes=event_info['duration']):
                            
                            # Добавляем событие в базу
                            cur.execute("""
                                INSERT INTO active_events (event_type, multiplier, start_time, end_time, description)
                                VALUES (%s, %s, %s, %s, %s)
                                ON CONFLICT (event_type) DO NOTHING
                            """, (
                                event_id,
                                event_info['multiplier'],
                                event_start,
                                event_start + timedelta(minutes=event_info['duration']),
                                event_info['description']
                            ))
                            
                            active_events.append({
                                'id': event_id,
                                **event_info,
                                'ends_in': (event_start + timedelta(minutes=event_info['duration']) - now).seconds // 60
                            })
                
                conn.commit()
                return active_events
    
    def get_event_multiplier(self):
        """Получить текущий множитель опыта"""
        active_events = self.check_active_events()
        multiplier = 1.0
        
        for event in active_events:
            multiplier *= event['multiplier']
        
        return multiplier, active_events
    
    def get_upcoming_events(self, hours_ahead: int = 24):
        """Получить предстоящие события"""
        now = get_moscow_time()
        upcoming = []
        
        for event_id, event_info in self.events.items():
            for hour, minute in event_info['schedule']:
                event_time = datetime.combine(now.date(), time(hour, minute))
                
                # Если событие сегодня
                if now <= event_time <= now + timedelta(hours=hours_ahead):
                    upcoming.append({
                        'id': event_id,
                        **event_info,
                        'starts_at': event_time,
                        'starts_in': (event_time - now).seconds // 60 if event_time > now else 0
                    })
        
        return sorted(upcoming, key=lambda x: x['starts_at'])
