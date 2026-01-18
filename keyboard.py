from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

def get_main_keyboard():
    """Основная клавиатура для личных сообщений"""
    return ReplyKeyboardMarkup([
        [KeyboardButton("👊 Шлёпнуть Мишка")],
        [KeyboardButton("📊 Статистика"), KeyboardButton("👴 О Мишке")]
    ], resize_keyboard=True)

def get_inline_keyboard():
    """Inline-кнопка для групп"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👊 Шлёпнуть Мишка по лысине", callback_data="shlep_mishok")]
    ])

def get_group_welcome_keyboard():
    """Клавиатура при добавлении в группу"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 Команды бота", callback_data="help_in_group")],
        [InlineKeyboardButton("👊 Шлёпнуть сейчас!", callback_data="shlep_mishok")]
    ])
