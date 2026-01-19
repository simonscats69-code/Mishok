from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple
from database import get_detailed_stats, get_global_trends, get_comparison_data

def get_moscow_time() -> datetime:
    """Московское время (упрощённо)"""
    return datetime.now()

class StatisticsSystem:
    def __init__(self):
        pass
    
    def get_daily_activity(self, user_id: int, days: int = 7) -> Dict[str, int]:
        stats = get_detailed_stats(user_id, days)
        daily = stats.get('daily_activity', {})
        
        result = {}
        for date_str, count in daily.items():
            try:
                date_obj = datetime.fromisoformat(date_str)
                result[date_obj.strftime("%d.%m")] = count
            except:
                result[date_str] = count
        
        # Заполняем пропущенные дни нулями
        end_date = get_moscow_time().date()
        start_date = end_date - timedelta(days=days-1)
        
        current_date = start_date
        while current_date <= end_date:
            key = current_date.strftime("%d.%m")
            if key not in result:
                result[key] = 0
            current_date += timedelta(days=1)
        
        # Сортируем по дате
        sorted_items = sorted(
            result.items(),
            key=lambda x: datetime.strptime(x[0], "%d.%m").date()
        )
        return dict(sorted_items)
    
    def get_hourly_distribution(self, user_id: int, days: int = 30) -> List[int]:
        stats = get_detailed_stats(user_id, days)
        return stats.get('hourly_distribution', [0]*24)
    
    def get_favorite_time(self, user_id: int) -> str:
        hours = self.get_hourly_distribution(user_id, 30)
        
        if not any(hours):
            return "📊 Пока нет данных о твоей активности"
        
        max_hour = hours.index(max(hours))
        max_count = max(hours)
        
        # Распределение по времени суток
        time_blocks = [
            (0, 5, "🌙 Ночью (0-6)", sum(hours[0:6])),
            (6, 11, "🌅 Утром (6-12)", sum(hours[6:12])),
            (12, 17, "☀️ Днём (12-18)", sum(hours[12:18])),
            (18, 23, "🌆 Вечером (18-24)", sum(hours[18:24]))
        ]
        
        best_block = max(time_blocks, key=lambda x: x[3])
        
        if 0 <= max_hour < 6:
            time_desc = "ночью 🌙"
        elif 6 <= max_hour < 12:
            time_desc = "утром 🌅"
        elif 12 <= max_hour < 18:
            time_desc = "днём ☀️"
        else:
            time_desc = "вечером 🌆"
        
        return (
            f"⏰ *Любимое время:* {time_desc} ({max_hour:02d}:00)\n"
            f"📊 *Шлёпков в этот час:* {max_count}\n"
            f"🎯 *Самое активное время суток:* {best_block[2]}\n"
            f"📈 *Всего шлёпков {best_block[2].split()[0].lower()}:* {best_block[3]}"
        )
    
    def get_activity_summary(self, user_id: int) -> Dict[str, Any]:
        stats = get_detailed_stats(user_id, 365)
        summary = stats.get('summary', {})
        
        # Добавляем медиану и процентили если есть данные
        daily_data = list(stats.get('daily_activity', {}).values())
        if daily_data:
            from utils import calculate_median, calculate_percentile
            summary['median_daily'] = calculate_median(daily_data)
            summary['p90_daily'] = calculate_percentile(daily_data, 90)
        
        return summary
    
    def get_comparison_stats(self, user_id: int) -> Dict[str, Any]:
        data = get_comparison_data()
        
        if not data['total_users']:
            return {
                'total_users': 0,
                'avg_shleps': 0,
                'percentile': 0,
                'rank': 1,
                'user_shleps': 0,
                'median_shleps': 0
            }
        
        from database import get_user_stats
        _, user_shleps, _ = get_user_stats(user_id)
        
        # Статистика распределения
        counts = data['user_counts']
        better_than = sum(1 for c in counts if c > user_shleps)
        rank = better_than + 1
        percentile = ((data['total_users'] - better_than) / data['total_users'] * 100)
        
        # Медиана
        from utils import calculate_median
        median_shleps = calculate_median(counts) if counts else 0
        avg_shleps = sum(counts) / len(counts) if counts else 0
        
        return {
            'total_users': data['total_users'],
            'avg_shleps': round(avg_shleps, 1),
            'median_shleps': round(median_shleps, 1),
            'percentile': round(percentile, 1),
            'rank': rank,
            'user_shleps': user_shleps
        }
    
    def get_global_trends_info(self) -> Dict[str, Any]:
        trends = get_global_trends()
        
        # Дополнительные метрики
        if trends['shleps_24h'] > 0 and trends['active_users_24h'] > 0:
            trends['avg_per_user_24h'] = round(trends['shleps_24h'] / trends['active_users_24h'], 1)
        else:
            trends['avg_per_user_24h'] = 0
        
        # Прогноз на сегодня
        if trends['current_hour'] > 0:
            avg_per_hour = trends['shleps_this_hour'] / (trends['current_hour'] + 1)
            trends['projected_today'] = int(avg_per_hour * 24)
        else:
            trends['projected_today'] = 0
        
        return trends
    
    def format_daily_chart(self, user_id: int, days: int = 7) -> str:
        activity = self.get_daily_activity(user_id, days)
        
        if not activity:
            return "📊 Нет данных за последние дни"
        
        max_val = max(activity.values()) if activity else 1
        lines = []
        
        for date_str, count in activity.items():
            bar_len = int((count / max_val) * 15)
            bar = "█" * bar_len + "░" * (15 - bar_len)
            emoji = "🔥" if count > 10 else "⚡" if count > 5 else "👉" if count > 0 else "⏸️"
            lines.append(f"{emoji} {date_str}: {bar} {count}")
        
        return "\n".join(lines)
    
    def format_hourly_chart(self, user_id: int) -> str:
        hours = self.get_hourly_distribution(user_id, 30)
        
        if not any(hours):
            return "⏰ Нет данных по часам"
        
        lines = ["⏰ *Активность по часам:*"]
        
        for i in range(0, 24, 4):
            total = sum(hours[i:i+4])
            max_total = max([sum(hours[j:j+4]) for j in range(0, 24, 4)]) or 1
            bar_len = int((total / max_total) * 15)
            bar = "█" * bar_len + "░" * (15 - bar_len)
            lines.append(f"{i:02d}:00-{i+3:02d}:00: {bar} {total}")
        
        return "\n".join(lines)

# Глобальный экземпляр
stats_system = StatisticsSystem()

# Интерфейс для импорта
def get_daily_activity(user_id: int, days: int = 7):
    return stats_system.get_daily_activity(user_id, days)

def get_hourly_distribution(user_id: int, days: int = 30):
    return stats_system.get_hourly_distribution(user_id, days)

def get_favorite_time(user_id: int):
    return stats_system.get_favorite_time(user_id)

def get_activity_summary(user_id: int):
    return stats_system.get_activity_summary(user_id)

def get_comparison_stats(user_id: int):
    return stats_system.get_comparison_stats(user_id)

def get_global_trends_info():
    return stats_system.get_global_trends_info()

def format_daily_activity_chart(user_id: int, days: int = 7):
    return stats_system.format_daily_chart(user_id, days)

def format_hourly_distribution_chart(user_id: int):
    return stats_system.format_hourly_chart(user_id)

if __name__ == "__main__":
    print("🔍 Тест statistics.py")
    print("=" * 50)
    
    test_user = 123456
    print("1. Любимое время тестового пользователя:")
    print(get_favorite_time(test_user))
    
    print("\n2. Глобальные тренды:")
    trends = get_global_trends_info()
    for key in ['active_users_24h', 'shleps_24h', 'active_today']:
        print(f"   {key}: {trends.get(key, 0)}")
    
    print("=" * 50)
