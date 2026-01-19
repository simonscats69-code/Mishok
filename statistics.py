import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from database import load_data

logger = logging.getLogger(__name__)

def get_favorite_time(user_id: int) -> str:
    try:
        data = load_data()
        user_data = data["users"].get(str(user_id))
        
        if not user_data or "damage_history" not in user_data:
            return "⏰ *Любимое время:* данных недостаточно"
        
        hour_counts = {}
        for record in user_data["damage_history"]:
            try:
                record_time = datetime.fromisoformat(record["timestamp"])
                hour = record_time.hour
                hour_counts[hour] = hour_counts.get(hour, 0) + 1
            except:
                continue
        
        if not hour_counts:
            return "⏰ *Любимое время:* данных недостаточно"
        
        favorite_hour = max(hour_counts.items(), key=lambda x: x[1])[0]
        
        if 5 <= favorite_hour < 12:
            time_of_day = "утро"
            emoji = "🌅"
        elif 12 <= favorite_hour < 17:
            time_of_day = "день"
            emoji = "☀️"
        elif 17 <= favorite_hour < 22:
            time_of_day = "вечер"
            emoji = "🌆"
        else:
            time_of_day = "ночь"
            emoji = "🌙"
        
        hour_str = f"{favorite_hour:02d}:00"
        
        return f"⏰ *Любимое время:* {hour_str} ({time_of_day} {emoji})"
    
    except Exception as e:
        logger.error(f"Ошибка получения любимого времени: {e}")
        return "⏰ *Любимое время:* ошибка расчета"

def get_comparison_stats(user_id: int) -> Dict[str, Any]:
    try:
        data = load_data()
        all_users = data.get("users", {})
        
        if not all_users:
            return {
                "total_users": 0,
                "avg_shleps": 0,
                "rank": 1,
                "percentile": 100
            }
        
        user_data = all_users.get(str(user_id))
        user_shleps = user_data.get("total_shleps", 0) if user_data else 0
        
        all_shleps = []
        for uid, udata in all_users.items():
            if "total_shleps" in udata:
                all_shleps.append(udata["total_shleps"])
        
        if not all_shleps:
            return {
                "total_users": len(all_users),
                "avg_shleps": 0,
                "rank": 1,
                "percentile": 100
            }
        
        total_users = len(all_shleps)
        avg_shleps = sum(all_shleps) / total_users
        
        sorted_shleps = sorted(all_shleps, reverse=True)
        
        try:
            rank = sorted_shleps.index(user_shleps) + 1
        except ValueError:
            rank = total_users + 1
        
        if total_users > 1:
            behind = total_users - rank
            percentile = (behind / (total_users - 1)) * 100
        else:
            percentile = 100
        
        return {
            "total_users": total_users,
            "avg_shleps": round(avg_shleps, 1),
            "rank": rank,
            "percentile": round(percentile, 1)
        }
    
    except Exception as e:
        logger.error(f"Ошибка сравнения статистики: {e}")
        return {
            "total_users": 0,
            "avg_shleps": 0,
            "rank": 1,
            "percentile": 100
        }
