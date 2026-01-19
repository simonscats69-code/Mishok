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
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👊 НАЧАТЬ ШЛЁПАТЬ!", callback_data="start_shlep_session")],
        [
            InlineKeyboardButton("📊 Статистика", callback_data="stats_inline"),
            InlineKeyboardButton("🎯 Уровень", callback_data="level_inline")
        ]
    ])

def get_chat_vote_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👍 За", callback_data="vote_yes")],
        [InlineKeyboardButton("👎 Против", callback_data="vote_no")],
        [InlineKeyboardButton("🤷 Воздержаться", callback_data="vote_abstain")]
    ])

def get_duel_invite_keyboard(challenger_id: int, target_id: int, duel_id: str):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚔️ Принять вызов!", 
                               callback_data=f"duel_accept_{duel_id}"),
            InlineKeyboardButton("❌ Отклонить", 
                               callback_data=f"duel_decline_{duel_id}")
        ]
    ])

def get_duel_active_keyboard(duel_id: str):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👊 Шлёпнуть в дуэли!", callback_data=f"duel_shlep_{duel_id}"),
            InlineKeyboardButton("📊 Статистика", callback_data=f"duel_stats_{duel_id}")
        ],
        [
            InlineKeyboardButton("🏳️ Сдаться", callback_data=f"duel_surrender_{duel_id}"),
            InlineKeyboardButton("🔄 Обновить", callback_data=f"duel_refresh_{duel_id}")
        ]
    ])

def get_duel_finished_keyboard(duel_id: str):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Детальная статистика", callback_data=f"duel_details_{duel_id}"),
            InlineKeyboardButton("⚔️ Реванш", callback_data=f"duel_rematch_{duel_id}")
        ],
        [
            InlineKeyboardButton("🏆 Топ дуэлей", callback_data="duel_top"),
            InlineKeyboardButton("❌ Закрыть", callback_data=f"duel_close_{duel_id}")
        ]
    ])

get_inline_keyboard = lambda: main_kb(for_chat=True)
get_game_keyboard = lambda: main_kb(for_chat=False)
