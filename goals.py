from datetime import datetime, timedelta
from database import get_connection, add_points
from utils import get_moscow_time

class GlobalGoalsSystem:
    def __init__(self):
        self.active_goals = []
        self.init_default_goals()
    
    def init_default_goals(self):
        self.active_goals = [
            {
                'id': 1,
                'name': 'Миллионный шлёпок 🎯',
                'target': 1000000,
                'current': 0,
                'reward': {'type': 'points', 'value': 10000},
                'description': 'Сообщество должно достичь 1,000,000 шлёпков!'
            },
            {
                'id': 2,
                'name': 'Неделя активности 📈',
                'target': 50000,
                'current': 0,
                'reward': {'type': 'multiplier', 'value': 1.5, 'duration': 24},
                'description': '50,000 шлёпков за неделю',
                'start_date': get_moscow_time().date(),
                'end_date': get_moscow_time().date() + timedelta(days=7)
            },
            {
                'id': 3,
                'name': 'Шлёпок в каждый час ⏰',
                'target': 24,
                'current': 0,
                'reward': {'type': 'achievement', 'value': 'hour_master'},
                'description': 'Кто-то должен шлёпнуть в каждый час суток'
            }
        ]
        
        self.load_from_db()
    
    def load_from_db(self):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM global_goals WHERE is_active = TRUE")
                
                for row in cur.fetchall():
                    goal_id, name, target, current, reward_type, reward_value, is_active, start_date, end_date = row
                    
                    self.active_goals.append({
                        'id': goal_id,
                        'name': name,
                        'target': target,
                        'current': current,
                        'reward': {'type': reward_type, 'value': reward_value},
                        'description': f"Глобальная цель: {name}",
                        'start_date': start_date,
                        'end_date': end_date
                    })
    
    def update_goal_progress(self, goal_id: int, increment: int = 1):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE global_goals 
                    SET current_value = current_value + %s
                    WHERE id = %s AND is_active = TRUE
                    RETURNING current_value, target_value, reward_type, reward_value
                """, (increment, goal_id))
                
                result = cur.fetchone()
                if result:
                    current, target, reward_type, reward_value = result
                    
                    if current >= target:
                        self.complete_goal(goal_id, reward_type, reward_value)
                    
                    conn.commit()
                    return current, target
    
    def complete_goal(self, goal_id: int, reward_type: str, reward_value):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE global_goals SET is_active = FALSE WHERE id = %s", (goal_id,))
                
                if reward_type == 'points':
                    cur.execute("""
                        UPDATE user_points 
                        SET points = points + %s 
                        WHERE points > 0
                    """, (reward_value,))
                
                cur.execute("""
                    INSERT INTO goal_completions (goal_id, completed_at, reward_type, reward_value)
                    VALUES (%s, NOW(), %s, %s)
                """, (goal_id, reward_type, reward_value))
                
                conn.commit()
    
    def get_community_contributions(self, user_id: int):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT g.id, g.goal_name, g.current_value, g.target_value,
                           COUNT(DISTINCT s.user_id) as contributors,
                           COALESCE(SUM(CASE WHEN s.user_id = %s THEN 1 ELSE 0 END), 0) as user_contributions
                    FROM global_goals g
                    LEFT JOIN detailed_stats s ON g.id = 1
                    WHERE g.is_active = TRUE
                    GROUP BY g.id, g.goal_name, g.current_value, g.target_value
                """, (user_id,))
                
                contributions = []
                for goal_id, name, current, target, contributors, user_contribution in cur.fetchall():
                    contributions.append({
                        'goal_id': goal_id,
                        'name': name,
                        'progress': (current / target * 100) if target > 0 else 0,
                        'current': current,
                        'target': target,
                        'contributors': contributors,
                        'user_contribution': user_contribution,
                        'user_percentage': (user_contribution / current * 100) if current > 0 else 0
                    })
                
                return contributions
    
    def get_global_stats(self):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT total_shleps FROM global_stats WHERE id = 1")
                total_shleps = cur.fetchone()[0] or 0
                
                cur.execute("""
                    SELECT COUNT(DISTINCT user_id) 
                    FROM detailed_stats 
                    WHERE stat_date = CURRENT_DATE
                """)
                active_today = cur.fetchone()[0] or 0
                
                cur.execute("""
                    SELECT SUM(shlep_count) 
                    FROM detailed_stats 
                    WHERE stat_date = CURRENT_DATE
                """)
                today_shleps = cur.fetchone()[0] or 0
                
                cur.execute("""
                    SELECT MAX(daily_total) 
                    FROM (
                        SELECT SUM(shlep_count) as daily_total
                        FROM detailed_stats
                        GROUP BY stat_date
                    ) daily_stats
                """)
                daily_record = cur.fetchone()[0] or 0
                
                return {
                    'total_shleps': total_shleps,
                    'active_today': active_today,
                    'today_shleps': today_shleps,
                    'daily_record': daily_record,
                    'average_per_user': total_shleps / max(active_today, 1)
                }
