from telegram import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    ReplyKeyboardMarkup, 
    KeyboardButton
)

def get_main_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("👊 Шлёпнуть Мишка")],
        [KeyboardButton("📊 Статистика"), KeyboardButton("🏆 Достижения")],
        [KeyboardButton("⚡ Навыки"), KeyboardButton("👴 О Мишке")]
    ], resize_keyboard=True, input_field_placeholder="Выбери действие...")

def get_game_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("👊 Шлёпнуть Мишка")],
        [
            KeyboardButton("🎯 Уровень"), 
            KeyboardButton("📈 Статистика"),
            KeyboardButton("🎯 Цели")
        ],
        [
            KeyboardButton("⚡ Навыки"), 
            KeyboardButton("🏆 Достижения"),
            KeyboardButton("👴 О Мишке")
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

def get_simple_inline_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👊 Шлёпнуть сейчас!", callback_data="shlep_mishok"),
            InlineKeyboardButton("📊 Статистика", callback_data="stats_inline")
        ]
    ])

def get_group_welcome_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 Показать команды", callback_data="help_in_group")],
        [InlineKeyboardButton("👊 Шлёпнуть Мишка", callback_data="shlep_mishok")],
        [
            InlineKeyboardButton("📊 Статистика", callback_data="stats_inline"),
            InlineKeyboardButton("🎯 Уровень", callback_data="level_inline")
        ]
    ])

def get_achievements_keyboard():
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
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📅 Дата получения", callback_data=f"achievement_date_{achievement_id}"),
            InlineKeyboardButton("🎯 Следующее", callback_data="next_achievement")
        ],
        [InlineKeyboardButton("◀️ Назад к достижениям", callback_data="back_achievements")]
    ])

def get_level_keyboard():
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
            InlineKeyboardButton("📅 По дням", callback_data="daily_stats")
        ],
        [InlineKeyboardButton("◀️ Назад к меню", callback_data="back_main")]
    ])

def get_stats_period_keyboard(period="daily"):
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

def get_back_button(back_to: str = "main"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Назад", callback_data=f"back_{back_to}")]
    ])

def get_confirm_keyboard(action: str, yes_text="✅ Да", no_text="❌ Нет"):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(yes_text, callback_data=f"confirm_{action}"),
            InlineKeyboardButton(no_text, callback_data=f"cancel_{action}")
        ]
    ])

def get_navigation_keyboard(current_page: int, total_pages: int, prefix: str):
    buttons = []
    
    if current_page > 1:
        buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"{prefix}_{current_page-1}"))
    
    buttons.append(InlineKeyboardButton(f"{current_page}/{total_pages}", callback_data="current_page"))
    
    if current_page < total_pages:
        buttons.append(InlineKeyboardButton("Вперёд ➡️", callback_data=f"{prefix}_{current_page+1}"))
    
    return InlineKeyboardMarkup([buttons])

def get_main_menu_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎮 Играть", callback_data="play_menu"),
            InlineKeyboardButton("📊 Статистика", callback_data="stats_menu")
        ],
        [
            InlineKeyboardButton("🏆 Достижения", callback_data="achievements_menu"),
            InlineKeyboardButton("⚡ Прокачка", callback_data="level_menu")
        ],
        [
            InlineKeyboardButton("🎯 Цели", callback_data="goals_menu"),
            InlineKeyboardButton("🆘 Помощь", callback_data="help_menu")
        ]
    ])

def get_help_keyboard():
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

def create_custom_keyboard(buttons_data, columns=2):
    keyboard = []
    row = []
    
    for i, (text, callback) in enumerate(buttons_data):
        row.append(InlineKeyboardButton(text, callback_data=callback))
        
        if (i + 1) % columns == 0 or i == len(buttons_data) - 1:
            keyboard.append(row)
            row = []
    
    return InlineKeyboardMarkup(keyboard)

def create_grid_keyboard(items, prefix, columns=3):
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

def test_keyboards():
    keyboards = {
        "Основная": get_main_keyboard(),
        "Игровая": get_game_keyboard(),
        "Inline": get_inline_keyboard(),
        "Достижения": get_achievements_keyboard(),
        "Уровни": get_level_keyboard(),
        "Навыки": get_skills_keyboard(),
        "Статистика": get_stats_keyboard(),
        "Назад": get_back_button("main"),
        "Подтверждение": get_confirm_keyboard("test_action"),
        "Навигация": get_navigation_keyboard(2, 5, "page"),
        "Главное меню": get_main_menu_keyboard(),
        "Помощь": get_help_keyboard(),
    }
    
    print(f"✅ Создано {len(keyboards)} клавиатур")
    return keyboards

if __name__ == "__main__":
    test_keyboards()
    print("✅ Модуль клавиатур готов к работе")
