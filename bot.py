#!/usr/bin/env python3

import logging
import random
import sys
import os
import asyncio
from datetime import datetime, timedelta

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import (
        Application, CommandHandler, MessageHandler, CallbackQueryHandler,
        ContextTypes, filters
    )
    from telegram.constants import ParseMode
    TELEGRAM_AVAILABLE = True
except ImportError as e:
    logger.error(f"Ошибка импорта telegram: {e}")
    TELEGRAM_AVAILABLE = False
    class Update: pass
    class ContextTypes: 
        class DEFAULT_TYPE: pass

try:
    from config import (
        BOT_TOKEN, MISHOK_REACTIONS, MISHOK_INTRO
    )
    CONFIG_AVAILABLE = True
except ImportError as e:
    logger.error(f"Ошибка импорта config: {e}")
    CONFIG_AVAILABLE = False
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    MISHOK_REACTIONS = ["Ой, больно! 😠", "Эй, не шлёпай! 👴💢"]
    MISHOK_INTRO = "👴 *Мишок Лысый* - бот для шлёпков"

try:
    from database import (
        init_db, add_shlep, get_stats, get_top_users, 
        get_user_stats, get_chat_stats, get_chat_top_users,
        create_chat_vote, get_chat_vote, update_chat_vote,
        assign_chat_role, get_user_roles, get_chat_roles_stats
    )
    DATABASE_AVAILABLE = True
except ImportError as e:
    logger.error(f"Ошибка импорта database: {e}")
    DATABASE_AVAILABLE = False
    def init_db(): logger.info("БД: заглушка init_db")
    def add_shlep(user_id, username, damage=0, chat_id=None): 
        logger.info(f"БД: заглушка add_shlep для {user_id}")
        return (0, 0, 0)
    def get_stats(): return (0, None, 0, None, None)
    def get_top_users(limit=10): return []
    def get_user_stats(user_id): return (None, 0, None)
    def get_chat_stats(chat_id): return None
    def get_chat_top_users(chat_id, limit=10): return []
    def create_chat_vote(*args, **kwargs): return None
    def get_chat_vote(vote_id): return None
    def update_chat_vote(vote_id, user_id, vote_type): return False
    def assign_chat_role(*args, **kwargs): return False
    def get_user_roles(chat_id, user_id): return []
    def get_chat_roles_stats(chat_id): return {}

try:
    from keyboard import (
        get_game_keyboard, get_inline_keyboard,
        get_chat_vote_keyboard, get_chat_duel_keyboard,
        get_chat_quick_actions, get_chat_roles_keyboard,
        get_chat_notification_keyboard, get_chat_record_keyboard,
        get_back_button, get_confirm_keyboard
    )
    KEYBOARD_AVAILABLE = True
except ImportError as e:
    logger.error(f"Ошибка импорта keyboard: {e}")
    KEYBOARD_AVAILABLE = False
    def get_game_keyboard(): return None
    def get_inline_keyboard(): return None
    def get_chat_vote_keyboard(*args, **kwargs): return None
    def get_chat_duel_keyboard(*args, **kwargs): return None
    def get_chat_quick_actions(): return None
    def get_chat_roles_keyboard(): return None
    def get_chat_notification_keyboard(*args, **kwargs): return None
    def get_chat_record_keyboard(*args, **kwargs): return None
    def get_back_button(*args, **kwargs): return None
    def get_confirm_keyboard(*args, **kwargs): return None

try:
    from cache import cache
    CACHE_AVAILABLE = True
    logger.info("Кэш система загружена")
except ImportError as e:
    logger.warning(f"Кэш система не загружена: {e}")
    CACHE_AVAILABLE = False
    class StubCache:
        async def get(self, key): return None
        async def set(self, key, value): pass
        async def delete(self, key): return False
    cache = StubCache()

if not TELEGRAM_AVAILABLE:
    logger.error("Библиотека python-telegram-bot не установлена!")
    sys.exit(1)

if not BOT_TOKEN:
    logger.error("BOT_TOKEN не установлен! Добавь его в .env файл")
    sys.exit(1)

if DATABASE_AVAILABLE:
    try:
        init_db()
        logger.info("База данных инициализирована")
    except Exception as e:
        logger.error(f"Ошибка инициализации БД: {e}")
else:
    logger.warning("База данных недоступна, используется заглушка")

def format_number(num: int) -> str:
    return f"{num:,}".replace(",", " ")

def calculate_level(shlep_count: int) -> dict:
    level = (shlep_count // 10) + 1
    current_progress = shlep_count % 10
    
    base_damage = 10
    damage_per_level = 0.5
    min_damage = int(base_damage + (level - 1) * damage_per_level)
    max_damage = min_damage + 5
    
    return {
        'level': level,
        'progress': current_progress * 10,
        'min_damage': min_damage,
        'max_damage': max_damage,
        'next_level_in': 10 - current_progress if current_progress < 10 else 0
    }

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not CONFIG_AVAILABLE:
        await update.message.reply_text(
            "Конфигурация бота не загружена. Обратитесь к администратору.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    user = update.effective_user
    chat = update.effective_chat
    
    welcome_text = f"""
👋 *Привет, {user.first_name}!*

Я — *Мишок Лысый*, виртуальный персонаж с идеально отполированной лысиной! 👴✨

*Что ты можешь делать:*
• Шлёпать меня по лысине командой `/shlep`
• Смотреть статистику шлёпков `/stats`
• Проверить свой уровень `/level`

*Для чатов:*
📊 /chat_stats — статистика чата
🏆 /chat_top — топ игроков чата
🗳️ /vote — голосование за шлёпок
⚔️ /duel — вызвать на дуэль
👑 /roles — роли в чате

*Для начала просто отправь:* `/shlep`
    """
    
    if chat.type == "private":
        keyboard = get_game_keyboard() if KEYBOARD_AVAILABLE else None
        await update.message.reply_text(
            welcome_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            f"👋 {user.first_name}, используй /shlep чтобы шлёпнуть Мишка!",
            reply_markup=get_inline_keyboard() if KEYBOARD_AVAILABLE else None,
            parse_mode=ParseMode.MARKDOWN
        )

async def mishok_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        MISHOK_INTRO,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_inline_keyboard() if KEYBOARD_AVAILABLE and update.effective_chat.type != "private" else None
    )

async def shlep_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        chat = update.effective_chat
        
        user_data = get_user_stats(user.id)
        if not user_data:
            username, user_count, last_shlep = (None, 0, None)
        else:
            username, user_count, last_shlep = user_data
        
        level_info = calculate_level(user_count)
        
        damage = random.randint(level_info['min_damage'], level_info['max_damage'])
        
        if damage < 15:
            reaction = "Легкий шлёпок! 😌"
        elif damage < 25:
            reaction = "Неплохо бьёшь! 😠"
        elif damage < 35:
            reaction = "Ой, крепко! 💢"
        else:
            reaction = "КОНТРА!!! 🚨"
        
        total_shleps, user_count, current_max_damage = add_shlep(
            user.id, 
            user.username or user.first_name,
            damage,
            chat.id if chat.type != "private" else None
        )
        
        if CACHE_AVAILABLE:
            await cache.delete("global_stats")
            await cache.delete(f"user_stats_{user.id}")
            await cache.delete("top_users_10")
            if chat.type != "private":
                await cache.delete(f"chat_stats_{chat.id}")
                await cache.delete(f"chat_top_{chat.id}")
        
        record_message = ""
        if damage > current_max_damage:
            record_message = f"\n🏆 *НОВЫЙ РЕКОРД!* 🏆\n"
            if chat.type != "private":
                await send_chat_notification(chat.id, user, "record", damage)
        
        message_lines = [
            f"{reaction}",
            record_message,
            f"💥 *Урон:* {damage} единиц",
            f"👤 *{user.first_name}*: {user_count} шлёпков",
            f"",
            f"🎯 *Уровень шлёпателя:* {level_info['level']}",
            f"📊 *Шлёпков до след. уровня:* {level_info['next_level_in']}",
            f"⚡ *Диапазон урона:* {level_info['min_damage']}-{level_info['max_damage']}",
            f"",
            f"📈 *Общее количество:* {format_number(total_shleps)}"
        ]
        
        if chat.type != "private":
            roles = get_user_roles(chat.id, user.id)
            if roles:
                message_lines.append(f"\n👑 *Роли:* {', '.join(roles)}")
        
        message_text = "\n".join(message_lines)
        
        keyboard = None
        if chat.type != "private":
            if KEYBOARD_AVAILABLE:
                keyboard = get_chat_quick_actions()
        else:
            if KEYBOARD_AVAILABLE:
                keyboard = get_inline_keyboard()
        
        await update.message.reply_text(
            message_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
        
        if chat.type != "private" and user_count % 50 == 0:
            await update.message.reply_text(
                f"🎉 *ЮБИЛЕЙ!* {user.first_name} достиг {user_count} шлёпков!",
                parse_mode=ParseMode.MARKDOWN
            )
        
    except Exception as e:
        logger.error(f"Ошибка команды /shlep: {e}")
        await update.message.reply_text("Произошла ошибка при шлёпке!")

async def shlep_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    chat = update.effective_chat
    
    user_data = get_user_stats(user.id)
    if not user_data:
        username, user_count, last_shlep = (None, 0, None)
    else:
        username, user_count, last_shlep = user_data
    
    level_info = calculate_level(user_count)
    
    damage = random.randint(level_info['min_damage'], level_info['max_damage'])
    
    if damage < 15:
        reaction = "Легкий шлёпок! 😌"
    elif damage < 25:
        reaction = "Неплохо бьёшь! 😠"
    elif damage < 35:
        reaction = "Ой, крепко! 💢"
    else:
        reaction = "КОНТРА!!! 🚨"
    
    total_shleps, user_count, current_max_damage = add_shlep(
        user.id, 
        user.username or user.first_name,
        damage,
        chat.id if chat.type != "private" else None
    )
    
    if CACHE_AVAILABLE:
        await cache.delete("global_stats")
        await cache.delete(f"user_stats_{user.id}")
        await cache.delete("top_users_10")
        if chat.type != "private":
            await cache.delete(f"chat_stats_{chat.id}")
            await cache.delete(f"chat_top_{chat.id}")
    
    record_message = ""
    if damage > current_max_damage:
        record_message = f"\n🏆 *НОВЫЙ РЕКОРД!* 🏆\n"
    
    message_lines = [
        f"{reaction}",
        record_message,
        f"💥 *Урон:* {damage} единиц",
        f"👤 *{user.first_name}*: {user_count} шлёпков",
        f"",
        f"🎯 *Уровень шлёпателя:* {level_info['level']}",
        f"📊 *Шлёпков до след. уровня:* {level_info['next_level_in']}",
        f"⚡ *Диапазон урона:* {level_info['min_damage']}-{level_info['max_damage']}",
        f"",
        f"📈 *Общее количество:* {format_number(total_shleps)}"
    ]
    
    message_text = "\n".join(message_lines)
    
    await query.edit_message_text(
        message_text,
        parse_mode=ParseMode.MARKDOWN
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        cache_key = "global_stats"
        cache_key_top = "top_users_10"
        
        if CACHE_AVAILABLE:
            cached_stats = await cache.get(cache_key)
            cached_top = await cache.get(cache_key_top)
        else:
            cached_stats = None
            cached_top = None
        
        if cached_stats:
            total_shleps, last_shlep, max_damage, max_damage_user, max_damage_date = cached_stats
        else:
            total_shleps, last_shlep, max_damage, max_damage_user, max_damage_date = get_stats()
            if CACHE_AVAILABLE:
                await cache.set(cache_key, (total_shleps, last_shlep, max_damage, max_damage_user, max_damage_date))
        
        if cached_top:
            top_users = cached_top
        else:
            top_users = get_top_users(10)
            if CACHE_AVAILABLE:
                await cache.set(cache_key_top, top_users)
        
        stats_text = f"""
📊 *СТАТИСТИКА ШЛЁПОВ*

👑 *РЕКОРДНЫЙ УДАР:*
   💥 {max_damage} единиц урона
   👤 {max_damage_user or 'Пока нет рекорда'}
   📅 {max_damage_date.strftime('%d.%m.%Y %H:%M') if max_damage_date else '—'}

🔢 *Всего шлёпков:* {format_number(total_shleps)}
⏰ *Последний шлёпок:* {last_shlep.strftime('%d.%m.%Y %H:%M') if last_shlep else "ещё не было"}
"""
        
        if top_users:
            stats_text += "\n🏆 *ТОП ШЛЁПАТЕЛЕЙ:*\n\n"
            for i, (username, count) in enumerate(top_users, 1):
                name = username or f"Аноним {i}"
                level = calculate_level(count)
                
                if level['level'] >= 50:
                    title = "👑 ЛЕГЕНДА"
                elif level['level'] >= 30:
                    title = "💎 МАСТЕР"
                elif level['level'] >= 20:
                    title = "⭐ ПРОФИ"
                elif level['level'] >= 10:
                    title = "🔥 АКТИВНЫЙ"
                else:
                    title = "👊 НОВИЧОК"
                
                stats_text += f"{i}. {title} {name}\n"
                stats_text += f"   📊 {format_number(count)} шлёпков | Ур. {level['level']}\n"
                stats_text += f"   ⚡ Урон: {level['min_damage']}-{level['max_damage']}\n\n"
        else:
            stats_text += "\n🏆 *Пока никто не шлёпал Мишка*"
        
        if CACHE_AVAILABLE:
            stats_text += f"\n_📊 Кэш: {cache.get_hit_rate():.1f}% попаданий_"
        
        await update.message.reply_text(
            stats_text,
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.error(f"Ошибка команды /stats: {e}")
        await update.message.reply_text("Ошибка загрузки статистики")

async def chat_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat = update.effective_chat
        
        if chat.type == "private":
            await update.message.reply_text("Эта команда работает только в группах!")
            return
        
        cache_key = f"chat_stats_{chat.id}"
        
        if CACHE_AVAILABLE:
            cached_stats = await cache.get(cache_key)
        else:
            cached_stats = None
        
        if cached_stats:
            chat_stats = cached_stats
        else:
            chat_stats = get_chat_stats(chat.id)
            if chat_stats and CACHE_AVAILABLE:
                await cache.set(cache_key, chat_stats)
        
        if not chat_stats:
            stats_text = f"""
📊 *СТАТИСТИКА ЧАТА*

В этом чате ещё не было шлёпков!
Используй /shlep чтобы стать первым! 🎯
"""
        else:
            stats_text = f"""
📊 *СТАТИСТИКА ЧАТА* #{chat.id}

👥 *Участников в статистике:* {chat_stats['total_users']}
👊 *Всего шлёпков в чате:* {format_number(chat_stats['total_shleps'])}
🏆 *Рекорд чата:* {chat_stats['max_damage']} урона
👑 *Рекордсмен:* {chat_stats['max_damage_user'] or 'Нет'}
📅 *Дата рекорда:* {chat_stats['max_damage_date'].strftime('%d.%m.%Y %H:%M') if chat_stats['max_damage_date'] else 'Нет'}
"""
            
            if chat_stats.get('active_today', 0) > 0:
                stats_text += f"\n🔥 *Активных сегодня:* {chat_stats['active_today']}"
            
            if chat_stats.get('last_activity'):
                last_active = (datetime.now() - chat_stats['last_activity']).seconds // 60
                stats_text += f"\n⏰ *Последняя активность:* {last_active} минут назад"
        
        await update.message.reply_text(
            stats_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_inline_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка команды chat_stats: {e}")
        await update.message.reply_text("Ошибка загрузки статистики чата")

async def chat_top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat = update.effective_chat
        
        if chat.type == "private":
            await update.message.reply_text("Эта команда работает только в группах!")
            return
        
        cache_key = f"chat_top_{chat.id}"
        
        if CACHE_AVAILABLE:
            cached_top = await cache.get(cache_key)
        else:
            cached_top = None
        
        if cached_top:
            chat_top = cached_top
        else:
            chat_top = get_chat_top_users(chat.id, limit=10)
            if CACHE_AVAILABLE:
                await cache.set(cache_key, chat_top)
        
        if not chat_top:
            await update.message.reply_text(
                "В этом чате пока никто не шлёпал Мишка! Будь первым!",
                reply_markup=get_inline_keyboard()
            )
            return
        
        top_text = "🏆 *ТОП ШЛЁПАТЕЛЕЙ ЧАТА:*\n\n"
        
        for i, (username, count) in enumerate(chat_top, 1):
            name = username or f"Игрок {i}"
            level_info = calculate_level(count)
            
            medal = ""
            if i == 1:
                medal = "🥇 "
            elif i == 2:
                medal = "🥈 "
            elif i == 3:
                medal = "🥉 "
            
            top_text += f"{medal}{i}. {name}\n"
            top_text += f"   📊 {format_number(count)} шлёпков | Ур. {level_info['level']}\n"
            top_text += f"   ⚡ Урон: {level_info['min_damage']}-{level_info['max_damage']}\n\n"
        
        await update.message.reply_text(
            top_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_inline_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка команды chat_top: {e}")
        await update.message.reply_text("Ошибка загрузки топа чата")

async def vote_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat = update.effective_chat
        user = update.effective_user
        
        if chat.type == "private":
            await update.message.reply_text("Голосования доступны только в группах!")
            return
        
        question = " ".join(context.args) if context.args else "Шлёпнуть Мишка?"
        
        vote_message = await update.message.reply_text(
            f"🗳️ *ГОЛОСОВАНИЕ*\n\n{question}\n\nГолосование длится 5 минут!",
            parse_mode=ParseMode.MARKDOWN
        )
        
        if DATABASE_AVAILABLE:
            vote_id = create_chat_vote(
                chat.id,
                vote_message.message_id,
                user.id,
                user.first_name,
                question
            )
            
            if vote_id and KEYBOARD_AVAILABLE:
                keyboard = get_chat_vote_keyboard(vote_id)
                await vote_message.edit_reply_markup(reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Ошибка команды /vote: {e}")
        await update.message.reply_text("Ошибка создания голосования")

async def duel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat = update.effective_chat
        user = update.effective_user
        
        if chat.type == "private":
            await update.message.reply_text("Дуэли доступны только в группах!")
            return
        
        if context.args:
            target_mention = ' '.join(context.args)
            
            duel_text = f"""
⚔️ *ВЫЗОВ НА ДУЭЛЬ!*

{user.first_name} вызывает {target_mention} на дуэль шлёпков!

📜 *Правила:*
• У вас есть 5 минут
• Кто сделает больше шлёпков - победил
• Победитель получает роль "⚔️ Победитель дуэли" на 24 часа

Для принятия вызова используй кнопку ниже!
"""
        else:
            duel_text = """
⚔️ *СИСТЕМА ДУЭЛЕЙ*

Используй `/duel @username` чтобы вызвать кого-то на дуэль!

📜 *Правила:*
• Дуэль длится 5 минут
• Побеждает тот, кто сделает больше шлёпков
• Победитель получает специальную роль
"""
        
        await update.message.reply_text(
            duel_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_chat_duel_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка команды /duel: {e}")
        await update.message.reply_text("Ошибка создания дуэли")

async def roles_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat = update.effective_chat
        user = update.effective_user
        
        if chat.type == "private":
            await update.message.reply_text("Роли доступны только в группах!")
            return
        
        user_roles = get_user_roles(chat.id, user.id)
        chat_roles_stats = get_chat_roles_stats(chat.id)
        
        roles_text = f"""
👑 *РОЛИ В ЧАТЕ*

*Твои роли:*
{', '.join(user_roles) if user_roles else 'Пока нет ролей'}

*Статистика ролей в чате:*
"""
        
        if chat_roles_stats:
            for role_type, count in chat_roles_stats.items():
                roles_text += f"• {role_type}: {count} чел.\n"
        else:
            roles_text += "В чате пока нет активных ролей"
        
        roles_text += "\n*Как получить роли:*"
        roles_text += "\n• 👑 Король шлёпков — быть топ-1 в чате"
        roles_text += "\n• 🎯 Самый меткий — нанести максимальный урон"
        roles_text += "\n• ⚡ Спринтер — сделать 10+ шлёпков за 5 минут"
        roles_text += "\n• 💪 Силач — нанести урон 40+ единиц"
        
        await update.message.reply_text(
            roles_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_chat_roles_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка команды /roles: {e}")
        await update.message.reply_text("Ошибка загрузки ролей")

async def level_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        chat = update.effective_chat
        cache_key = f"user_stats_{user.id}"
        
        if CACHE_AVAILABLE:
            cached_data = await cache.get(cache_key)
        else:
            cached_data = None
        
        if cached_data:
            username, user_count, last_shlep = cached_data
        else:
            user_data = get_user_stats(user.id)
            if not user_data:
                username, user_count, last_shlep = (None, 0, None)
            else:
                username, user_count, last_shlep = user_data
            
            if CACHE_AVAILABLE and user_count > 0:
                await cache.set(cache_key, (username, user_count, last_shlep))
        
        level_info = calculate_level(user_count)
        
        progress_bar = "█" * (level_info['progress'] // 10) + "░" * (10 - (level_info['progress'] // 10))
        
        text = f"""
🎯 *ТВОЙ УРОВЕНЬ ШЛЁПАТЕЛЯ*

👤 *Игрок:* {user.first_name}
📊 *Всего шлёпков:* {format_number(user_count)}
🎯 *Текущий уровень:* {level_info['level']}

{progress_bar} {level_info['progress']}%

⚡ *Твоя сила удара:* {level_info['min_damage']}-{level_info['max_damage']}
🎯 *До следующего уровня:* {level_info['next_level_in']} шлёпков

📈 *Следующий уровень даст:*
   +0.5 к минимальному урону
   +0.5 к максимальному урону
"""
        
        if chat.type != "private":
            user_roles = get_user_roles(chat.id, user.id)
            if user_roles:
                text += f"\n👑 *Твои роли в этом чате:* {', '.join(user_roles)}"
        
        if level_info['level'] >= 50:
            title = "👑 ЛЕГЕНДА ШЛЁПКОВ"
            advice = "Ты - мастер! Твой шлёпок слышен в соседних чатах!"
        elif level_info['level'] >= 30:
            title = "💎 МАСТЕР ШЛЁПКОВ"
            advice = "Отличный результат! Продолжай в том же духе!"
        elif level_info['level'] >= 20:
            title = "⭐ ПРОФЕССИОНАЛ"
            advice = "Хорошая работа! Уже чувствуется твоя сила!"
        elif level_info['level'] >= 10:
            title = "🔥 АКТИВНЫЙ ШЛЁПАТЕЛЬ"
            advice = "Продолжай шлёпать, чтобы увеличить свою силу!"
        else:
            title = "👊 НОВИЧОК"
            advice = "Шлёпай больше, чтобы стать сильнее!"
        
        text += f"\n🏆 *Твой титул:* {title}"
        text += f"\n💡 *{advice}*"
        
        if last_shlep:
            text += f"\n\n⏰ *Последний шлёпок:* {last_shlep.strftime('%d.%m.%Y %H:%M')}"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Ошибка команды /level: {e}")
        await update.message.reply_text("Ошибка загрузки информации об уровне")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🆘 *Помощь по командам*

*Основные команды:*
/start — Начало работы с ботом
/shlep — Шлёпнуть Мишка по лысине
/stats — Статистика и рекорды
/level — Твой уровень и сила
/mishok — Информация о Мишке

*Команды для чатов:*
/chat_stats — Статистика чата
/chat_top — Топ игроков чата
/vote [вопрос] — Голосование (5 мин)
/duel @username — Вызов на дуэль
/roles — Роли в чате

*В группах:* используй команды или inline-кнопки
"""
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    chat = update.effective_chat
    
    if chat.type != "private":
        return
    
    button_actions = {
        "👊 Шлёпнуть Мишка": shlep_command,
        "🎯 Уровень": level_command,
        "📊 Статистика": stats_command,
        "👴 О Мишке": mishok_info_command,
    }
    
    if text in button_actions:
        await button_actions[text](update, context)
    else:
        await update.message.reply_text(
            "Используй кнопки ниже или команды из /help",
            reply_markup=get_game_keyboard() if KEYBOARD_AVAILABLE else None
        )

async def group_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.new_chat_members:
        for member in update.message.new_chat_members:
            if member.id == context.bot.id:
                welcome_text = """
👴 *Мишок Лысый в чате!*

Теперь можно шлёпать меня по лысине прямо здесь!

*Основные команды:*
/shlep — шлёпнуть Мишка
/stats — статистика и рекорды
/level — уровень игрока

*Команды для чата:*
/chat_stats — статистика этого чата
/chat_top — топ игроков чата
/vote — голосование за шлёпок
/duel — вызвать на дуэль
/roles — роли в чате

*Используй кнопки под сообщениями!*
"""
                await update.message.reply_text(
                    welcome_text,
                    reply_markup=get_inline_keyboard() if KEYBOARD_AVAILABLE else None,
                    parse_mode=ParseMode.MARKDOWN
                )

async def send_chat_notification(chat_id: int, user, notification_type: str, value=None):
    """Отправка уведомлений в чат"""
    try:
        from telegram.constants import ParseMode
        
        notifications = {
            "record": f"🏆 *НОВЫЙ РЕКОРД ЧАТА!*\n\n{user.first_name} установил новый рекорд: {value} единиц урона!",
            "milestone": f"🎉 *ЮБИЛЕЙ!*\n\n{user.first_name} достиг {value} шлёпков!",
            "role": f"👑 *НОВАЯ РОЛЬ!*\n\n{user.first_name} получил роль: {value}",
            "duel": f"⚔️ *ДУЭЛЬ ЗАВЕРШЕНА!*\n\n{user.first_name} победил в дуэли!"
        }
        
        message = notifications.get(notification_type)
        if message:
            # В реальном коде здесь был бы вызов API Telegram
            # await context.bot.send_message(chat_id=chat_id, text=message, parse_mode=ParseMode.MARKDOWN)
            pass
            
    except Exception as e:
        logger.error(f"Ошибка отправки уведомления: {e}")

async def inline_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    chat = update.effective_chat
    user = update.effective_user
    
    try:
        if data == "shlep_mishok":
            await shlep_callback(update, context)
        elif data == "stats_inline":
            await stats_command(update, context)
        elif data == "level_inline":
            await level_command(update, context)
        elif data == "mishok_info":
            await mishok_info_command(update, context)
        elif data == "chat_stats":
            await chat_stats_command(update, context)
        elif data == "chat_top":
            await chat_top_command(update, context)
        elif data.startswith("vote_"):
            await handle_vote_callback(update, context, data)
        elif data.startswith("duel_"):
            await handle_duel_callback(update, context, data)
        elif data.startswith("role_"):
            await handle_role_callback(update, context, data)
        elif data.startswith("quick_"):
            await handle_quick_callback(update, context, data)
        elif data.startswith("back_"):
            await handle_back_callback(update, context, data)
        else:
            await query.message.reply_text("Эта функция скоро будет доступна!")
    except Exception as e:
        logger.error(f"Ошибка в inline_handler: {e}")
        await query.message.reply_text("Ошибка обработки команды")

async def handle_vote_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    query = update.callback_query
    
    if data.startswith("vote_yes_") or data.startswith("vote_no_"):
        parts = data.split("_")
        if len(parts) >= 3:
            vote_id = int(parts[2])
            vote_type = "yes" if parts[1] == "yes" else "no"
            
            if DATABASE_AVAILABLE:
                success = update_chat_vote(vote_id, query.from_user.id, vote_type)
                if success:
                    await query.answer("Ваш голос учтён!")
                else:
                    await query.answer("Ошибка голосования")
            else:
                await query.answer("Голосование временно недоступно")
    
    elif data.startswith("vote_results_"):
        parts = data.split("_")
        if len(parts) >= 3:
            vote_id = int(parts[2])
            
            if DATABASE_AVAILABLE:
                vote_info = get_chat_vote(vote_id)
                if vote_info:
                    total_votes = vote_info[6] + vote_info[7]
                    if total_votes > 0:
                        yes_percent = (vote_info[6] / total_votes) * 100
                        no_percent = (vote_info[7] / total_votes) * 100
                        
                        result_text = f"""
📊 *РЕЗУЛЬТАТЫ ГОЛОСОВАНИЯ*

{vote_info[5]}

👍 *За:* {vote_info[6]} ({yes_percent:.1f}%)
👎 *Против:* {vote_info[7]} ({no_percent:.1f}%)
👥 *Всего голосов:* {total_votes}
"""
                        
                        await query.message.edit_text(
                            result_text,
                            parse_mode=ParseMode.MARKDOWN
                        )
                    else:
                        await query.answer("Пока нет голосов")
                else:
                    await query.answer("Голосование не найдено")
            else:
                await query.answer("Результаты временно недоступны")

async def handle_duel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    query = update.callback_query
    
    if data == "duel_start":
        await duel_command(update, context)
    elif data == "duel_list":
        await query.message.reply_text("Список активных дуэлей скоро будет доступен!")
    elif data == "duel_my":
        await query.message.reply_text("Информация о ваших дуэлях скоро будет доступна!")
    elif data.startswith("duel_accept_"):
        await query.answer("Вызов принят! Дуэль началась!")
    elif data.startswith("duel_decline_"):
        await query.answer("Вызов отклонён")

async def handle_role_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    query = update.callback_query
    
    if data == "role_king":
        await query.message.reply_text("👑 *Король шлёпков*\n\nЭта роль присваивается игроку, который занимает первое место в топе чата. Действует 24 часа.")
    elif data == "role_accurate":
        await query.message.reply_text("🎯 *Самый меткий*\n\nЭта роль присваивается за нанесение максимального урона в чате. Действует 24 часа.")
    elif data == "role_sprinter":
        await query.message.reply_text("⚡ *Спринтер*\n\nЭта роль присваивается за 10+ шлёпков за 5 минут. Действует 12 часов.")
    elif data == "role_strong":
        await query.message.reply_text("💪 *Силач*\n\nЭта роль присваивается за урон 40+ единиц. Действует 24 часа.")
    elif data == "role_all":
        await roles_command(update, context)
    elif data == "role_my":
        chat = update.effective_chat
        user = update.effective_user
        
        user_roles = get_user_roles(chat.id, user.id)
        if user_roles:
            roles_text = f"👑 *Ваши роли в этом чате:*\n\n"
            for role in user_roles:
                roles_text += f"• {role}\n"
        else:
            roles_text = "У вас пока нет ролей в этом чате"
        
        await query.message.reply_text(roles_text, parse_mode=ParseMode.MARKDOWN)

async def handle_quick_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    query = update.callback_query
    
    if data == "quick_shlep":
        await shlep_callback(update, context)
    elif data == "quick_stats":
        await chat_stats_command(update, context)
    elif data == "quick_level":
        await level_command(update, context)
    elif data == "quick_daily_top":
        await query.message.reply_text("Топ дня скоро будет доступен!")
    elif data == "quick_vote":
        await vote_command(update, context)
    elif data == "quick_duel":
        await duel_command(update, context)

async def handle_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    query = update.callback_query
    
    if data == "back_main":
        await start_command(update, context)
    elif data == "back_chat":
        chat = update.effective_chat
        if chat.type != "private":
            await query.message.edit_text(
                "Главное меню чата",
                reply_markup=get_chat_quick_actions()
            )
    elif data == "back_roles":
        await roles_command(update, context)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} вызвал ошибку: {context.error}")
    
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "Произошла ошибка. Попробуй снова.",
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            pass

async def cache_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if CACHE_AVAILABLE:
            stats = cache.get_stats()
            text = f"""
📊 *СТАТИСТИКА КЭША*

• Всего записей: {stats['total_entries']}
• Попаданий: {stats['hits']}
• Промахов: {stats['misses']}
• Процент попаданий: {stats['hit_rate']:.1f}%
• TTL: {stats['ttl_seconds']} сек
"""
        else:
            text = "❌ Кэш система не загружена"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Ошибка команды cache_stats: {e}")

async def clear_cache_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if CACHE_AVAILABLE:
            await cache.clear()
            text = "✅ Кэш очищен"
        else:
            text = "❌ Кэш система не загружена"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Ошибка команды clear_cache: {e}")
