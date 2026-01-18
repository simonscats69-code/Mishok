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
            InlineKeyboardButton("👊 Шлёпнуть Мишка", callback_data="shlep_mishok"),
            InlineKeyboardButton("📊 Статистика", callback_data="stats_inline")
        ],
        [
            InlineKeyboardButton("🎯 Мой уровень", callback_data="level_inline"),
            InlineKeyboardButton("👴 О Мишке", callback_data="mishok_info")
        ]
    ])

def get_back_button(back_to: str = "main"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Назад", callback_data=f"back_{back_to}")]
    ])
