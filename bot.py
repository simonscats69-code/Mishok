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
        text += "📊 *За день:* не в топе\n"
    
    if weekly_pos:
        text += f"📈 *За неделю:* #{weekly_pos} ({weekly_count} шлёпков)\n"
    else:
        text += "📈 *За неделю:* не в топе\n"
    
    # Получаем общее количество шлёпков
    from database import get_connection
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT shlep_count FROM user_stats WHERE user_id = %s", (user.id,))
            result = cur.fetchone()
            total = result[0] if result else 0
    
    text += f"\n🎯 *Всего шлёпков:* {total}"
    
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)

# Обновляем функцию process_shlep для работы с системами:

async def process_shlep(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback: bool):
    """Основная логика шлёпка с системами"""
    user = update.effective_user
    chat = update.effective_chat
    
    # Добавляем в статистику
    total, user_count = add_shlep(user.id, user.username or user.first_name)
    
    # Проверяем достижения
    new_achievements = achievement_system.check_achievements(user.id, user_count)
    
    # Обновляем задачи
    completed_tasks = task_system.update_task_progress(user.id)
    
    # Выбираем случайную реакцию
    reaction = random.choice(MISHOK_REACTIONS)
    
    # Формируем сообщение
    message_text = f"""
{reaction}

*Шлёпок №{total}*
👤 {user.first_name}: {user_count} шлёпков
👴 Мишок: всё ещё лысый
    """
    
    # Добавляем информацию о новых достижениях
    if new_achievements:
        for ach in new_achievements:
            message_text += f"\n🎉 *Новое достижение!* {ach['emoji']} {ach['name']}"
            # Добавляем очки за достижение
            points = ach.get('points', 10)
            total_points = add_points(user.id, points)
            message_text += f" (+{points} очков)"
    
    # Добавляем информацию о выполненных задачах
    if completed_tasks:
        message_text += "\n\n📅 *Выполненные задания:*"
        for task in completed_tasks:
            message_text += f"\n✅ {task['emoji']} {task['name']} (+{task['reward']} очков)"
            add_points(user.id, task['reward'])
    
    # Отправляем ASCII анимацию (с вероятностью 10%)
    if random.random() < 0.1:
        animation = generate_animation()
        message_text += f"\n\n{animation}"
    
    # Отправляем сообщение
    if is_callback:
        await update.callback_query.edit_message_text(
            message_text,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            message_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_inline_keyboard() if chat.type != "private" else None
        )
    
    # Отправляем стикер
    sticker_key = random.choice(list(STICKERS.keys()))
    if STICKERS.get(sticker_key):
        try:
            if is_callback:
                await update.callback_query.message.reply_sticker(STICKERS[sticker_key])
            else:
                await update.message.reply_sticker(STICKERS[sticker_key])
        except:
            pass

# Обновляем обработчики в main():

def main():
    """Запуск бота"""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not found!")
        return
    
    # Создаём приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Основные команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("shlep", shlep_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("mishok", mishok_info))
    application.add_handler(CommandHandler("achievements", achievements_command))
    application.add_handler(CommandHandler("tasks", tasks_command))
    application.add_handler(CommandHandler("rating", rating_command))
    
    # Inline-кнопки для шлёпка
    application.add_handler(CallbackQueryHandler(shlep_callback, pattern="^shlep_mishok$"))
    
    # Inline-кнопки для статистики
    application.add_handler(CallbackQueryHandler(stats_inline_callback, pattern="^stats_inline$"))
    
    # Inline-кнопки для достижений
    application.add_handler(CallbackQueryHandler(my_achievements_callback, pattern="^my_achievements$"))
    application.add_handler(CallbackQueryHandler(next_achievement_callback, pattern="^next_achievement$"))
    application.add_handler(CallbackQueryHandler(top_achievements_callback, pattern="^top_achievements$"))
    
    # Inline-кнопки для заданий
    application.add_handler(CallbackQueryHandler(my_tasks_callback, pattern="^my_tasks$"))
    application.add_handler(CallbackQueryHandler(time_remaining_callback, pattern="^time_remaining$"))
    application.add_handler(CallbackQueryHandler(my_rewards_callback, pattern="^my_rewards$"))
    
    # Inline-кнопки для рейтинга
    application.add_handler(CallbackQueryHandler(daily_rating_callback, pattern="^daily_rating$"))
    application.add_handler(CallbackQueryHandler(weekly_rating_callback, pattern="^weekly_rating$"))
    application.add_handler(CallbackQueryHandler(my_rating_callback, pattern="^my_rating$"))
    
    # Сообщения
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler))
    
    # Ошибки
    application.add_error_handler(error_handler)
    
    # Запуск
    logger.info("Бот запускается...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)
