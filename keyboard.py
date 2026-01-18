from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

def get_main_keyboard():
    """Основная клавиатура для личных сообщений (старая)"""
    return ReplyKeyboardMarkup([
        [KeyboardButton("👊 Шлёпнуть Мишка")],
        [KeyboardButton("📊 Статистика"), KeyboardButton("🎯 Достижения")],
        [KeyboardButton("📅 Задания"), KeyboardButton("🏆 Рейтинг")],
        [KeyboardButton("👴 О Мишке")]
    ], resize_keyboard=True)

def get_game_keyboard():
    """Новая игровая клавиатура со всеми функциями"""
    return ReplyKeyboardMarkup([
        [KeyboardButton("👊 Шлёпнуть Мишка")],
        [KeyboardButton("🎯 Уровень"), KeyboardButton("📈 Статистика")],
        [KeyboardButton("🏆 Рекорды"), KeyboardButton("🎪 События")],
        [KeyboardButton("🎯 Цели"), KeyboardButton("⚡ Навыки")],
        [KeyboardButton("📅 Задания"), KeyboardButton("👴 О Мишке")]
    ], resize_keyboard=True)

def get_inline_keyboard():
    """Inline-кнопки для групп"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👊 Шлёпнуть Мишка", callback_data="shlep_mishok")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats_inline"),
         InlineKeyboardButton("🎯 Уровень", callback_data="level_inline")],
        [InlineKeyboardButton("🏆 Рекорды", callback_data="records_inline"),
         InlineKeyboardButton("🎪 События", callback_data="events_inline")]
    ])

def get_achievements_keyboard():
    """Клавиатура для достижений"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📈 Мои достижения", callback_data="my_achievements")],
        [InlineKeyboardButton("🎯 Следующее", callback_data="next_achievement")],
        [InlineKeyboardButton("🏆 Топ достижений", callback_data="top_achievements")]
    ])

def get_tasks_keyboard():
    """Клавиатура для заданий"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Мои задания", callback_data="my_tasks")],
        [InlineKeyboardButton("⏳ До конца дня", callback_data="time_remaining")],
        [InlineKeyboardButton("🎁 Полученные награды", callback_data="my_rewards")]
    ])

def get_rating_keyboard():
    """Клавиатура для рейтинга"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 За день", callback_data="daily_rating")],
        [InlineKeyboardButton("📈 За неделю", callback_data="weekly_rating")],
        [InlineKeyboardButton("👤 Моя позиция", callback_data="my_rating")]
    ])

def get_level_keyboard():
    """Клавиатура для уровня"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Прогресс уровня", callback_data="level_progress")],
        [InlineKeyboardButton("⚡ Мои навыки", callback_data="my_skills")],
        [InlineKeyboardButton("💰 Мои очки", callback_data="my_points")]
    ])

def get_stats_keyboard():
    """Клавиатура для статистики"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Активность", callback_data="activity_stats")],
        [InlineKeyboardButton("⏰ Любимое время", callback_data="favorite_time")],
        [InlineKeyboardButton("📈 График", callback_data="activity_chart")]
    ])

def get_records_keyboard():
    """Клавиатура для рекордов"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💪 Самый сильный", callback_data="strongest_record")],
        [InlineKeyboardButton("⚡ Самый быстрый", callback_data="fastest_record")],
        [InlineKeyboardButton("👊 Самая длинная серия", callback_data="combo_record")]
    ])

def get_events_keyboard():
    """Клавиатура для событий"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎪 Активные события", callback_data="active_events")],
        [InlineKeyboardButton("⏰ Ближайшие", callback_data="upcoming_events")],
        [InlineKeyboardButton("📅 Расписание", callback_data="events_schedule")]
    ])

def get_goals_keyboard():
    """Клавиатура для целей"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 Прогресс целей", callback_data="goals_progress")],
        [InlineKeyboardButton("👤 Мой вклад", callback_data="my_contribution")],
        [InlineKeyboardButton("🏆 Награды", callback_data="goals_rewards")]
    ])

def get_skills_keyboard():
    """Клавиатура для навыков"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 Меткий шлёпок", callback_data="skill_accurate_info")],
        [InlineKeyboardButton("👊 Серия ударов", callback_data="skill_combo_info")],
        [InlineKeyboardButton("💥 Критический удар", callback_data="skill_critical_info")],
        [InlineKeyboardButton("⚡ Улучшить навык...", callback_data="upgrade_skill_menu")]
    ])

def get_group_welcome_keyboard():
    """При добавлении в группу"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 Команды бота", callback_data="help_in_group")],
        [InlineKeyboardButton("👊 Шлёпнуть сейчас!", callback_data="shlep_mishok")]
    ])

def get_quick_actions_keyboard():
    """Быстрые действия для групп"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👊 Шлёпок", callback_data="shlep_mishok"),
            InlineKeyboardButton("📊 Статы", callback_data="stats_inline")
        ],
        [
            InlineKeyboardButton("🎯 Уровень", callback_data="level_inline"),
            InlineKeyboardButton("🏆 Рекорды", callback_data="records_inline")
        ]
    ])

def get_back_button(back_to: str = "main"):
    """Кнопка назад"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Назад", callback_data=f"back_{back_to}")]
    ])

def get_confirm_keyboard(action: str):
    """Клавиатура подтверждения"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Да", callback_data=f"confirm_{action}"),
            InlineKeyboardButton("❌ Нет", callback_data=f"cancel_{action}")
        ]
    ])

def get_navigation_keyboard(current: int, total: int, prefix: str):
    """Навигация по страницам"""
    buttons = []
    
    if current > 1:
        buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"{prefix}_{current-1}"))
    
    buttons.append(InlineKeyboardButton(f"{current}/{total}", callback_data="current_page"))
    
    if current < total:
        buttons.append(InlineKeyboardButton("Вперед ➡️", callback_data=f"{prefix}_{current+1}"))
    
    return InlineKeyboardMarkup([buttons])
