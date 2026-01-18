#!/usr/bin/env python3

import logging
import random
import sys
import os
import asyncio
from datetime import datetime

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
    from telegram import Update
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
        get_user_stats
    )
    DATABASE_AVAILABLE = True
except ImportError as e:
    logger.error(f"Ошибка импорта database: {e}")
    DATABASE_AVAILABLE = False
    def init_db(): logger.info("БД: заглушка init_db")
    def add_shlep(user_id, username, damage=0): 
        logger.info(f"БД: заглушка add_shlep для {user_id}")
        return (0, 0, 0)
    def get_stats(): return (0, None, 0, None, None)
    def get_top_users(limit=10): return []
    def get_user_stats(user_id): return (None, 0, None)

try:
    from keyboard import (
        get_game_keyboard, get_inline_keyboard,
        get_stats_keyboard, get_back_button
    )
    KEYBOARD_AVAILABLE = True
except ImportError as e:
    logger.error(f"Ошибка импорта keyboard: {e}")
    KEYBOARD_AVAILABLE = False
    def get_game_keyboard(): return None
    def get_inline_keyboard(): return None
    def get_stats_keyboard(): return None
    def get_back_button(*args, **kwargs): return None

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

*Система уровней:*
🎯 Уровень растёт с каждыми 10 шлёпками
⚡ Урон увеличивается с уровнем
🏆 Рекордный удар сохраняется

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
            damage
        )
        
        if CACHE_AVAILABLE:
            await cache.delete("global_stats")
            await cache.delete(f"user_stats_{user.id}")
            await cache.delete("top_users_10")
        
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
        
        keyboard = get_inline_keyboard() if KEYBOARD_AVAILABLE and chat.type != "private" else None
        await update.message.reply_text(
            message_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Ошибка команды /shlep: {e}")
        await update.message.reply_text("Произошла ошибка при шлёпке!")

async def shlep_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    
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
        damage
    )
    
    if CACHE_AVAILABLE:
        await cache.delete("global_stats")
        await cache.delete(f"user_stats_{user.id}")
        await cache.delete("top_users_10")
    
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
            logger.debug("Используем кэшированную глобальную статистику")
        else:
            total_shleps, last_shlep, max_damage, max_damage_user, max_damage_date = get_stats()
            if CACHE_AVAILABLE:
                await cache.set(cache_key, (total_shleps, last_shlep, max_damage, max_damage_user, max_damage_date))
                logger.debug("Сохранили глобальную статистику в кэш")
        
        if cached_top:
            top_users = cached_top
            logger.debug("Используем кэшированный топ пользователей")
        else:
            top_users = get_top_users(10)
            if CACHE_AVAILABLE:
                await cache.set(cache_key_top, top_users)
                logger.debug("Сохранили топ пользователей в кэш")
        
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

async def level_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        cache_key = f"user_stats_{user.id}"
        
        if CACHE_AVAILABLE:
            cached_data = await cache.get(cache_key)
        else:
            cached_data = None
        
        if cached_data:
            username, user_count, last_shlep = cached_data
            logger.debug(f"Используем кэшированные данные для пользователя {user.id}")
        else:
            user_data = get_user_stats(user.id)
            if not user_data:
                username, user_count, last_shlep = (None, 0, None)
            else:
                username, user_count, last_shlep = user_data
            
            if CACHE_AVAILABLE and user_count > 0:
                await cache.set(cache_key, (username, user_count, last_shlep))
                logger.debug(f"Сохранили данные пользователя {user.id} в кэш")
        
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

*Или используй кнопки под сообщениями!*
"""
                await update.message.reply_text(
                    welcome_text,
                    reply_markup=get_inline_keyboard() if KEYBOARD_AVAILABLE else None,
                    parse_mode=ParseMode.MARKDOWN
                )

async def inline_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    try:
        if data == "shlep_mishok":
            await shlep_callback(update, context)
        elif data == "stats_inline":
            await stats_command(update, context)
        elif data == "level_inline":
            await level_command(update, context)
        elif data == "mishok_info":
            await mishok_info_command(update, context)
        else:
            await query.message.reply_text("Эта функция скоро будет доступна!")
    except Exception as e:
        logger.error(f"Ошибка в inline_handler: {e}")
        await query.message.reply_text("Ошибка обработки команды")

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
    """Команда для админов: статистика кэша"""
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
    """Команда для админов: очистка кэша"""
    try:
        if CACHE_AVAILABLE:
            await cache.clear()
            text = "✅ Кэш очищен"
        else:
            text = "❌ Кэш система не загружена"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Ошибка команды clear_cache: {e}")
