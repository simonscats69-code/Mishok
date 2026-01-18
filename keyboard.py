from telegram import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    ReplyKeyboardMarkup, 
    KeyboardButton
)

def get_game_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("👊 Шлёпнуть Мишка")],
        [
            KeyboardButton("🎯 Уровень"), 
            KeyboardButton("📈 Статистика"),
            KeyboardButton("🎯 Цели")
        ],
        [
            KeyboardButton("⚡ Навыки")
        ]
    ], resize_keyboard=True, input_field_placeholder="Выбери систему...")

def get_inline_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👊 Шлёпнуть Мишка", callback_data="shlep_mishok"),
            InlineKeyboardButton("📊 Статистика", callback_data="stats_inline")
        ],
        [
            InlineKeyboardButton("🎯 Уровень", callback_data="level_inline"),
            InlineKeyboardButton("🎯 Цели", callback_data="goals_inline")
        ]
    ])

def get_skills_keyboard():
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
            InlineKeyboardButton("📊 Мои навыки", callback_data="my_skills")
        ],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_main")]
    ])

def get_stats_keyboard():
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
            InlineKeyboardButton("🎯 Цели", callback_data="goals_stats")
        ],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_main")]
    ])

def get_goals_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎯 Активные цели", callback_data="active_goals"),
            InlineKeyboardButton("🏆 Завершённые", callback_data="completed_goals")
        ],
        [
            InlineKeyboardButton("📊 Мой вклад", callback_data="my_contributions"),
            InlineKeyboardButton("📈 Прогресс", callback_data="goals_progress")
        ],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_main")]
    ])

def get_upgrade_skill_keyboard(skill_id, can_upgrade=True, cost=0):
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

def get_back_button(back_to: str = "main"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Назад", callback_data=f"back_{back_to}")]
    ])
