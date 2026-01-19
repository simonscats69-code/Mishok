from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

def main_kb(for_chat=False):
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
                InlineKeyboardButton("📊 Тренды", callback_data="trends"),
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
            [KeyboardButton("📈 Моя статистика"), KeyboardButton("📊 Тренды")],
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
            InlineKeyboardButton("📊 Тренды", callback_data="shlep_trends"),
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

def quick_actions():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👊 Ещё раз!", callback_data="quick_shlep"),
            InlineKeyboardButton("📊 Стата чата", callback_data="quick_stats")
        ],
        [
            InlineKeyboardButton("🎯 Уровень", callback_data="quick_level"),
            InlineKeyboardButton("📈 Моя стата", callback_data="quick_my_stats")
        ],
        [
            InlineKeyboardButton("📊 Тренды", callback_data="quick_trends"),
            InlineKeyboardButton("🗳️ Голосование", callback_data="quick_vote")
        ],
        [
            InlineKeyboardButton("⚔️ Дуэль", callback_data="quick_duel")
        ]
    ])

def get_chat_vote_keyboard(vote_id=None):
    """Клавиатура для голосования с уникальным ID"""
    if vote_id is None:
        vote_id = "temp"
    
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👍 За", callback_data=f"vote_yes_{vote_id}"),
            InlineKeyboardButton("👎 Против", callback_data=f"vote_no_{vote_id}")
        ],
        [InlineKeyboardButton("🤷 Воздержаться", callback_data=f"vote_abstain_{vote_id}")]
    ])

def get_chat_duel_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚔️ Принять дуэль", callback_data="accept_duel")],
        [InlineKeyboardButton("❌ Отказаться", callback_data="decline_duel")]
    ])

def get_chat_admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("🔄 Сбросить кэш", callback_data="admin_clear_cache")],
        [InlineKeyboardButton("💾 Создать бэкап", callback_data="admin_backup")],
        [InlineKeyboardButton("📈 Топ 20", callback_data="admin_top_20")]
    ])

def get_chat_roles_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👑 Король шлёпков", callback_data="role_king")],
        [InlineKeyboardButton("🎯 Самый меткий", callback_data="role_accurate")],
        [InlineKeyboardButton("⚡ Спринтер", callback_data="role_sprinter")],
        [InlineKeyboardButton("💪 Силач", callback_data="role_strong")],
        [InlineKeyboardButton("📊 Все роли", callback_data="role_all")]
    ])

def get_chat_notification_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔔 Включить уведомления", callback_data="notify_on")],
        [InlineKeyboardButton("🔕 Выключить уведомления", callback_data="notify_off")],
        [InlineKeyboardButton("⏰ Настроить время", callback_data="notify_time")]
    ])

def get_chat_record_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏆 Глобальный рекорд", callback_data="record_global")],
        [InlineKeyboardButton("📊 Рекорд чата", callback_data="record_chat")],
        [InlineKeyboardButton("👤 Личный рекорд", callback_data="record_personal")],
        [InlineKeyboardButton("📈 История рекордов", callback_data="record_history")]
    ])

get_chat_quick_actions = quick_actions
get_inline_keyboard = lambda: main_kb(for_chat=True)
get_game_keyboard = lambda: main_kb(for_chat=False)
