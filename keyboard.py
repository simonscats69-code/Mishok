#!/usr/bin/env python3
"""
Keyboard module for Mishok bot
"""

from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# ========== ОСНОВНЫЕ КЛАВИАТУРЫ ==========
def get_main_keyboard(for_chat: bool = False):
    """Универсальная клавиатура для чатов и ЛС"""
    if for_chat:
        # Для групповых чатов - inline клавиатура
        buttons = [
            [InlineKeyboardButton("👊 Шлёпнуть сейчас!", callback_data="shlep_mishok")],
            [
                InlineKeyboardButton("📊 Статистика", callback_data="stats_inline"),
                InlineKeyboardButton("🏆 Топ чата", callback_data="chat_top")
            ],
            [
                InlineKeyboardButton("🎯 Мой уровень", callback_data="level_inline"),
                InlineKeyboardButton("📈 Моя статистика", callback_data="my_stats")
            ],
            [
                InlineKeyboardButton("📊 Глобальные тренды", callback_data="trends"),
                InlineKeyboardButton("❓ Помощь", callback_data="help_inline")
            ]
        ]
    else:
        # Для личных сообщений - обычная клавиатура
        buttons = [
            [KeyboardButton("👊 Шлёпнуть Мишка")],
            [
                KeyboardButton("🎯 Уровень"),
                KeyboardButton("📊 Статистика")
            ],
            [
                KeyboardButton("📈 Моя статистика"),
                KeyboardButton("📊 Тренды")
            ],
            [KeyboardButton("❓ Помощь")]
        ]
        return ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=False)
    
    return InlineKeyboardMarkup(buttons)

def get_quick_actions():
    """Быстрые действия после шлёпка"""
    buttons = [
        [
            InlineKeyboardButton("👊 Ещё раз!", callback_data="quick_shlep"),
            InlineKeyboardButton("📊 Стата чата", callback_data="quick_stats")
        ],
        [
            InlineKeyboardButton("🎯 Уровень", callback_data="quick_level"),
            InlineKeyboardButton("📈 Моя стата", callback_data="quick_my_stats")
        ],
        [
            InlineKeyboardButton("📊 Глобальные тренды", callback_data="quick_trends"),
            InlineKeyboardButton("🗳️ Голосование", callback_data="quick_vote")
        ],
        [
            InlineKeyboardButton("⚔️ Дуэль", callback_data="quick_duel"),
            InlineKeyboardButton("📈 Топ дня", callback_data="quick_daily_top")
        ]
    ]
    return InlineKeyboardMarkup(buttons)

def get_stats_keyboard():
    """Клавиатура для раздела статистики"""
    buttons = [
        [
            InlineKeyboardButton("📊 Общая статистика", callback_data="stats_inline"),
            InlineKeyboardButton("📈 Моя статистика", callback_data="my_stats")
        ],
        [
            InlineKeyboardButton("📊 Глобальные тренды", callback_data="trends"),
            InlineKeyboardButton("🏆 Топ игроков", callback_data="top_global")
        ],
        [
            InlineKeyboardButton("📅 Активность по дням", callback_data="daily_stats"),
            InlineKeyboardButton("⏰ По часам", callback_data="hourly_stats")
        ],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_main")]
    ]
    return InlineKeyboardMarkup(buttons)

def get_user_stats_keyboard():
    """Клавиатура для детальной статистики пользователя"""
    buttons = [
        [
            InlineKeyboardButton("📅 За неделю", callback_data="stats_week"),
            InlineKeyboardButton("📅 За месяц", callback_data="stats_month")
        ],
        [
            InlineKeyboardButton("⏰ По часам", callback_data="stats_hours"),
            InlineKeyboardButton("📊 Сравнение", callback_data="stats_compare")
        ],
        [
            InlineKeyboardButton("📈 График активности", callback_data="stats_chart"),
            InlineKeyboardButton("🎯 Прогресс", callback_data="stats_progress")
        ],
        [InlineKeyboardButton("◀️ Назад к статистике", callback_data="back_stats")]
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

def get_duel_keyboard(duel_id: int, challenged_id: int):
    """Клавиатура для дуэли"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚔️ Принять вызов", callback_data=f"duel_accept_{duel_id}"),
            InlineKeyboardButton("🏃 Отказаться", callback_data=f"duel_decline_{duel_id}")
        ],
        [
            InlineKeyboardButton("📊 Статистика дуэли", callback_data=f"duel_stats_{duel_id}"),
            InlineKeyboardButton("⏰ Осталось времени", callback_data=f"duel_time_{duel_id}")
        ]
    ])

def get_confirm_keyboard(action: str, item_id: int = 0):
    """Клавиатура подтверждения"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Да", callback_data=f"confirm_yes_{action}_{item_id}"),
            InlineKeyboardButton("❌ Нет", callback_data=f"confirm_no_{action}_{item_id}")
        ]
    ])

def get_back_button(back_to: str = "main"):
    """Кнопка назад"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Назад", callback_data=f"back_{back_to}")]
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

def get_chat_duel_keyboard(duel_id: int, challenged_id: int):
    return get_duel_keyboard(duel_id, challenged_id)

# ========== ТЕКСТОВЫЕ КНОПКИ ДЛЯ ОТЛАДКИ ==========
def get_test_keyboard():
    """Клавиатура для тестирования (временная)"""
    buttons = [
        [InlineKeyboardButton("🔍 Тест БД", callback_data="test_db")],
        [InlineKeyboardButton("📊 Тест статистики", callback_data="test_stats")],
        [InlineKeyboardButton("⚙️ Тест кэша", callback_data="test_cache")],
        [InlineKeyboardButton("🔄 Сброс тестовых данных", callback_data="test_reset")]
    ]
    return InlineKeyboardMarkup(buttons)

# ========== КЛАВИАТУРА НАСТРОЕК ==========
def get_settings_keyboard():
    """Клавиатура настроек (для админов)"""
    buttons = [
        [InlineKeyboardButton("💾 Создать бэкап", callback_data="settings_backup")],
        [InlineKeyboardButton("📊 Статистика БД", callback_data="settings_db_stats")],
        [InlineKeyboardButton("🔄 Очистить кэш", callback_data="settings_clear_cache")],
        [InlineKeyboardButton("⚙️ Настройки уведомлений", callback_data="settings_notifications")],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_main")]
    ]
    return InlineKeyboardMarkup(buttons)

# ========== ПУСТЫЕ ФУНКЦИИ ДЛЯ СОВМЕСТИМОСТИ ==========
def get_chat_admin_keyboard(*args, **kwargs): 
    """Заглушка для совместимости"""
    return None

def get_chat_roles_keyboard(*args, **kwargs): 
    """Заглушка для совместимости"""
    return None

def get_chat_notification_keyboard(*args, **kwargs): 
    """Заглушка для совместимости"""
    return None

def get_chat_record_keyboard(*args, **kwargs): 
    """Заглушка для совместимости"""
    return None

if __name__ == "__main__":
    print("🔍 Тестирование клавиатур...")
    print("=" * 50)
    
    print("1. Основная клавиатура (для чатов):")
    kb = get_main_keyboard(for_chat=True)
    print(f"   Кнопок: {len(kb.inline_keyboard)} строк")
    
    print("\n2. Основная клавиатура (для ЛС):")
    kb2 = get_main_keyboard(for_chat=False)
    print(f"   Кнопок: {len(kb2.keyboard)} строк")
    
    print("\n3. Быстрые действия:")
    kb3 = get_quick_actions()
    print(f"   Кнопок: {len(kb3.inline_keyboard)} строк")
    
    print("\n4. Клавиатура статистики:")
    kb4 = get_stats_keyboard()
    print(f"   Кнопок: {len(kb4.inline_keyboard)} строк")
    
    print("=" * 50)
    print("✅ Все клавиатуры созданы успешно!")
