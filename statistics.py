from datetime import datetime, timedelta
from collections import defaultdict
import matplotlib.pyplot as plt
import io
import base64
from database import get_connection
from utils import get_moscow_time

class StatisticsSystem:
    def __init__(self):
        pass
    
    def record_shlep(self, user_id: int, timestamp: datetime = None):
        """Записать шлёпок в статистику"""
        if timestamp is None:
            timestamp = get_moscow_time()
        
        with get_connection() as conn:
            with conn.cursor() as cur:
                date = timestamp.date()
                hour = timestamp.hour
                
                cur.execute("""
                    INSERT INTO detailed_stats (user_id, stat_date, hour, shlep_count)
                    VALUES (%s, %s, %s, 1)
                    ON CONFLICT (user_id, stat_date, hour) 
                    DO UPDATE SET shlep_count = detailed_stats.shlep_count + 1
                """, (user_id, date, hour))
                
                conn.commit()
    
    def get_daily_activity(self, user_id: int, days: int = 7):
        """Получить активность за последние дни"""
        end_date = get_moscow_time().date()
        start_date = end_date - timedelta(days=days-1)
        
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT stat_date, SUM(shlep_count) as daily_shleps
                    FROM detailed_stats
                    WHERE user_id = %s AND stat_date BETWEEN %s AND %s
                    GROUP BY stat_date
                    ORDER BY stat_date
                """, (user_id, start_date, end_date))
                
                # Заполняем все дни
                result = {}
                current_date = start_date
                while current_date <= end_date:
                    result[current_date.strftime("%d.%m")] = 0
                    current_date += timedelta(days=1)
                
                # Заполняем реальные данные
                for date_str, count in cur.fetchall():
                    result[date.strftime("%d.%m")] = count
                
                return result
    
    def get_hourly_distribution(self, user_id: int):
        """Распределение по часам"""
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT hour, SUM(shlep_count) as total
                    FROM detailed_stats
                    WHERE user_id = %s
                    GROUP BY hour
                    ORDER BY hour
                """, (user_id,))
                
                distribution = [0] * 24
                for hour, total in cur.fetchall():
                    distribution[hour] = total
                
                return distribution
    
    def generate_activity_chart(self, user_id: int, days: int = 7):
        """Сгенерировать график активности"""
        activity = self.get_daily_activity(user_id, days)
        
        dates = list(activity.keys())
        counts = list(activity.values())
        
        plt.figure(figsize=(10, 5))
        plt.bar(dates, counts, color='skyblue')
        plt.title('Активность по дням', fontsize=14)
        plt.xlabel('Дата', fontsize=12)
        plt.ylabel('Количество шлёпков', fontsize=12)
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Сохраняем в буфер
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        plt.close()
        buf.seek(0)
        
        # Конвертируем в base64
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        buf.close()
        
        return img_base64
    
    def get_favorite_time(self, user_id: int):
        """Любимое время для шлёпков"""
        distribution = self.get_hourly_distribution(user_id)
        
        if not any(distribution):
            return "Пока нет данных"
        
        max_hour = distribution.index(max(distribution))
        total = sum(distribution)
        
        times_of_day = [
            (0, 6, "ночью 🌙"),
            (7, 12, "утром 🌅"),
            (13, 17, "днём ☀️"),
            (18, 23, "вечером 🌆")
        ]
        
        for start, end, description in times_of_day:
            if start <= max_hour <= end:
                time_desc = description
                break
        else:
            time_desc = "в неизвестное время"
        
        return f"Ты чаще всего шлёпаешь {time_desc} ({max_hour}:00)"
    
    def compare_with_friends(self, user_id: int, friend_ids: list):
        """Сравнить с друзьями"""
        with get_connection() as conn:
            with conn.cursor() as cur:
                # Получаем статистику за последнюю неделю
                end_date = get_moscow_time().date()
                start_date = end_date - timedelta(days=7)
                
                placeholders = ', '.join(['%s'] * len(friend_ids))
                query = f"""
                    SELECT 
                        u.user_id,
                        u.username,
                        COALESCE(SUM(s.shlep_count), 0) as weekly_shleps
                    FROM (VALUES {', '.join(['(%s)'] * len(friend_ids))}) AS u(user_id)
                    LEFT JOIN detailed_stats s ON u.user_id = s.user_id 
                        AND s.stat_date BETWEEN %s AND %s
                    LEFT JOIN user_stats us ON u.user_id = us.user_id
                    GROUP BY u.user_id, u.username
                    ORDER BY weekly_shleps DESC
                """
                
                params = friend_ids * 2 + [start_date, end_date]
                cur.execute(query, params)
                
                results = []
                for friend_id, username, weekly_shleps in cur.fetchall():
                    results.append({
                        'user_id': friend_id,
                        'username': username or f"User {friend_id}",
                        'weekly_shleps': weekly_shleps
                    })
                
                return results
