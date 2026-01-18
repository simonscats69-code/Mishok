#!/usr/bin/env python3
"""
Statistics module for Mishok bot - адаптирован для SQLite
"""

import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from database import get_detailed_stats, get_global_trends

class StatisticsSystem:
    def __init__(self):
        pass
    
    def get_daily_activity(self, user_id: int, days: int = 7) -> Dict[str, int]:
        """
        Возвращает активность пользователя по дням
        
        Args:
            user_id: ID пользователя
            days: количество дней для анализа (по умолчанию 7)
        
        Returns:
            Словарь {дата: количество_шлёпков}
        """
        try:
            stats = get_detailed_stats(user_id, days)
            daily_data = stats.get('daily_activity', {})
            
            # Форматируем даты
            result = {}
            for date_obj, count in daily_data.items():
                if isinstance(date_obj, str):
                    date_str = date_obj
                else:
                    date_str = date_obj.strftime("%d.%m")
                result[date_str] = count
            
            return result
        except Exception as e:
            print(f"❌ Ошибка в get_daily_activity: {e}")
            return {}
    
    def get_hourly_distribution(self, user_id: int, days: int = 30) -> List[int]:
        """
        Возвращает распределение шлёпков по часам суток
        
        Args:
            user_id: ID пользователя
            days: количество дней для анализа
        
        Returns:
            Список из 24 чисел - количество шлёпков в каждый час
        """
        try:
            stats = get_detailed_stats(user_id, days)
            return stats.get('hourly_distribution', [0] * 24)
        except Exception as e:
            print(f"❌ Ошибка в get_hourly_distribution: {e}")
            return [0] * 24
    
    def get_favorite_time(self, user_id: int) -> str:
        """
        Определяет любимое время пользователя для шлёпков
        
        Args:
            user_id: ID пользователя
        
        Returns:
            Строка с описанием любимого времени
        """
        distribution = self.get_hourly_distribution(user_id, 30)
        
        if not any(distribution):
            return "Пока нет данных о твоей активности 📊"
        
        max_hour = distribution.index(max(distribution))
        max_count = max(distribution)
        
        # Определяем время суток
        if 0 <= max_hour < 6:
            time_desc = "ночью 🌙"
            time_range = "с 0:00 до 6:00"
        elif 6 <= max_hour < 12:
            time_desc = "утром 🌅"
            time_range = "с 6:00 до 12:00"
        elif 12 <= max_hour < 18:
            time_desc = "днём ☀️"
            time_range = "с 12:00 до 18:00"
        else:
            time_desc = "вечером 🌆"
            time_range = "с 18:00 до 24:00"
        
        hour_formatted = f"{max_hour:02d}:00"
        
        times_of_day = [
            (0, 5, "🌙 Ночью (0-6)", sum(distribution[0:6])),
            (6, 11, "🌅 Утром (6-12)", sum(distribution[6:12])),
            (12, 17, "☀️ Днём (12-18)", sum(distribution[12:18])),
            (18, 23, "🌆 Вечером (18-24)", sum(distribution[18:24]))
        ]
        
        # Находим самое активное время суток
        best_period = max(times_of_day, key=lambda x: x[3])
        
        return (
            f"⏰ *Любимое время:* {time_desc} ({hour_formatted})\n"
            f"📊 *Шлёпков в этот час:* {max_count}\n"
            f"🎯 *Самое активное время суток:* {best_period[2]}\n"
            f"📈 *Всего шлёпков {best_period[2].split()[0].lower()}:* {best_period[3]}"
        )
    
    def get_activity_summary(self, user_id: int) -> Dict[str, Any]:
        """
        Возвращает сводку активности пользователя
        
        Args:
            user_id: ID пользователя
        
        Returns:
            Словарь с различными метриками активности
        """
        try:
            stats = get_detailed_stats(user_id, 365)  # За весь период
            summary = stats.get('summary', {})
            
            # Добавляем дополнительные метрики
            hourly = self.get_hourly_distribution(user_id, 30)
            if any(hourly):
                summary['most_active_hour'] = hourly.index(max(hourly))
                summary['avg_per_day'] = summary.get('daily_avg', 0)
            
            return summary
        except Exception as e:
            print(f"❌ Ошибка в get_activity_summary: {e}")
            return {
                'active_days': 0,
                'total_shleps': 0,
                'last_active': None,
                'daily_avg': 0,
                'best_day': None,
                'best_day_count': 0
            }
    
    def get_comparison_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Сравнивает пользователя с другими
        
        Args:
            user_id: ID пользователя
        
        Returns:
            Словарь с метриками сравнения
        """
        try:
            # Подключаемся к базе для сложных запросов
            conn = sqlite3.connect("mishok.db")
            cursor = conn.cursor()
            
            # Общее количество пользователей
            cursor.execute("SELECT COUNT(DISTINCT user_id) as total_users FROM shleps WHERE user_id > 0")
            total_users = cursor.fetchone()[0] or 0
            
            if total_users == 0:
                return {
                    'total_users': 0,
                    'avg_shleps': 0,
                    'percentile': 0,
                    'rank': 1
                }
            
            # Среднее количество шлёпков на пользователя
            cursor.execute("""
                SELECT AVG(user_count) as avg_shleps 
                FROM (
                    SELECT user_id, COUNT(*) as user_count 
                    FROM shleps 
                    GROUP BY user_id
                )
            """)
            avg_shleps = cursor.fetchone()[0] or 0
            
            # Количество шлёпков текущего пользователя
            cursor.execute("SELECT COUNT(*) FROM shleps WHERE user_id = ?", (user_id,))
            user_shleps = cursor.fetchone()[0] or 0
            
            # Процент пользователей с меньшим количеством шлёпков
            cursor.execute("""
                SELECT COUNT(DISTINCT user_id) as better_users
                FROM shleps
                GROUP BY user_id
                HAVING COUNT(*) > ?
            """, (user_shleps,))
            better_users = cursor.fetchone()
            better_users = better_users[0] if better_users else 0
            
            rank = better_users + 1
            percentile = ((total_users - better_users) / total_users * 100) if total_users > 0 else 0
            
            conn.close()
            
            return {
                'total_users': total_users,
                'avg_shleps': round(avg_shleps, 1),
                'percentile': round(percentile, 1),
                'rank': rank,
                'user_shleps': user_shleps,
                'better_than': round(percentile, 1)
            }
            
        except Exception as e:
            print(f"❌ Ошибка в get_comparison_stats: {e}")
            return {
                'total_users': 0,
                'avg_shleps': 0,
                'percentile': 0,
                'rank': 1
            }
    
    def get_global_trends_info(self) -> Dict[str, Any]:
        """
        Возвращает глобальные тренды
        
        Returns:
            Словарь с глобальной статистикой
        """
        try:
            trends = get_global_trends()
            
            # Добавляем дополнительные вычисления
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
            
        except Exception as e:
            print(f"❌ Ошибка в get_global_trends_info: {e}")
            return {
                'active_users_24h': 0,
                'shleps_24h': 0,
                'active_today': 0,
                'current_hour': 0,
                'shleps_this_hour': 0
            }
    
    def format_daily_activity_chart(self, user_id: int, days: int = 7) -> str:
        """
        Форматирует активность в виде текстового графика
        
        Args:
            user_id: ID пользователя
            days: количество дней
        
        Returns:
            Строка с текстовым графиком
        """
        activity = self.get_daily_activity(user_id, days)
        
        if not activity:
            return "📊 Нет данных за последние дни"
        
        # Сортируем по дате
        sorted_dates = sorted(activity.items())
        
        # Находим максимум для масштабирования
        max_count = max(activity.values()) if activity else 1
        
        chart_lines = []
        for date_str, count in sorted_dates[-days:]:  # Последние N дней
            if max_count > 0:
                bar_length = int((count / max_count) * 20)  # Макс 20 символов
            else:
                bar_length = 0
            
            bar = "█" * bar_length
            if bar_length < 20:
                bar += "░" * (20 - bar_length)
            
            emoji = "🔥" if count > 10 else "⚡" if count > 5 else "👉" if count > 0 else "⏸️"
            
            chart_lines.append(f"{emoji} {date_str}: {bar} {count}")
        
        return "\n".join(chart_lines)
    
    def format_hourly_distribution_chart(self, user_id: int) -> str:
        """
        Форматирует распределение по часам в виде текстового графика
        
        Args:
            user_id: ID пользователя
        
        Returns:
            Строка с текстовым графиком
        """
        distribution = self.get_hourly_distribution(user_id, 30)
        
        if not any(distribution):
            return "⏰ Нет данных о распределении по часам"
        
        max_count = max(distribution)
        
        chart_lines = ["⏰ *Распределение по часам:*"]
        
        # Группируем по 4 часа для компактности
        for block_start in range(0, 24, 4):
            block_end = block_start + 3
            block_data = distribution[block_start:block_end+1]
            block_total = sum(block_data)
            
            if max_count > 0:
                bar_length = int((block_total / max_count) * 15)  # Макс 15 символов
            else:
                bar_length = 0
            
            bar = "█" * bar_length
            if bar_length < 15:
                bar += "░" * (15 - bar_length)
            
            time_range = f"{block_start:02d}:00-{block_end:02d}:00"
            chart_lines.append(f"{time_range}: {bar} {block_total}")
        
        return "\n".join(chart_lines)

# ========== ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР ==========
stats_system = StatisticsSystem()

# ========== ИНТЕРФЕЙС ДЛЯ ИМПОРТА ==========
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
    return stats_system.format_daily_activity_chart(user_id, days)

def format_hourly_distribution_chart(user_id: int):
    return stats_system.format_hourly_distribution_chart(user_id)

if __name__ == "__main__":
    print("🔍 Тестирование модуля статистики...")
    print("=" * 50)
    
    # Тестовые данные
    test_user_id = 123456
    
    print("1. Любимое время:")
    print(get_favorite_time(test_user_id))
    
    print("\n2. Глобальные тренды:")
    trends = get_global_trends_info()
    for key, value in trends.items():
        print(f"   {key}: {value}")
    
    print("\n3. Сравнительная статистика:")
    comparison = get_comparison_stats(test_user_id)
    for key, value in comparison.items():
        print(f"   {key}: {value}")
    
    print("=" * 50)
