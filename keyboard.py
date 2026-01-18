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
            KeyboardButton("📊 Статистика")
        ],
        [KeyboardButton("👴 О Мишке")]
    ], resize_keyboard=True, input_field_placeholder="Выбери действие...")

def get_inline_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👊 Шлёпнуть сейчас!", callback_data="shlep_mishok"),
        ],
        [
            InlineKeyboardButton("📊 Статистика чата", callback_data="chat_stats"),
            InlineKeyboardButton("🏆 Топ чата", callback_data="chat_top")
        ],
        [
            InlineKeyboardButton("🎯 Мой уровень", callback_data="level_inline"),
            InlineKeyboardButton("👴 Инфо", callback_data="mishok_info")
        ]
    ])

def get_chat_vote_keyboard(vote_id: int):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👍 Шлёпать!", callback_data=f"vote_yes_{vote_id}"),
            InlineKeyboardButton("👎 Не шлёпать", callback_data=f"vote_no_{vote_id}")
        ],
        [
            InlineKeyboardButton("📊 Результаты", callback_data=f"vote_results_{vote_id}")
        ]
    ])

def get_chat_duel_keyboard(duel_id: int = None):
    buttons = []
    if duel_id:
        buttons.append([
            InlineKeyboardButton("⚔️ Принять вызов", callback_data=f"duel_accept_{duel_id}"),
            InlineKeyboardButton("🚫 Отклонить", callback_data=f"duel_decline_{duel_id}")
        ])
    else:
        buttons.append([
            InlineKeyboardButton("⚔️ Вызвать на дуэль", callback_data="duel_start"),
            InlineKeyboardButton("🏆 Активные дуэли", callback_data="duel_list")
        ])
    
    buttons.append([
        InlineKeyboardButton("📊 Мои дуэли", callback_data="duel_my"),
        InlineKeyboardButton("👑 Роли в чате", callback_data="chat_roles")
    ])
    
    return InlineKeyboardMarkup(buttons)

def get_chat_quick_actions():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👊 Шлёпок", callback_data="quick_shlep"),
            InlineKeyboardButton("📊 Стата", callback_data="quick_stats")
        ],
        [
            InlineKeyboardButton("🎯 Уровень", callback_data="quick_level"),
            InlineKeyboardButton("📈 Топ дня", callback_data="quick_daily_top")
        ],
        [
            InlineKeyboardButton("🗳️ Голосование", callback_data="quick_vote"),
            InlineKeyboardButton("⚔️ Дуэль", callback_data="quick_duel")
        ]
    ])

def get_chat_admin_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Статистика чата", callback_data="admin_stats"),
            InlineKeyboardButton("👥 Роли", callback_data="admin_roles")
        ],
        [
            InlineKeyboardButton("⚙️ Настройки", callback_data="admin_settings"),
            InlineKeyboardButton("📢 Объявление", callback_data="admin_announce")
        ]
    ])

def get_chat_roles_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👑 Король шлёпков", callback_data="role_king"),
            InlineKeyboardButton("🎯 Самый меткий", callback_data="role_accurate")
        ],
        [
            InlineKeyboardButton("⚡ Спринтер", callback_data="role_sprinter"),
            InlineKeyboardButton("💪 Силач", callback_data="role_strong")
        ],
        [
            InlineKeyboardButton("📊 Все роли", callback_data="role_all"),
            InlineKeyboardButton("🏆 Мои роли", callback_data="role_my")
        ]
    ])

def get_chat_notification_keyboard(notification_id: int):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👊 Ответить шлёпком", callback_data=f"notify_shlep_{notification_id}"),
            InlineKeyboardButton("📊 Посмотреть", callback_data=f"notify_view_{notification_id}")
        ]
    ])

def get_chat_record_keyboard(record_type: str, record_id: int):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🏆 Поздравить!", callback_data=f"record_congrats_{record_type}_{record_id}"),
            InlineKeyboardButton("👊 Бросить вызов", callback_data=f"record_challenge_{record_type}_{record_id}")
        ],
        [
            InlineKeyboardButton("📊 Подробнее", callback_data=f"record_details_{record_type}_{record_id}")
        ]
    ])

def get_back_button(back_to: str = "main"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Назад", callback_data=f"back_{back_to}")]
    ])

def get_confirm_keyboard(action: str, confirm_id: int):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Да", callback_data=f"confirm_yes_{action}_{confirm_id}"),
            InlineKeyboardButton("❌ Нет", callback_data=f"confirm_no_{action}_{confirm_id}")
        ]
    ])
