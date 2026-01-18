from config import ACHIEVEMENTS
from database import get_connection

class AchievementSystem:
    def __init__(self):
        self.achievements = ACHIEVEMENTS
    
    def check_achievements(self, user_id: int, current_count: int):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS user_achievements (
                        user_id BIGINT,
                        achievement_id INT,
                        achieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (user_id, achievement_id)
                    )
                """)
                
                cur.execute("""
                    SELECT achievement_id FROM user_achievements 
                    WHERE user_id = %s
                """, (user_id,))
                achieved = {row[0] for row in cur.fetchall()}
                
                new_achievements = []
                for threshold, achievement in self.achievements.items():
                    if threshold <= current_count and threshold not in achieved:
                        cur.execute("""
                            INSERT INTO user_achievements (user_id, achievement_id)
                            VALUES (%s, %s)
                        """, (user_id, threshold))
                        new_achievements.append(achievement)
                
                conn.commit()
                return new_achievements
    
    def get_user_achievements(self, user_id: int):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT a.achievement_id, a.achieved_at 
                    FROM user_achievements a
                    WHERE user_id = %s
                    ORDER BY a.achievement_id
                """, (user_id,))
                
                achievements = []
                for row in cur.fetchall():
                    threshold = row[0]
                    if threshold in self.achievements:
                        achievement = self.achievements[threshold].copy()
                        achievement['achieved_at'] = row[1]
                        achievements.append(achievement)
                
                return achievements
    
    def get_achievements_progress(self, user_id: int):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COALESCE(shlep_count, 0) 
                    FROM user_stats 
                    WHERE user_id = %s
                """, (user_id,))
                result = cur.fetchone()
                current_count = result[0] if result else 0
                
                cur.execute("""
                    SELECT achievement_id FROM user_achievements 
                    WHERE user_id = %s
                """, (user_id,))
                achieved_ids = {row[0] for row in cur.fetchall()}
                
                progress = []
                for threshold in sorted(self.achievements.keys()):
                    is_achieved = threshold in achieved_ids
                    progress.append({
                        **self.achievements[threshold],
                        'threshold': threshold,
                        'achieved': is_achieved,
                        'current': current_count,
                        'progress_percent': min(100, (current_count / threshold * 100)) if threshold > 0 else 100,
                        'remaining': max(0, threshold - current_count) if not is_achieved else 0
                    })
                
                return progress
    
    def get_next_achievement(self, current_count: int):
        for threshold in sorted(self.achievements.keys()):
            if threshold > current_count:
                return {
                    'threshold': threshold,
                    'remaining': threshold - current_count,
                    **self.achievements[threshold]
                }
        return None
