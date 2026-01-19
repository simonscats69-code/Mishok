from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

def main_kb(for_chat=False):
    if for_chat:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("👊 Шлёпнуть сейчас!", callback_data="shlep_mishok")],
            [InlineKeyboardButton("📊 Статистика", callback_data="stats_inline"), InlineKeyboardButton("🏆 Топ чата", callback_data="chat_top")],
            [InlineKeyboardButton("🎯 Уровень", callback_data="level_inline"), InlineKeyboardButton("📈 Моя статистика", callback_data="my_stats")],
            [InlineKeyboardButton("📊 Тренды", callback_data="trends"), InlineKeyboardButton("❓ Помощь", callback_data="help_inline")]
        ])
    else:
        return ReplyKeyboardMarkup([[KeyboardButton("👊 Шлёпнуть Мишка")],[KeyboardButton("🎯 Уровень"),KeyboardButton("📊 Статистика")],[KeyboardButton("📈 Моя статистика"),KeyboardButton("📊 Тренды")],[KeyboardButton("❓ Помощь")]], resize_keyboard=True)

def quick_actions():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👊 Ещё раз!", callback_data="quick_shlep"), InlineKeyboardButton("📊 Стата чата", callback_data="quick_stats")],
        [InlineKeyboardButton("🎯 Уровень", callback_data="quick_level"), InlineKeyboardButton("📈 Моя стата", callback_data="quick_my_stats")],
        [InlineKeyboardButton("📊 Тренды", callback_data="quick_trends"), InlineKeyboardButton("🗳️ Голосование", callback_data="quick_vote")],
        [InlineKeyboardButton("⚔️ Дуэль", callback_data="quick_duel"), InlineKeyboardButton("📈 Топ дня", callback_data="quick_daily_top")]
    ])

# Только используемые callback_data:
# shlep_mishok, stats_inline, level_inline, chat_top, my_stats, trends, help_inline
# quick_shlep, quick_stats, quick_level, quick_my_stats, quick_trends, quick_vote, quick_duel, quick_daily_top

get_chat_quick_actions = quick_actions
get_inline_keyboard = lambda: main_kb(for_chat=True)
get_game_keyboard = lambda: main_kb(for_chat=False)

# Заглушки для совместимости (используются в bot.py импортами)
get_chat_vote_keyboard = lambda *_, **__: None
get_chat_duel_keyboard = lambda *_, **__: None
get_chat_admin_keyboard = lambda *_, **__: None
get_chat_roles_keyboard = lambda *_, **__: None
get_chat_notification_keyboard = lambda *_, **__: None
get_chat_record_keyboard = lambda *_, **__: None
