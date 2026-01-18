from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# ========== ОСНОВНЫЕ КЛАВИАТУРЫ ==========
def get_main_keyboard(for_chat: bool = False):
    """Универсальная клавиатура для чатов и ЛС"""
    if for_chat:
        # Для групповых чатов
        buttons = [
            [InlineKeyboardButton("👊 Шлёпнуть сейчас!", callback_data="shlep_mishok")],
            [
                InlineKeyboardButton("📊 Статистика", callback_data="chat_stats"),
                InlineKeyboardButton("🏆 Топ чата", callback_data="chat_top")
            ],
            [
                InlineKeyboardButton("🎯 Мой уровень", callback_data="level_inline"),
                InlineKeyboardButton("❓ Помощь", callback_data="help_inline")
            ]
        ]
    else:
        # Для личных сообщений
        buttons = [
            [KeyboardButton("👊 Шлёпнуть Мишка")],
            [
                KeyboardButton("🎯 Уровень"),
                KeyboardButton("📊 Статистика")
            ],
            [KeyboardButton("❓ Помощь")]
        ]
        return ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    
    return InlineKeyboardMarkup(buttons)

def get_quick_actions():
    """Быстрые действия для шлёпка"""
    buttons = [
        [
            InlineKeyboardButton("👊 Ещё раз!", callback_data="quick_shlep"),
            InlineKeyboardButton("📊 Стата", callback_data="quick_stats")
        ],
        [
            InlineKeyboardButton("🎯 Уровень", callback_data="quick_level"),
            InlineKeyboardButton("⚔️ Дуэль", callback_data="quick_duel")
        ],
        [
            InlineKeyboardButton("🗳️ Голосование", callback_data="quick_vote"),
            InlineKeyboardButton("📈 Топ дня", callback_data="quick_daily_top")
        ]
    ]
    return InlineKeyboardMarkup(buttons)

# ========== СПЕЦИАЛЬНЫЕ КЛАВИАТУРЫ ==========
def get_vote_keyboard(vote_id: int):
    """Клавиатура для голосования"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👍 За", callback_data=f"vote_yes_{vote_id}"),
            InlineKeyboardButton("👎 Против", callback_data=f"vote_no_{vote_id}")
        ],
        [InlineKeyboardButton("📊 Результаты", callback_data=f"vote_results_{vote_id}")]
    ])

def get_confirm_keyboard(action: str, item_id: int = 0):
    """Клавиатура подтверждения"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Да", callback_data=f"confirm_yes_{action}_{item_id}"),
            InlineKeyboardButton("❌ Нет", callback_data=f"confirm_no_{action}_{item_id}")
        ]
    ])

# ========== АЛИАСЫ ДЛЯ СОВМЕСТИМОСТИ ==========
# Старые названия функций для совместимости
def get_game_keyboard():
    return get_main_keyboard(for_chat=False)

def get_inline_keyboard():
    return get_main_keyboard(for_chat=True)

def get_chat_quick_actions():
    return get_quick_actions()

def get_chat_vote_keyboard(vote_id: int):
    return get_vote_keyboard(vote_id)

def get_back_button(back_to: str = "main"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Назад", callback_data=f"back_{back_to}")]
    ])

# Пустые функции для совместимости (больше не используются)
def get_chat_duel_keyboard(*args, **kwargs): return None
def get_chat_admin_keyboard(*args, **kwargs): return None
def get_chat_roles_keyboard(*args, **kwargs): return None
def get_chat_notification_keyboard(*args, **kwargs): return None
def get_chat_record_keyboard(*args, **kwargs): return None
def get_confirm_keyboard(*args, **kwargs): return None
