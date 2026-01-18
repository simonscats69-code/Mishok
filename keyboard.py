"""
📱 Модуль клавиатур для бота "Мишок Лысый"
Содержит все клавиатуры для личных сообщений и групп
"""

from telegram import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    ReplyKeyboardMarkup, 
    KeyboardButton
)

# ========== ОСНОВНЫЕ КЛАВИАТУРЫ ДЛЯ ЛИЧНЫХ СООБЩЕНИЙ ==========

def get_main_keyboard():
    """
    Основная клавиатура для личных сообщений
    Используется когда системы не загружены
    """
    return ReplyKeyboardMarkup([
        [KeyboardButton("👊 Шлёпнуть Мишка")],
        [KeyboardButton("📊 Статистика"), KeyboardButton("🎯 Достижения")],
        [KeyboardButton("📅 Задания"), KeyboardButton("🏆 Рейтинг")],
        [KeyboardButton("👴 О Мишке")]
    ], resize_keyboard=True, input_field_placeholder="Выбери действие...")


def get_game_keyboard():
    """
    Полная игровая клавиатура со всеми системами
    Используется когда системы загружены
    """
    return ReplyKeyboardMarkup([
        [KeyboardButton("👊 Шлёпнуть Мишка")],
        [
            KeyboardButton("🎯 Уровень"), 
            KeyboardButton("📈 Статистика"),
            KeyboardButton("🏆 Рекорды")
        ],
        [
            KeyboardButton("🎪 События"), 
            KeyboardButton("🎯 Цели"),
            KeyboardButton("⚡ Навыки")
        ],
        [
            KeyboardButton("📅 Задания"), 
            KeyboardButton("🏆 Рейтинг"),
            KeyboardButton("👴 О Мишке")
        ]
    ], resize_keyboard=True, input_field_placeholder="Выбери систему...")


# ========== INLINE-КЛАВИАТУРЫ ДЛЯ ГРУПП ==========

def get_inline_keyboard():
    """
    Основная inline-клавиатура для групп
    Показывается под сообщениями в чатах
    """
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👊 Шлёпнуть Мишка", callback_data="shlep_mishok"),
            InlineKeyboardButton("📊 Статистика", callback_data="stats_inline")
        ],
        [
            InlineKeyboardButton("🎯 Уровень", callback_data="level_inline"),
            InlineKeyboardButton("🏆 Рекорды", callback_data="records_inline")
        ],
        [
            InlineKeyboardButton("🎪 События", callback_data="events_inline"),
            InlineKeyboardButton("🎯 Цели", callback_data="goals_inline")
        ]
    ])


def get_simple_inline_keyboard():
    """
    Упрощённая inline-клавиатура для групп
    Когда нужно минимум кнопок
    """
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👊 Шлёпнуть сейчас!", callback_data="shlep_mishok"),
            InlineKeyboardButton("📊 Статистика", callback_data="stats_inline")
        ]
    ])


def get_group_welcome_keyboard():
    """
    Клавиатура при добавлении бота в группу
    """
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 Показать команды", callback_data="help_in_group")],
        [InlineKeyboardButton("👊 Шлёпнуть Мишка", callback_data="shlep_mishok")],
        [
            InlineKeyboardButton("📊 Статистика", callback_data="stats_inline"),
            InlineKeyboardButton("🎯 Уровень", callback_data="level_inline")
        ]
    ])


# ========== КЛАВИАТУРЫ ДЛЯ СИСТЕМЫ ДОСТИЖЕНИЙ ==========

def get_achievements_keyboard():
    """
    Клавиатура для системы достижений
    """
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📈 Мои достижения", callback_data="my_achievements"),
            InlineKeyboardButton("🎯 Следующее", callback_data="next_achievement")
        ],
        [
            InlineKeyboardButton("🏆 Топ достижений", callback_data="top_achievements"),
            InlineKeyboardButton("📊 Прогресс", callback_data="achievements_progress")
        ],
        [InlineKeyboardButton("◀️ Назад к меню", callback_data="back_main")]
    ])


def get_achievement_details_keyboard(achievement_id):
    """
    Клавиатура для детальной информации о достижении
    """
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📅 Дата получения", callback_data=f"achievement_date_{achievement_id}"),
            InlineKeyboardButton("🎯 Следующее", callback_data="next_achievement")
        ],
        [InlineKeyboardButton("◀️ Назад к достижениям", callback_data="back_achievements")]
    ])


# ========== КЛАВИАТУРЫ ДЛЯ СИСТЕМЫ ЗАДАНИЙ ==========

def get_tasks_keyboard():
    """
    Клавиатура для системы заданий
    """
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📋 Мои задания", callback_data="my_tasks"),
            InlineKeyboardButton("⏳ До конца дня", callback_data="time_remaining")
        ],
        [
            InlineKeyboardButton("🎁 Полученные награды", callback_data="my_rewards"),
            InlineKeyboardButton("📊 Прогресс", callback_data="tasks_progress")
        ],
        [InlineKeyboardButton("◀️ Назад к меню", callback_data="back_main")]
    ])


def get_task_details_keyboard(task_id, completed=False):
    """
    Клавиатура для детальной информации о задании
    """
    buttons = []
    
    if not completed:
        buttons.append([
            InlineKeyboardButton("✅ Отметить выполненным", callback_data=f"complete_task_{task_id}")
        ])
    
    buttons.append([
        InlineKeyboardButton("📋 Все задания", callback_data="my_tasks"),
        InlineKeyboardButton("◀️ Назад", callback_data="back_tasks")
    ])
    
    return InlineKeyboardMarkup(buttons)


# ========== КЛАВИАТУРЫ ДЛЯ СИСТЕМЫ РЕЙТИНГА ==========

def get_rating_keyboard():
    """
    Клавиатура для системы рейтинга
    """
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 За день", callback_data="daily_rating"),
            InlineKeyboardButton("📈 За неделю", callback_data="weekly_rating")
        ],
        [
            InlineKeyboardButton("👤 Моя позиция", callback_data="my_rating"),
            InlineKeyboardButton("🏆 Топ-10", callback_data="top10_rating")
        ],
        [
            InlineKeyboardButton("📅 За месяц", callback_data="monthly_rating"),
            InlineKeyboardButton("📊 Статистика", callback_data="rating_stats")
        ],
        [InlineKeyboardButton("◀️ Назад к меню", callback_data="back_main")]
    ])


def get_rating_period_keyboard(period="daily"):
    """
    Клавиатура для выбора периода рейтинга
    """
    periods = {
        "daily": "📊 За день",
        "weekly": "📈 За неделю", 
        "monthly": "📅 За месяц",
        "alltime": "🏆 За всё время"
    }
    
    buttons = []
    for key, text in periods.items():
        callback = f"rating_{key}" if key != period else "current_period"
        buttons.append([InlineKeyboardButton(
            text, 
            callback_data=callback
        )])
    
    buttons.append([InlineKeyboardButton("◀️ Назад к рейтингам", callback_data="back_rating")])
    
    return InlineKeyboardMarkup(buttons)


# ========== КЛАВИАТУРЫ ДЛЯ СИСТЕМЫ УРОВНЕЙ ==========

def get_level_keyboard():
    """
    Клавиатура для системы уровней
    """
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Прогресс уровня", callback_data="level_progress"),
            InlineKeyboardButton("⚡ Мои навыки", callback_data="my_skills")
        ],
        [
            InlineKeyboardButton("💰 Мои очки", callback_data="my_points"),
            InlineKeyboardButton("📈 История XP", callback_data="xp_history")
        ],
        [
            InlineKeyboardButton("🎯 Следующий уровень", callback_data="next_level_info"),
            InlineKeyboardButton("🏆 Достижения уровня", callback_data="level_achievements")
        ],
        [InlineKeyboardButton("◀️ Назад к меню", callback_data="back_main")]
    ])


def get_skills_keyboard():
    """
    Клавиатура для системы навыков
    """
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎯 Меткий шлёпок", callback_data="skill_accurate_info"),
            InlineKeyboardButton("👊 Серия ударов", callback_data="skill_combo_info")
        ],
        [
            InlineKeyboardButton("💥 Критический удар", callback_data="skill_critical_info"),
            InlineKeyboardButton("💰 Стоимость улучшений", callback_data="skills_cost")
        ],
        [
            InlineKeyboardButton("⚡ Улучшить навык...", callback_data="upgrade_skill_menu"),
            InlineKeyboardButton("📊 Эффективность", callback_data="skills_efficiency")
        ],
        [InlineKeyboardButton("◀️ Назад к уровням", callback_data="back_level")]
    ])


def get_upgrade_skill_keyboard(skill_id, can_upgrade=True, cost=0):
    """
    Клавиатура для улучшения навыка
    """
    buttons = []
    
    if can_upgrade:
        buttons.append([
            InlineKeyboardButton(f"⚡ Улучшить за {cost} очков", callback_data=f"upgrade_{skill_id}")
        ])
    
    buttons.append([
        InlineKeyboardButton("📋 Все навыки", callback_data="my_skills"),
        InlineKeyboardButton("◀️ Назад", callback_data="back_skills")
    ])
    
    return InlineKeyboardMarkup(buttons)


# ========== КЛАВИАТУРЫ ДЛЯ СИСТЕМЫ СТАТИСТИКИ ==========

def get_stats_keyboard():
    """
    Клавиатура для системы статистики
    """
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Активность", callback_data="activity_stats"),
            InlineKeyboardButton("⏰ По часам", callback_data="hourly_stats")
        ],
        [
            InlineKeyboardButton("📈 График", callback_data="activity_chart"),
            InlineKeyboardButton("👥 Сравнить", callback_data="compare_stats")
        ],
        [
            InlineKeyboardButton("🌐 Глобальная", callback_data="global_stats"),
            InlineKeyboardButton("📅 По дням", callback_data="daily_stats")
        ],
        [InlineKeyboardButton("◀️ Назад к меню", callback_data="back_main")]
    ])


def get_stats_period_keyboard(period="daily"):
    """
    Клавиатура для выбора периода статистики
    """
    periods = {
        "daily": "📅 За день",
        "weekly": "📈 За неделю",
        "monthly": "📊 За месяц", 
        "alltime": "🏆 За всё время"
    }
    
    buttons = []
    for key, text in periods.items():
        callback = f"stats_{key}" if key != period else "current_period"
        buttons.append([InlineKeyboardButton(text, callback_data=callback)])
    
    buttons.append([InlineKeyboardButton("◀️ Назад к статистике", callback_data="back_stats")])
    
    return InlineKeyboardMarkup(buttons)


# ========== КЛАВИАТУРЫ ДЛЯ СИСТЕМЫ РЕКОРДОВ ==========

def get_records_keyboard():
    """
    Клавиатура для системы рекордов
    """
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💪 Сила шлёпка", callback_data="record_strength"),
            InlineKeyboardButton("⚡ Скорость", callback_data="record_speed")
        ],
        [
            InlineKeyboardButton("👊 Серия ударов", callback_data="record_combo"),
            InlineKeyboardButton("📊 Средний удар", callback_data="record_average")
        ],
        [
            InlineKeyboardButton("🏆 Все рекорды", callback_data="all_records"),
            InlineKeyboardButton("👑 Мои рекорды", callback_data="my_records")
        ],
        [
            InlineKeyboardButton("📅 Рекорды дня", callback_data="daily_records"),
            InlineKeyboardButton("📈 Рекорды недели", callback_data="weekly_records")
        ],
        [InlineKeyboardButton("◀️ Назад к меню", callback_data="back_main")]
    ])


def get_record_details_keyboard(record_type):
    """
    Клавиатура для детальной информации о рекорде
    """
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📅 История", callback_data=f"record_history_{record_type}"),
            InlineKeyboardButton("👤 Детали", callback_data=f"record_details_{record_type}")
        ],
        [
            InlineKeyboardButton("🏆 Все рекорды", callback_data="all_records"),
            InlineKeyboardButton("◀️ Назад", callback_data="back_records")
        ]
    ])


# ========== КЛАВИАТУРЫ ДЛЯ СИСТЕМЫ СОБЫТИЙ ==========

def get_events_keyboard():
    """
    Клавиатура для системы событий
    """
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎪 Активные", callback_data="active_events"),
            InlineKeyboardButton("⏰ Предстоящие", callback_data="upcoming_events")
        ],
        [
            InlineKeyboardButton("📅 Расписание", callback_data="events_schedule"),
            InlineKeyboardButton("📈 Множитель", callback_data="current_multiplier")
        ],
        [
            InlineKeyboardButton("🎁 Награды", callback_data="events_rewards"),
            InlineKeyboardButton("📊 Статистика", callback_data="events_stats")
        ],
        [InlineKeyboardButton("◀️ Назад к меню", callback_data="back_main")]
    ])


def get_event_details_keyboard(event_id):
    """
    Клавиатура для детальной информации о событии
    """
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⏳ Таймер", callback_data=f"event_timer_{event_id}"),
            InlineKeyboardButton("🎁 Награды", callback_data=f"event_rewards_{event_id}")
        ],
        [
            InlineKeyboardButton("📊 Участие", callback_data=f"event_participation_{event_id}"),
            InlineKeyboardButton("◀️ Назад к событиям", callback_data="back_events")
        ]
    ])


# ========== КЛАВИАТУРЫ ДЛЯ СИСТЕМЫ ЦЕЛЕЙ ==========

def get_goals_keyboard():
    """
    Клавиатура для системы целей
    """
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎯 Глобальные цели", callback_data="global_goals"),
            InlineKeyboardButton("👤 Мой вклад", callback_data="my_contributions")
        ],
        [
            InlineKeyboardButton("📊 Прогресс", callback_data="goals_progress"),
            InlineKeyboardButton("🏆 Награды", callback_data="goals_rewards")
        ],
        [
            InlineKeyboardButton("👥 Участники", callback_data="goals_participants"),
            InlineKeyboardButton("⏳ Таймер", callback_data="goals_timer")
        ],
        [InlineKeyboardButton("◀️ Назад к меню", callback_data="back_main")]
    ])


def get_goal_details_keyboard(goal_id):
    """
    Клавиатура для детальной информации о цели
    """
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Прогресс", callback_data=f"goal_progress_{goal_id}"),
            InlineKeyboardButton("👤 Мой вклад", callback_data=f"goal_contribution_{goal_id}")
        ],
        [
            InlineKeyboardButton("👥 Топ участников", callback_data=f"goal_top_{goal_id}"),
            InlineKeyboardButton("🎁 Награда", callback_data=f"goal_reward_{goal_id}")
        ],
        [InlineKeyboardButton("◀️ Назад к целям", callback_data="back_goals")]
    ])


# ========== КЛАВИАТУРЫ НАВИГАЦИИ И УТИЛИТЫ ==========

def get_back_button(back_to: str = "main"):
    """
    Универсальная кнопка "Назад"
    
    Args:
        back_to: Куда возвращаться (main, achievements, tasks, rating, level, stats, records, events, goals)
    """
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Назад", callback_data=f"back_{back_to}")]
    ])


def get_confirm_keyboard(action: str, yes_text="✅ Да", no_text="❌ Нет"):
    """
    Клавиатура подтверждения действия
    
    Args:
        action: Идентификатор действия
        yes_text: Текст на кнопке "Да"
        no_text: Текст на кнопке "Нет"
    """
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(yes_text, callback_data=f"confirm_{action}"),
            InlineKeyboardButton(no_text, callback_data=f"cancel_{action}")
        ]
    ])


def get_navigation_keyboard(current_page: int, total_pages: int, prefix: str):
    """
    Клавиатура навигации по страницам
    
    Args:
        current_page: Текущая страница
        total_pages: Всего страниц
        prefix: Префикс для callback_data
    """
    buttons = []
    
    # Кнопка "Назад"
    if current_page > 1:
        buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"{prefix}_{current_page-1}"))
    
    # Номер текущей страницы
    buttons.append(InlineKeyboardButton(f"{current_page}/{total_pages}", callback_data="current_page"))
    
    # Кнопка "Вперёд"
    if current_page < total_pages:
        buttons.append(InlineKeyboardButton("Вперёд ➡️", callback_data=f"{prefix}_{current_page+1}"))
    
    return InlineKeyboardMarkup([buttons])


def get_main_menu_keyboard():
    """
    Клавиатура главного меню (inline версия)
    """
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎮 Играть", callback_data="play_menu"),
            InlineKeyboardButton("📊 Статистика", callback_data="stats_menu")
        ],
        [
            InlineKeyboardButton("🏆 Достижения", callback_data="achievements_menu"),
            InlineKeyboardButton("📅 Задания", callback_data="tasks_menu")
        ],
        [
            InlineKeyboardButton("⚡ Прокачка", callback_data="level_menu"),
            InlineKeyboardButton("🎪 События", callback_data="events_menu")
        ],
        [
            InlineKeyboardButton("🎯 Цели", callback_data="goals_menu"),
            InlineKeyboardButton("🏆 Рейтинг", callback_data="rating_menu")
        ],
        [InlineKeyboardButton("🆘 Помощь", callback_data="help_menu")]
    ])


def get_help_keyboard():
    """
    Клавиатура помощи
    """
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📖 Команды", callback_data="help_commands"),
            InlineKeyboardButton("🎮 Геймплей", callback_data="help_gameplay")
        ],
        [
            InlineKeyboardButton("⚡ Системы", callback_data="help_systems"),
            InlineKeyboardButton("🏆 Достижения", callback_data="help_achievements")
        ],
        [
            InlineKeyboardButton("📊 Статистика", callback_data="help_stats"),
            InlineKeyboardButton("🎯 Цели", callback_data="help_goals")
        ],
        [InlineKeyboardButton("◀️ Назад в меню", callback_data="back_main")]
    ])


def get_admin_keyboard():
    """
    Клавиатура для администратора
    """
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Статистика бота", callback_data="admin_stats"),
            InlineKeyboardButton("👥 Пользователи", callback_data="admin_users")
        ],
        [
            InlineKeyboardButton("🔧 Управление событиями", callback_data="admin_events"),
            InlineKeyboardButton("🎯 Управление целями", callback_data="admin_goals")
        ],
        [
            InlineKeyboardButton("⚙️ Настройки", callback_data="admin_settings"),
            InlineKeyboardButton("📦 Обновления", callback_data="admin_updates")
        ],
        [InlineKeyboardButton("◀️ Выход", callback_data="back_main")]
    ])


# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

def create_custom_keyboard(buttons_data, columns=2):
    """
    Создание кастомной клавиатуры из данных
    
    Args:
        buttons_data: Список кортежей (текст, callback_data)
        columns: Количество кнопок в строке
    """
    keyboard = []
    row = []
    
    for i, (text, callback) in enumerate(buttons_data):
        row.append(InlineKeyboardButton(text, callback_data=callback))
        
        if (i + 1) % columns == 0 or i == len(buttons_data) - 1:
            keyboard.append(row)
            row = []
    
    return InlineKeyboardMarkup(keyboard)


def create_grid_keyboard(items, prefix, columns=3):
    """
    Создание клавиатуры-сетки
    
    Args:
        items: Список элементов
        prefix: Префикс для callback_data
        columns: Количество колонок
    """
    keyboard = []
    row = []
    
    for i, item in enumerate(items):
        if hasattr(item, 'name') and hasattr(item, 'id'):
            text = item.name
            callback = f"{prefix}_{item.id}"
        elif isinstance(item, dict) and 'name' in item and 'id' in item:
            text = item['name']
            callback = f"{prefix}_{item['id']}"
        elif isinstance(item, tuple) and len(item) == 2:
            text, callback = item
        else:
            text = str(item)
            callback = f"{prefix}_{i}"
        
        row.append(InlineKeyboardButton(text, callback_data=callback))
        
        if (i + 1) % columns == 0 or i == len(items) - 1:
            keyboard.append(row)
            row = []
    
    return InlineKeyboardMarkup(keyboard)


# ========== ТЕСТОВАЯ ФУНКЦИЯ ==========

def test_keyboards():
    """Тестовая функция для проверки создания клавиатур"""
    keyboards = {
        "Основная": get_main_keyboard(),
        "Игровая": get_game_keyboard(),
        "Inline": get_inline_keyboard(),
        "Достижения": get_achievements_keyboard(),
        "Задания": get_tasks_keyboard(),
        "Рейтинг": get_rating_keyboard(),
        "Уровни": get_level_keyboard(),
        "Навыки": get_skills_keyboard(),
        "Статистика": get_stats_keyboard(),
        "Рекорды": get_records_keyboard(),
        "События": get_events_keyboard(),
        "Цели": get_goals_keyboard(),
        "Назад": get_back_button("main"),
        "Подтверждение": get_confirm_keyboard("test_action"),
        "Навигация": get_navigation_keyboard(2, 5, "page"),
        "Главное меню": get_main_menu_keyboard(),
        "Помощь": get_help_keyboard(),
        "Админка": get_admin_keyboard(),
    }
    
    print(f"✅ Создано {len(keyboards)} клавиатур")
    return keyboards


if __name__ == "__main__":
    # Тестирование при прямом запуске
    test_keyboards()
    print("✅ Модуль клавиатур готов к работе")
