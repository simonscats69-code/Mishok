from datetime import datetime, timedelta
from database import get_connection
from utils import get_moscow_time

class StatisticsSystem:
    def __init__(self):
        pass
    
    def record_shlep(self, user_id: int, timestamp: datetime = None):
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
                
                result = {}
                current_date = start_date
                while current_date <= end_date:
                    result[current_date.strftime("%d.%m")] = 0
                    current_date += timedelta(days=1)
                
                for date, count in cur.fetchall():
                    result[date.strftime("%d.%m")] = count
                
                return result
    
    def get_hourly_distribution(self, user_id: int, days: int = 30):
        end_date = get_moscow_time().date()
        start_date = end_date - timedelta(days=days-1)
        
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT hour, SUM(shlep_count) as total
                    FROM detailed_stats
                    WHERE user_id = %s AND stat_date BETWEEN %s AND %s
                    GROUP BY hour
                    ORDER BY hour
                """, (user_id, start_date, end_date))
                
                distribution = [0] * 24
                for hour, total in cur.fetchall():
                    distribution[hour] = total
                
                return distribution
    
    def get_favorite_time(self, user_id: int):
        distribution = self.get_hourly_distribution(user_id, 30)
        
        if not any(distribution):
            return "Пока нет данных о твоей активности"
        
        max_hour = distribution.index(max(distribution))
        max_count = max(distribution)
        
        times_of_day = [
            (0, 5, "ночью 🌙", "с 0:00 до 6:00"),
            (6, 11, "утром 🌅", "с 6:00 до 12:00"),
            (12, 17, "днём ☀️", "с 12:00 до 18:00"),
            (18, 23, "вечером 🌆", "с 18:00 до 24:00")
        ]
        
        time_desc = ""
        time_range = ""
        for start, end, description, range_text in times_of_day:
            if start <= max_hour <= end:
                time_desc = description
                time_range = range_text
                break
        
        hour_formatted = f"{max_hour}:00"
        return f"Чаще всего шлёпаешь {time_desc} ({hour_formatted})\nВсего шлёпков в это время: {max_count}"
    
    def get_activity_summary(self, user_id: int):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        COUNT(DISTINCT stat_date) as active_days,
                        SUM(shlep_count) as total_shleps,
                        MAX(stat_date) as last_active,
                        AVG(shlep_count) as daily_avg
                    FROM detailed_stats
                    WHERE user_id = %s
                """, (user_id,))
                
                result = cur.fetchone()
                if not result or result[0] is None:
                    return {
                        'active_days': 0,
                        'total_shleps': 0,
                        'last_active': None,
                        'daily_avg': 0
                    }
                
                active_days, total_shleps, last_active, daily_avg = result
                
                cur.execute("""
                    SELECT stat_date, SUM(shlep_count) as daily_total
                    FROM detailed_stats
                    WHERE user_id = %s
                    GROUP BY stat_date
                    ORDER BY daily_total DESC
                    LIMIT 1
                """, (user_id,))
                
                best_day_result = cur.fetchone()
                best_day = best_day_result[0] if best_day_result else None
                best_day_count = best_day_result[1] if best_day_result else 0
                
                return {
                    'active_days': active_days or 0,
                    'total_shleps': total_shleps or 0,
                    'last_active': last_active,
                    'daily_avg': round(daily_avg or 0, 1),
                    'best_day': best_day,
                    'best_day_count': best_day_count or 0
                }
    
    def get_comparison_stats(self, user_id: int):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        COUNT(DISTINCT user_id) as total_users,
                        AVG(total_shleps) as avg_shleps_per_user,
                        PERCENT_RANK() OVER (ORDER BY shlep_count) as user_percentile
                    FROM user_stats us
                    CROSS JOIN (
                        SELECT AVG(shlep_count) as avg_shleps FROM user_stats
                    ) avg_stats
                    WHERE us.user_id = %s
                """, (user_id,))
                
                result = cur.fetchone()
                if not result:
                    return {
                        'total_users': 0,
                        'avg_shleps': 0,
                        'percentile': 0
                    }
                
                total_users, avg_shleps, percentile = result
                
                cur.execute("""
                    SELECT COUNT(*) as user_rank
                    FROM user_stats
                    WHERE shlep_count > (
                        SELECT shlep_count FROM user_stats WHERE user_id = %s
                    )
                """, (user_id,))
                
                rank_result = cur.fetchone()
                rank = rank_result[0] + 1 if rank_result else 1
                
                return {
                    'total_users': total_users or 0,
                    'avg_shleps': round(avg_shleps or 0, 1),
                    'percentile': round((percentile or 0) * 100, 1),
                    'rank': rank
                }
    
    def get_global_trends(self):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        COUNT(DISTINCT user_id) as active_users_24h,
                        SUM(shlep_count) as shleps_24h,
                        COUNT(DISTINCT CASE WHEN stat_date = CURRENT_DATE THEN user_id END) as active_today
                    FROM detailed_stats
                    WHERE stat_date >= CURRENT_DATE - INTERVAL '1 day'
                """)
                
                result = cur.fetchone()
                active_24h, shleps_24h, active_today = result
                
                cur.execute("""
                    SELECT 
                        EXTRACT(HOUR FROM NOW()) as current_hour,
                        COALESCE(SUM(shlep_count), 0) as shleps_this_hour
                    FROM detailed_stats
                    WHERE stat_date = CURRENT_DATE 
                    AND hour = EXTRACT(HOUR FROM NOW())
                """)
                
                hour_result = cur.fetchone()
                current_hour = int(hour_result[0]) if hour_result[0] else 0
                shleps_this_hour = hour_result[1] if hour_result[1] else 0
                
                return {
                    'active_users_24h': active_24h or 0,
                    'shleps_24h': shleps_24h or 0,
                    'active_today': active_today or 0,
                    'current_hour': current_hour,
                    'shleps_this_hour': shleps_this_hour
                }
