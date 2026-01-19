import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from database import load_data
from utils import format_number

logger = logging.getLogger(__name__)

def get_favorite_time(user_id: int) -> str:
    """Возвращает любимое время пользователя для шлёпков"""
    try:
        data = load_data()
        user_data = data["users"].get(str(user_id))
        
        if not user_data or "damage_history" not in user_data:
            return "⏰ *Любимое время:* данных недостаточно"
        
        # Анализируем время шлёпков
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
        
        # Находим самое популярное время
        favorite_hour = max(hour_counts.items(), key=lambda x: x[1])[0]
        
        # Форматируем время
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
    """Сравнивает пользователя с другими"""
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
        
        # Статистика текущего пользователя
        user_data = all_users.get(str(user_id))
        user_shleps = user_data.get("total_shleps", 0) if user_data else 0
        
        # Собираем статистику всех пользователей
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
        
        # Рассчитываем статистику
        total_users = len(all_shleps)
        avg_shleps = sum(all_shleps) / total_users
        
        # Определяем ранг
        sorted_shleps = sorted(all_shleps, reverse=True)
        
        try:
            rank = sorted_shleps.index(user_shleps) + 1
        except ValueError:
            rank = total_users + 1
        
        # Процентиль (сколько пользователей позади)
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

def get_global_trends_info() -> Dict[str, Any]:
    """Возвращает информацию о глобальных трендах"""
    try:
        data = load_data()
        
        if "timestamps" not in data:
            return {}
        
        timestamps = data["timestamps"]
        now = datetime.now()
        
        # За последние 24 часа
        last_24h = []
        active_users_24h = set()
        
        for i in range(24):
            hour_key = (now - timedelta(hours=i)).strftime("%Y-%m-%d %H:00")
            if hour_key in timestamps:
                last_24h.append(timestamps[hour_key]["count"])
                active_users_24h.update(timestamps[hour_key]["users"])
        
        shleps_24h = sum(last_24h)
        
        # Сегодня
        today_key = now.strftime("%Y-%m-%d")
        active_today = len(timestamps.get(today_key, {}).get("users", set())) if today_key in timestamps else 0
        
        # Текущий час
        current_hour_key = now.strftime("%Y-%m-%d %H:00")
        shleps_this_hour = timestamps.get(current_hour_key, {}).get("count", 0) if current_hour_key in timestamps else 0
        
        # Среднее на пользователя
        avg_per_user_24h = shleps_24h / len(active_users_24h) if active_users_24h else 0
        
        return {
            "active_users_24h": len(active_users_24h),
            "shleps_24h": shleps_24h,
            "avg_per_user_24h": round(avg_per_user_24h, 1),
            "active_today": active_today,
            "current_hour": now.hour,
            "shleps_this_hour": shleps_this_hour
        }
    
    except Exception as e:
        logger.error(f"Ошибка получения трендов: {e}")
        return {}

def format_daily_activity_chart(user_id: int, days: int = 7) -> str:
    """Форматирует график ежедневной активности"""
    try:
        from database import get_user_activity
        
        activity = get_user_activity(user_id, days)
        
        if not activity or "daily" not in activity:
            return "📅 *Активность:* данных нет"
        
        daily_data = activity["daily"]
        
        if not daily_data:
            return "📅 *Активность:* данных нет"
        
        # Находим максимум для масштабирования
        max_count = max([day["count"] for day in daily_data] + [1])
        
        chart_lines = []
        for day in daily_data[-7:]:  # Последние 7 дней
            date_parts = day["date"].split("-")
            date_label = f"{date_parts[2]}.{date_parts[1]}"
            
            # Простой ASCII график
            bar_length = int((day["count"] / max_count) * 10)
            bar = "█" * bar_length + "░" * (10 - bar_length)
            
            count_str = str(day["count"]).rjust(3)
            chart_lines.append(f"{date_label}: {bar} {count_str}")
        
        return "📅 *Активность за неделю:*\n" + "\n".join(chart_lines)
    
    except Exception as e:
        logger.error(f"Ошибка форматирования графика: {e}")
        return "📅 *Активность:* ошибка отображения"

def format_hourly_distribution_chart(user_id: int) -> str:
    """Форматирует график распределения по часам"""
    try:
        from database import get_user_activity
        
        activity = get_user_activity(user_id, 30)  # За 30 дней
        
        if not activity or "hourly" not in activity:
            return "⏰ *По часам:* данных нет"
        
        hourly_data = activity["hourly"]
        
        if not hourly_data:
            return "⏰ *По часам:* данных нет"
        
        # Группируем по времени суток
        time_blocks = {
            "🌙 Ночь (00-05)": 0,
            "🌅 Утро (06-11)": 0,
            "☀️ День (12-17)": 0,
            "🌆 Вечер (18-23)": 0
        }
        
        for hour_str, count in hourly_data.items():
            hour = int(hour_str.split(":")[0])
            
            if 0 <= hour <= 5:
                time_blocks["🌙 Ночь (00-05)"] += count
            elif 6 <= hour <= 11:
                time_blocks["🌅 Утро (06-11)"] += count
            elif 12 <= hour <= 17:
                time_blocks["☀️ День (12-17)"] += count
            elif 18 <= hour <= 23:
                time_blocks["🌆 Вечер (18-23)"] += count
        
        # Находим максимум для масштабирования
        max_count = max(time_blocks.values()) or 1
        
        chart_lines = []
        for label, count in time_blocks.items():
            percentage = (count / max_count) * 100
            bar_length = int(percentage / 10)  # 0-10 символов
            
            bar = "█" * bar_length + "░" * (10 - bar_length)
            count_str = str(count).rjust(3)
            
            chart_lines.append(f"{label}: {bar} {count_str}")
        
        return "⏰ *Распределение по времени суток:*\n" + "\n".join(chart_lines)
    
    except Exception as e:
        logger.error(f"Ошибка форматирования часового графика: {e}")
        return "⏰ *По часам:* ошибка отображения"

def get_streak_info(user_id: int) -> Dict[str, Any]:
    """Возвращает информацию о сериях (стриках)"""
    try:
        data = load_data()
        user_data = data["users"].get(str(user_id))
        
        if not user_data or "damage_history" not in user_data:
            return {"current_streak": 0, "max_streak": 0, "last_activity": None}
        
        # Сортируем историю по времени
        history = sorted(
            user_data["damage_history"],
            key=lambda x: datetime.fromisoformat(x["timestamp"]),
            reverse=True
        )
        
        if not history:
            return {"current_streak": 0, "max_streak": 0, "last_activity": None}
        
        # Анализируем стрики
        current_streak = 0
        max_streak = 0
        last_date = None
        
        # Получаем все уникальные даты
        dates_set = set()
        for record in history:
            try:
                record_date = datetime.fromisoformat(record["timestamp"]).date()
                dates_set.add(record_date)
            except:
                continue
        
        if not dates_set:
            return {"current_streak": 0, "max_streak": 0, "last_activity": None}
        
        # Сортируем даты
        dates = sorted(dates_set, reverse=True)
        
        # Текущий стрик (последовательные дни)
        today = datetime.now().date()
        streak_days = 0
        
        for i, date in enumerate(dates):
            if i == 0:
                # Проверяем, был ли сегодня
                if date == today:
                    streak_days = 1
                else:
                    # Проверяем, был ли вчера
                    yesterday = today - timedelta(days=1)
                    if date == yesterday:
                        streak_days = 1
                    else:
                        break
            else:
                # Проверяем последовательность дней
                prev_date = dates[i-1]
                expected_date = prev_date - timedelta(days=1)
                
                if date == expected_date:
                    streak_days += 1
                else:
                    break
        
        current_streak = streak_days
        
        # Максимальный стрик (по всем данным)
        all_dates = sorted(dates_set)
        max_consecutive = 0
        current_consecutive = 1 if all_dates else 0
        
        for i in range(1, len(all_dates)):
            prev_date = all_dates[i-1]
            current_date = all_dates[i]
            
            if (current_date - prev_date).days == 1:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 1
        
        max_streak = max(max_consecutive, current_consecutive, 1) if all_dates else 0
        
        return {
            "current_streak": current_streak,
            "max_streak": max_streak,
            "last_activity": dates[0] if dates else None
        }
    
    except Exception as e:
        logger.error(f"Ошибка получения информации о стриках: {e}")
        return {"current_streak": 0, "max_streak": 0, "last_activity": None}

def get_achievements(user_id: int) -> List[Dict[str, Any]]:
    """Возвращает достижения пользователя"""
    try:
        data = load_data()
        user_data = data["users"].get(str(user_id))
        
        if not user_data:
            return []
        
        total_shleps = user_data.get("total_shleps", 0)
        max_damage = user_data.get("max_damage", 0)
        
        achievements = []
        
        # Достижения по количеству шлёпков
        if total_shleps >= 1:
            achievements.append({
                "title": "🎯 Первый шлёпок",
                "description": "Сделал первый шлёпок по Мишку",
                "unlocked": True
            })
        
        if total_shleps >= 10:
            achievements.append({
                "title": "🔥 Десяточка",
                "description": "Сделал 10 шлёпков",
                "unlocked": True
            })
        
        if total_shleps >= 50:
            achievements.append({
                "title": "💪 Полтинник",
                "description": "Сделал 50 шлёпков",
                "unlocked": True
            })
        
        if total_shleps >= 100:
            achievements.append({
                "title": "🏆 Сотня",
                "description": "Сделал 100 шлёпков",
                "unlocked": True
            })
        
        # Достижения по урону
        if max_damage >= 30:
            achievements.append({
                "title": "💥 Силач",
                "description": "Нанес урон 30+ единиц",
                "unlocked": True
            })
        
        if max_damage >= 50:
            achievements.append({
                "title": "⚡ Разряд",
                "description": "Нанес урон 50+ единиц",
                "unlocked": True
            })
        
        if max_damage >= 80:
            achievements.append({
                "title": "💎 Бриллиантовая рука",
                "description": "Нанес урон 80+ единиц",
                "unlocked": True
            })
        
        # Специальные достижения
        streak_info = get_streak_info(user_id)
        if streak_info["current_streak"] >= 3:
            achievements.append({
                "title": "📅 Серийный шлёпатель",
                "description": "Шлёпает 3 дня подряд",
                "unlocked": True
            })
        
        if streak_info["max_streak"] >= 7:
            achievements.append({
                "title": "⭐ Неделя шлёпков",
                "description": "Шлёпал 7 дней подряд",
                "unlocked": True
            })
        
        return achievements
    
    except Exception as e:
        logger.error(f"Ошибка получения достижений: {e}")
        return []
