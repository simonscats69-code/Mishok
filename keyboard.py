from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

def get_main_keyboard():
    """Основная клавиатура для личных сообщений"""
    return ReplyKeyboardMarkup([
        [KeyboardButton("👊 Шлёпнуть Мишка")],
        [KeyboardButton("📊 Статистика"), KeyboardButton("🎯 Достижения")],
        [KeyboardButton("📅 Задания"), KeyboardButton("🏆 Рейтинг")],
        [KeyboardButton("👴 О Мишке")]
    ], resize_keyboard=True)

def get_inline_keyboard():
    """Inline-кнопка для групп"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👊 Шлёпнуть Мишка", callback_data="shlep_mishok")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats_inline"),
         InlineKeyboardButton("🏆 Рейтинг", callback_data="rating_inline")]
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
