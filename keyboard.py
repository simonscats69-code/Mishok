from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

def get_shlep_session_keyboard():
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
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👊 НАЧАТЬ ШЛЁПАТЬ!", callback_data="start_shlep_session")],
        [
            InlineKeyboardButton("📊 Статистика", callback_data="stats_inline"),
            InlineKeyboardButton("🎯 Уровень", callback_data="level_inline")
        ]
    ])

def get_chat_vote_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👍 ЗА", callback_data="vote_yes"),
            InlineKeyboardButton("👎 ПРОТИВ", callback_data="vote_no")
        ]
    ])

def get_main_inline_keyboard():
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

def get_main_reply_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("👊 Шлёпнуть Мишка")],
        [KeyboardButton("🎯 Уровень"), KeyboardButton("📊 Статистика")],
        [KeyboardButton("📈 Моя статистика")],
        [KeyboardButton("❓ Помощь"), KeyboardButton("👴 О Мишке")]
    ], resize_keyboard=True, one_time_keyboard=False, selective=True)

def get_admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧹 Очистка", callback_data="admin_cleanup"),
         InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("💾 Бэкап", callback_data="admin_backup"),
         InlineKeyboardButton("🔧 Исправление", callback_data="admin_repair")],
        [InlineKeyboardButton("❌ Закрыть", callback_data="admin_close")]
    ])

def get_cleanup_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🗑️ Логи", callback_data="cleanup_logs"),
         InlineKeyboardButton("📦 Временные файлы", callback_data="cleanup_temp")],
        [InlineKeyboardButton("💾 Старые бэкапы", callback_data="cleanup_backups")],
        [InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]
    ])

def get_confirmation_keyboard(action: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"✅ Да, {action}", callback_data=f"confirm_{action}")],
        [InlineKeyboardButton("❌ Нет, отмена", callback_data="cancel_action")]
    ])

# Удаляем ненужные функции
get_inline_keyboard = get_main_inline_keyboard
