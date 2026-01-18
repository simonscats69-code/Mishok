import math
from datetime import datetime, timedelta
from database import get_connection, add_points
from config import ACHIEVEMENTS

class LevelSystem:
    def __init__(self):
        self.base_xp = 100
        self.xp_multiplier = 1.5
    
    def calculate_xp_for_level(self, level: int) -> int:
        return int(self.base_xp * (self.xp_multiplier ** (level - 1)))
    
    def calculate_level(self, xp: int) -> tuple:
        level = 1
        xp_needed = self.calculate_xp_for_level(level)
        xp_remaining = xp
        
        while xp_remaining >= xp_needed:
            xp_remaining -= xp_needed
            level += 1
            xp_needed = self.calculate_xp_for_level(level)
        
        progress_percent = (xp_remaining / xp_needed) * 100 if xp_needed > 0 else 100
        
        return {
            'level': level,
            'xp': xp,
            'xp_current': xp_remaining,
            'xp_needed': xp_needed,
            'progress': progress_percent,
            'total_xp_needed': self.calculate_total_xp_for_level(level),
            'next_level_in': xp_needed - xp_remaining
        }
    
    def calculate_total_xp_for_level(self, level: int) -> int:
        total = 0
        for lvl in range(1, level):
            total += self.calculate_xp_for_level(lvl)
        return total
    
    def add_xp(self, user_id: int, xp_amount: int, reason: str = "shlep"):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO user_xp (user_id, xp, last_updated)
                    VALUES (%s, %s, NOW())
                    ON CONFLICT (user_id) 
                    DO UPDATE SET 
                        xp = user_xp.xp + EXCLUDED.xp,
                        last_updated = EXCLUDED.last_updated
                    RETURNING xp
                """, (user_id, xp_amount))
                
                new_xp = cur.fetchone()[0]
                
                cur.execute("""
                    INSERT INTO xp_history (user_id, xp_amount, reason, timestamp)
                    VALUES (%s, %s, %s, NOW())
                """, (user_id, xp_amount, reason))
                
                old_level = self.get_user_level(user_id)
                new_level_info = self.calculate_level(new_xp)
                
                if new_level_info['level'] > old_level:
                    level_up_reward = new_level_info['level'] * 50
                    add_points(user_id, level_up_reward)
                    
                    cur.execute("""
                        INSERT INTO level_ups (user_id, level, reward, timestamp)
                        VALUES (%s, %s, %s, NOW())
                    """, (user_id, new_level_info['level'], level_up_reward))
                
                conn.commit()
                return new_level_info
    
    def get_user_level(self, user_id: int) -> int:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT xp FROM user_xp WHERE user_id = %s", (user_id,))
                result = cur.fetchone()
                if result:
                    xp = result[0]
                    level_info = self.calculate_level(xp)
                    return level_info['level']
                return 1
    
    def get_level_progress(self, user_id: int):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT xp FROM user_xp WHERE user_id = %s", (user_id,))
                result = cur.fetchone()
                xp = result[0] if result else 0
                return self.calculate_level(xp)

class MishokLevelSystem:
    def __init__(self):
        self.levels = {
            1: {"name": "Нежный Мишок", "resistance": 0.0, "reactions": "base"},
            10: {"name": "Закалённый Мишок", "resistance": 0.1, "reactions": "annoyed"},
            25: {"name": "Стальной Мишок", "resistance": 0.2, "reactions": "angry"},
            50: {"name": "Несокрушимый Мишок", "resistance": 0.3, "reactions": "epic"},
            100: {"name": "Легендарный Мишок", "resistance": 0.4, "reactions": "legendary"},
        }
    
    def get_mishok_level(self, total_shleps: int):
        current_level = 1
        current_stats = self.levels[1]
        
        for level_threshold, stats in sorted(self.levels.items(), reverse=True):
            if total_shleps >= level_threshold:
                current_level = level_threshold
                current_stats = stats
                break
        
        next_threshold = None
        for threshold in sorted(self.levels.keys()):
            if threshold > current_level:
                next_threshold = threshold
                break
        
        return {
            'level': current_level,
            'name': current_stats['name'],
            'resistance': current_stats['resistance'],
            'reactions': current_stats['reactions'],
            'next_level': next_threshold,
            'needed_for_next': next_threshold - total_shleps if next_threshold else 0
        }

class SkillsSystem:
    def __init__(self):
        self.skills = {
            'accurate_slap': {
                'name': 'Меткий шлёпок',
                'description': 'Увеличивает базовый опыт на 10%',
                'max_level': 10,
                'cost_per_level': [50, 100, 200, 400, 800, 1600, 3200, 6400, 12800, 25600],
                'effect_per_level': [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
            },
            'combo_slap': {
                'name': 'Серия ударов',
                'description': 'Шанс сделать дополнительный шлёпок',
                'max_level': 5,
                'cost_per_level': [100, 250, 500, 1000, 2000],
                'effect_per_level': [0.05, 0.1, 0.15, 0.2, 0.25]
            },
            'critical_slap': {
                'name': 'Критический удар',
                'description': 'Шанс на критический удар (2x XP)',
                'max_level': 5,
                'cost_per_level': [200, 500, 1000, 2000, 5000],
                'effect_per_level': [0.05, 0.1, 0.15, 0.2, 0.25]
            }
        }
    
    def get_user_skills(self, user_id: int):
        with get_connection() as conn:
            with conn.cursor() as cur:
                skills_data = {}
                for skill_id, skill_info in self.skills.items():
                    cur.execute("""
                        SELECT level FROM user_skills 
                        WHERE user_id = %s AND skill_id = %s
                    """, (user_id, skill_id))
                    
                    result = cur.fetchone()
                    level = result[0] if result else 0
                    
                    skills_data[skill_id] = {
                        **skill_info,
                        'current_level': level,
                        'next_cost': skill_info['cost_per_level'][level] if level < skill_info['max_level'] else None,
                        'current_effect': skill_info['effect_per_level'][level-1] if level > 0 else 0,
                        'next_effect': skill_info['effect_per_level'][level] if level < skill_info['max_level'] else skill_info['effect_per_level'][-1]
                    }
                
                return skills_data
    
    def upgrade_skill(self, user_id: int, skill_id: str):
        if skill_id not in self.skills:
            return False, "Навык не найден"
        
        skill_info = self.skills[skill_id]
        
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT us.level, up.points 
                    FROM user_skills us
                    LEFT JOIN user_points up ON us.user_id = up.user_id
                    WHERE us.user_id = %s AND us.skill_id = %s
                """, (user_id, skill_id))
                
                result = cur.fetchone()
                if not result:
                    current_level = 0
                    points = 0
                else:
                    current_level = result[0] or 0
                    points = result[1] or 0
                
                if current_level >= skill_info['max_level']:
                    return False, "Навык уже максимального уровня"
                
                cost = skill_info['cost_per_level'][current_level]
                
                if points < cost:
                    return False, f"Недостаточно очков. Нужно: {cost}"
                
                cur.execute("""
                    UPDATE user_points 
                    SET points = points - %s 
                    WHERE user_id = %s
                """, (cost, user_id))
                
                if current_level == 0:
                    cur.execute("""
                        INSERT INTO user_skills (user_id, skill_id, level)
                        VALUES (%s, %s, 1)
                    """, (user_id, skill_id))
                else:
                    cur.execute("""
                        UPDATE user_skills 
                        SET level = level + 1 
                        WHERE user_id = %s AND skill_id = %s
                    """, (user_id, skill_id))
                
                conn.commit()
                return True, f"Навык улучшен до уровня {current_level + 1}!"
