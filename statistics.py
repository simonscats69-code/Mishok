from datetime import datetime, timedelta

# Убрали точку перед импортами - это вызывает ошибку
from database import get_detailed_stats, get_global_trends, get_comparison_data, get_user_stats
from utils import calculate_median, calculate_percentile

class Stats:
    def __init__(self): 
        pass
    
    def daily_activity(self, user_id, days=7):
        stats = get_detailed_stats(user_id, days)
        daily = stats.get('daily_activity', {})
        result = {}
        
        for date_str, count in daily.items():
            try: 
                date_obj = datetime.fromisoformat(date_str)
                result[date_obj.strftime("%d.%m")] = count
            except: 
                result[date_str] = count
        
        end = datetime.now().date()
        start = end - timedelta(days=days-1)
        cur = start
        
        while cur <= end:
            key = cur.strftime("%d.%m")
            if key not in result:
                result[key] = 0
            cur += timedelta(days=1)
        
        sorted_items = sorted(
            result.items(), 
            key=lambda x: datetime.strptime(x[0], "%d.%m").date()
        )
        return dict(sorted_items)
    
    def hourly_dist(self, user_id, days=30):
        return get_detailed_stats(user_id, days).get('hourly_distribution', [0]*24)
    
    def favorite_time(self, user_id):
        hours = self.hourly_dist(user_id, 30)
        if not any(hours): 
            return "📊 Пока нет данных"
        
        max_hour = hours.index(max(hours))
        max_count = max(hours)
        
        blocks = [
            (0, 5, "🌙 Ночью (0-6)", sum(hours[0:6])),
            (6, 11, "🌅 Утром (6-12)", sum(hours[6:12])),
            (12, 17, "☀️ Днём (12-18)", sum(hours[12:18])),
            (18, 23, "🌆 Вечером (18-24)", sum(hours[18:24]))
        ]
        
        best = max(blocks, key=lambda x: x[3])
        
        if 0 <= max_hour < 6:
            desc = "ночью 🌙"
        elif 6 <= max_hour < 12:
            desc = "утром 🌅"
        elif 12 <= max_hour < 18:
            desc = "днём ☀️"
        else:
            desc = "вечером 🌆"
        
        return f"""⏰ *Любимое время:* {desc} ({max_hour:02d}:00)
📊 *В этот час:* {max_count}
🎯 *Самое активное:* {best[2]}
📈 *Всего {best[2].split()[0].lower()}:* {best[3]}"""
    
    def comparison(self, user_id):
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
        
        _, user_shleps, _ = get_user_stats(user_id)
        counts = data['user_counts']
        better = sum(1 for c in counts if c > user_shleps)
        rank = better + 1
        perc = ((data['total_users'] - better) / data['total_users'] * 100)
        
        median = calculate_median(counts) if counts else 0
        avg = sum(counts) / len(counts) if counts else 0
        
        return {
            'total_users': data['total_users'],
            'avg_shleps': round(avg, 1),
            'median_shleps': round(median, 1),
            'percentile': round(perc, 1),
            'rank': rank,
            'user_shleps': user_shleps
        }
    
    def global_trends(self):
        trends = get_global_trends()
        
        if trends['shleps_24h'] > 0 and trends['active_users_24h'] > 0:
            trends['avg_per_user_24h'] = round(trends['shleps_24h'] / trends['active_users_24h'], 1)
        else: 
            trends['avg_per_user_24h'] = 0
        
        if trends['current_hour'] > 0:
            avg_per_hour = trends['shleps_this_hour'] / (trends['current_hour'] + 1)
            trends['projected_today'] = int(avg_per_hour * 24)
        else: 
            trends['projected_today'] = 0
        
        return trends
    
    def daily_chart(self, user_id, days=7):
        act = self.daily_activity(user_id, days)
        if not act: 
            return "📊 Нет данных"
        
        mx = max(act.values()) if act else 1
        lines = []
        
        for date_str, cnt in act.items():
            bar_len = int((cnt / mx) * 15)
            bar = "█" * bar_len + "░" * (15 - bar_len)
            
            if cnt > 10:
                emoji = "🔥"
            elif cnt > 5:
                emoji = "⚡"
            elif cnt > 0:
                emoji = "👉"
            else:
                emoji = "⏸️"
            
            lines.append(f"{emoji} {date_str}: {bar} {cnt}")
        
        return "\n".join(lines)
    
    def hourly_chart(self, user_id):
        hours = self.hourly_dist(user_id, 30)
        if not any(hours): 
            return "⏰ Нет данных"
        
        lines = ["⏰ *Активность по часам:*"]
        
        for i in range(0, 24, 4):
            total = sum(hours[i:i+4])
            mx = max([sum(hours[j:j+4]) for j in range(0, 24, 4)]) or 1
            bar_len = int((total / mx) * 15)
            bar = "█" * bar_len + "░" * (15 - bar_len)
            lines.append(f"{i:02d}:00-{i+3:02d}:00: {bar} {total}")
        
        return "\n".join(lines)

# Создаем экземпляр и экспортируем функции
stats = Stats()

get_favorite_time = stats.favorite_time
get_comparison_stats = stats.comparison
get_global_trends_info = stats.global_trends
format_daily_activity_chart = stats.daily_chart
format_hourly_distribution_chart = stats.hourly_chart
