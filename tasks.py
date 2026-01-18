from datetime import datetime, timedelta
from config import DAILY_TASKS, TASK_REWARDS
from database import get_connection
from utils import get_moscow_time, is_new_day

class TaskSystem:
    def __init__(self):
        self.tasks = DAILY_TASKS
        self.rewards = TASK_REWARDS
    
    def init_user_tasks(self, user_id: int):
        with get_connection() as conn:
            with conn.cursor() as cur:
                today = get_moscow_time().date()
                
                cur.execute("""
                    SELECT COUNT(*) FROM user_daily_tasks
                    WHERE user_id = %s AND task_date = %s
                """, (user_id, today))
                
                if cur.fetchone()[0] == 0:
                    for i, task in enumerate(self.tasks):
                        cur.execute("""
                            INSERT INTO user_daily_tasks (user_id, task_date, task_id, progress)
                            VALUES (%s, %s, %s, 0)
                        """, (user_id, today, i))
                
                conn.commit()
    
    def update_task_progress(self, user_id: int):
        today = get_moscow_time().date()
        updated_tasks = []
        
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT task_id, progress, completed FROM user_daily_tasks
                    WHERE user_id = %s AND task_date = %s
                    ORDER BY task_id
                """, (user_id, today))
                
                tasks_data = cur.fetchall()
                
                for task_id, progress, completed in tasks_data:
                    if not completed:
                        new_progress = progress + 1
                        task = self.tasks[task_id]
                        
                        if new_progress >= task['required']:
                            cur.execute("""
                                UPDATE user_daily_tasks
                                SET progress = %s, completed = TRUE
                                WHERE user_id = %s AND task_date = %s AND task_id = %s
                            """, (new_progress, user_id, today, task_id))
                            updated_tasks.append(task)
                        else:
                            cur.execute("""
                                UPDATE user_daily_tasks
                                SET progress = %s
                                WHERE user_id = %s AND task_date = %s AND task_id = %s
                            """, (new_progress, user_id, today, task_id))
                
                conn.commit()
                return updated_tasks
    
    def get_user_tasks(self, user_id: int):
        today = get_moscow_time().date()
        
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT t.task_id, t.progress, t.completed
                    FROM user_daily_tasks t
                    WHERE t.user_id = %s AND t.task_date = %s
                    ORDER BY t.task_id
                """, (user_id, today))
                
                tasks = []
                for task_id, progress, completed in cur.fetchall():
                    task_info = self.tasks[task_id].copy()
                    task_info['progress'] = progress
                    task_info['completed'] = completed
                    task_info['task_id'] = task_id
                    tasks.append(task_info)
                
                return tasks

class RatingSystem:
    def __init__(self):
        pass
    
    def get_daily_rating(self, date=None):
        if date is None:
            date = get_moscow_time().date()
        
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        u.user_id,
                        u.username,
                        SUM(s.shlep_count) as daily_shleps
                    FROM detailed_stats s
                    JOIN user_stats u ON s.user_id = u.user_id
                    WHERE s.stat_date = %s
                    GROUP BY u.user_id, u.username
                    ORDER BY daily_shleps DESC
                    LIMIT 20
                """, (date,))
                
                return cur.fetchall()
    
    def get_weekly_rating(self):
        week_ago = get_moscow_time().date() - timedelta(days=7)
        
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        u.user_id,
                        u.username,
                        SUM(s.shlep_count) as weekly_shleps
                    FROM detailed_stats s
                    JOIN user_stats u ON s.user_id = u.user_id
                    WHERE s.stat_date >= %s
                    GROUP BY u.user_id, u.username
                    ORDER BY weekly_shleps DESC
                    LIMIT 20
                """, (week_ago,))
                
                return cur.fetchall()
    
    def get_user_daily_position(self, user_id: int):
        daily = self.get_daily_rating()
        for i, (uid, username, count) in enumerate(daily, 1):
            if uid == user_id:
                return i, count
        return None, 0
    
    def get_user_weekly_position(self, user_id: int):
        weekly = self.get_weekly_rating()
        for i, (uid, username, count) in enumerate(weekly, 1):
            if uid == user_id:
                return i, count
        return None, 0
