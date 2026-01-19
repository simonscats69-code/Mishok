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

def stats_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Общая", callback_data="stats_inline"), InlineKeyboardButton("📈 Моя", callback_data="my_stats")],
        [InlineKeyboardButton("📊 Тренды", callback_data="trends"), InlineKeyboardButton("🏆 Топ", callback_data="top_global")],
        [InlineKeyboardButton("📅 По дням", callback_data="daily_stats"), InlineKeyboardButton("⏰ По часам", callback_data="hourly_stats")],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_main")]
    ])

def user_stats_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 Неделя", callback_data="stats_week"), InlineKeyboardButton("📅 Месяц", callback_data="stats_month")],
        [InlineKeyboardButton("⏰ Часы", callback_data="stats_hours"), InlineKeyboardButton("📊 Сравнение", callback_data="stats_compare")],
        [InlineKeyboardButton("📈 График", callback_data="stats_chart"), InlineKeyboardButton("🎯 Прогресс", callback_data="stats_progress")],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_stats")]
    ])

def vote_kb(vote_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👍 За", callback_data=f"vote_yes_{vote_id}"), InlineKeyboardButton("👎 Против", callback_data=f"vote_no_{vote_id}")],
        [InlineKeyboardButton("📊 Результаты", callback_data=f"vote_results_{vote_id}")]
    ])

def duel_kb(duel_id, challenged_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚔️ Принять", callback_data=f"duel_accept_{duel_id}"), InlineKeyboardButton("🏃 Отказаться", callback_data=f"duel_decline_{duel_id}")],
        [InlineKeyboardButton("📊 Статистика", callback_data=f"duel_stats_{duel_id}"), InlineKeyboardButton("⏰ Время", callback_data=f"duel_time_{duel_id}")]
    ])

def confirm_kb(action, item_id=0):
    return InlineKeyboardMarkup([[InlineKeyboardButton("✅ Да", callback_data=f"confirm_yes_{action}_{item_id}"), InlineKeyboardButton("❌ Нет", callback_data=f"confirm_no_{action}_{item_id}")]])

def back_kb(back_to="main"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data=f"back_{back_to}")]])

def settings_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💾 Бэкап", callback_data="settings_backup")],
        [InlineKeyboardButton("📊 Статистика БД", callback_data="settings_db_stats")],
        [InlineKeyboardButton("🔄 Очистить кэш", callback_data="settings_clear_cache")],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_main")]
    ])

def test_kb():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔍 Тест БД", callback_data="test_db")],[InlineKeyboardButton("📊 Тест статистики", callback_data="test_stats")],[InlineKeyboardButton("⚙️ Тест кэша", callback_data="test_cache")],[InlineKeyboardButton("🔄 Сброс", callback_data="test_reset")]])

get_chat_quick_actions = quick_actions
get_inline_keyboard = lambda: main_kb(for_chat=True)
get_game_keyboard = lambda: main_kb(for_chat=False)
get_chat_vote_keyboard = vote_kb
get_chat_duel_keyboard = duel_kb
get_chat_admin_keyboard = lambda *_, **__: None
get_chat_roles_keyboard = lambda *_, **__: None
get_chat_notification_keyboard = lambda *_, **__: None
get_chat_record_keyboard = lambda *_, **__: None
