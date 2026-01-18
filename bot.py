import logging
import random
from datetime import datetime
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters, JobQueue
)
from telegram.constants import ParseMode

from config import BOT_TOKEN, MISHOK_REACTIONS, MISHOK_INTRO, STICKERS
from database import init_db, add_shlep, get_stats, get_top_users, add_points
from keyboard import get_main_keyboard, get_inline_keyboard, get_achievements_keyboard, get_tasks_keyboard, get_rating_keyboard
from achievements import AchievementSystem
from tasks import TaskSystem, RatingSystem
from utils import get_moscow_time, format_time_remaining, generate_animation

# Инициализация систем
achievement_system = AchievementSystem()
task_system = TaskSystem()
rating_system = RatingSystem()

# Добавляем новые команды в обработчики:

async def achievements_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /achievements"""
    await update.message.reply_text(
        "🎯 *Система достижений*\n\n"
        "Получайте достижения за шлёпки! Чем больше шлёпаете, тем круче достижения!",
        reply_markup=get_achievements_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

async def tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /tasks"""
    user = update.effective_user
    task_system.init_user_tasks(user.id)
    
    await update.message.reply_text(
        "📅 *Ежедневные задания*\n\n"
        "Выполняй задания каждый день и получай награды! Задания обновляются в 00:00 по МСК.",
        reply_markup=get_tasks_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

async def rating_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /rating"""
    await update.message.reply_text(
        "🏆 *Рейтинги*\n\n"
        "Соревнуйся с другими в количестве шлёпков!",
        reply_markup=get_rating_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

# Добавляем новые CallbackQuery обработчики:

async def my_achievements_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Мои достижения"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    achievements = achievement_system.get_user_achievements(user.id)
    
    if not achievements:
        text = "🎯 У тебя пока нет достижений. Продолжай шлёпать!"
    else:
        text = "🏆 *Твои достижения:*\n\n"
        for ach in achievements:
            text += f"{ach['emoji']} *{ach['name']}*\n"
            text += f"  └ {ach['description']}\n\n"
    
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)

async def next_achievement_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Следующее достижение"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    # Получаем текущее количество шлёпков пользователя
    from database import get_connection
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT shlep_count FROM user_stats WHERE user_id = %s", (user.id,))
            result = cur.fetchone()
            current_count = result[0] if result else 0
    
    next_ach = achievement_system.get_next_achievement(current_count)
    
    if not next_ach:
        text = "🎉 Поздравляю! Ты получил все достижения! Ты настоящая легенда! 🏆"
    else:
        text = f"🎯 *Следующее достижение:*\n\n"
        text += f"{next_ach['emoji']} *{next_ach['name']}*\n"
        text += f"  └ {next_ach['description']}\n\n"
        text += f"📊 *Прогресс:* {current_count}/{next_ach['threshold']}\n"
        text += f"⏳ *Осталось:* {next_ach['remaining']} шлёпков"
    
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)

async def my_tasks_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Мои задания на сегодня"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    tasks = task_system.get_user_tasks(user.id)
    
    text = "📅 *Твои задания на сегодня:*\n\n"
    time_left = format_time_remaining()
    
    for task in tasks:
        status = "✅" if task['completed'] else "⏳"
        progress = f"{task['progress']}/{task['required']}"
        reward = f"+{task['reward']} очков"
        
        text += f"{task['emoji']} *{task['name']}*\n"
        text += f"  └ {status} {progress} | {reward}\n\n"
    
    text += f"⏰ *До конца дня:* {time_left}"
    
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)

async def daily_rating_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Рейтинг за день"""
    query = update.callback_query
    await query.answer()
    
    rating = rating_system.get_daily_rating()
    today = get_moscow_time().strftime("%d.%m.%Y")
    
    text = f"📊 *Рейтинг за {today}:*\n\n"
    
    if not rating:
        text += "Пока никто не шлёпал сегодня 😴"
    else:
        medals = ["🥇", "🥈", "🥉"] + [f"{i}." for i in range(4, 21)]
        
        for i, (user_id, username, count) in enumerate(rating[:10], 1):
            medal = medals[i-1] if i <= len(medals) else f"{i}."
            name = username or f"User {user_id}"
            text += f"{medal} {name}: *{count}* шлёпков\n"
    
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)

async def weekly_rating_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Рейтинг за неделю"""
    query = update.callback_query
    await query.answer()
    
    rating = rating_system.get_weekly_rating()
    
    text = "📈 *Рейтинг за неделю:*\n\n"
    
    if not rating:
        text += "Пока тихо на этой неделе... 😴"
    else:
        medals = ["🥇", "🥈", "🥉"] + [f"{i}." for i in range(4, 21)]
        
        for i, (user_id, username, count) in enumerate(rating[:10], 1):
            medal = medals[i-1] if i <= len(medals) else f"{i}."
            name = username or f"User {user_id}"
            text += f"{medal} {name}: *{count}* шлёпков\n"
    
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)

async def my_rating_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Моя позиция в рейтингах"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    daily_pos, daily_count = rating_system.get_user_daily_position(user.id)
    weekly_pos, weekly_count = rating_system.get_user_weekly_position(user.id)
    
    text = "👤 *Твои позиции в рейтингах:*\n\n"
    
    if daily_pos:
        text += f"📊 *За день:* #{daily_pos} ({daily_count} шлёпков)\n"
    else:
        text += "📊 *
