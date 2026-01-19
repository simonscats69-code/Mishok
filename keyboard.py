from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

def main_kb(for_chat=False):
    """Основная клавиатура - разная для чатов и личных сообщений"""
    if for_chat:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("👊 Шлёпнуть сейчас!", callback_data="shlep_mishok")],
            [
                InlineKeyboardButton("📊 Статистика", callback_data="stats_inline"),
                InlineKeyboardButton("🏆 Топ чата", callback_data="chat_top")
            ],
            [
                InlineKeyboardButton("🎯 Уровень", callback_data="level_inline"),
                InlineKeyboardButton("📈 Моя статистика", callback_data="my_stats")
            ],
            [
                InlineKeyboardButton("👴 О Мишке", callback_data="mishok_info")
            ],
            [
                InlineKeyboardButton("❓ Помощь", callback_data="help_inline")
            ]
        ])
    else:
        return ReplyKeyboardMarkup([
            [KeyboardButton("👊 Шлёпнуть Мишка")],
            [KeyboardButton("🎯 Уровень"), KeyboardButton("📊 Статистика")],
            [KeyboardButton("📈 Моя статистика")],
            [KeyboardButton("❓ Помощь"), KeyboardButton("👴 О Мишке")]
        ], resize_keyboard=True, one_time_keyboard=False, selective=True)

def get_shlep_session_keyboard():
    """Клавиатура для сессии шлёпания"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👊 Ещё раз!", callback_data="shlep_again"),
            InlineKeyboardButton("🎯 Уровень", callback_data="shlep_level")
        ],
        [
            InlineKeyboardButton("📊 Статистика", callback_data="shlep_stats"),
            InlineKeyboardButton("📈 Моя стата", callback_data="shlep_my_stats")
        ],
        [
            InlineKeyboardButton("🔙 Меню", callback_data="shlep_menu")
        ]
    ])

def get_shlep_start_keyboard():
    """Клавиатура для начала шлёпания"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👊 НАЧАТЬ ШЛЁПАТЬ!", callback_data="start_shlep_session")],
        [
            InlineKeyboardButton("📊 Статистика", callback_data="stats_inline"),
            InlineKeyboardButton("🎯 Уровень", callback_data="level_inline")
        ]
    ])

def get_chat_vote_keyboard():
    """Клавиатура для голосования в чате"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👍 ЗА", callback_data="vote_yes"),
            InlineKeyboardButton("👎 ПРОТИВ", callback_data="vote_no")
        ]
    ])

get_inline_keyboard = lambda: main_kb(for_chat=True)
