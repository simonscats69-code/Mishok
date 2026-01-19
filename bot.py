import logging
import random
import sys
import os
from datetime import datetime
from functools import wraps
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.constants import ParseMode

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

_CONFIG = None
_DB = None
_KEYBOARD = None
_CACHE = None
_STATS = None

def get_config():
    global _CONFIG
    if _CONFIG is None:
        try:
            from config import BOT_TOKEN, MISHOK_REACTIONS, MISHOK_INTRO
            _CONFIG = {
                'BOT_TOKEN': BOT_TOKEN,
                'MISHOK_REACTIONS': MISHOK_REACTIONS,
                'MISHOK_INTRO': MISHOK_INTRO
            }
        except ImportError:
            _CONFIG = {
                'BOT_TOKEN': os.getenv("BOT_TOKEN", ""),
                'MISHOK_REACTIONS': ["Ой, больно! 😠", "Эй, не шлёпай! 👴💢"],
                'MISHOK_INTRO': "👴 *Мишок Лысый* - бот для шлёпков"
            }
    return _CONFIG

def get_db():
    global _DB
    if _DB is None:
        try:
            from database import (
                init_db, add_shlep, get_stats, get_top_users, 
                get_user_stats, get_chat_stats, get_chat_top_users,
                backup_database
            )
            _DB = {
                'init_db': init_db,
                'add_shlep': add_shlep,
                'get_stats': get_stats,
                'get_top_users': get_top_users,
                'get_user_stats': get_user_stats,
                'get_chat_stats': get_chat_stats,
                'get_chat_top_users': get_chat_top_users,
                'backup': backup_database
            }
            _DB['init_db']()
        except ImportError as e:
            logger.error(f"Ошибка импорта database: {e}")
            _DB = {
                'add_shlep': lambda *args: (0, 0, 0),
                'get_stats': lambda: (0, None, 0, None, None),
                'get_top_users': lambda limit=10: [],
                'get_user_stats': lambda uid: (f"Игрок_{uid}", 0, None),
                'get_chat_stats': lambda cid: None,
                'get_chat_top_users': lambda cid, limit=10: [],
                'backup': lambda: False
            }
    return _DB

def get_keyboard():
    global _KEYBOARD
    if _KEYBOARD is None:
        try:
            from keyboard import get_chat_quick_actions, get_inline_keyboard
            _KEYBOARD = {
                'chat_quick': get_chat_quick_actions,
                'inline': get_inline_keyboard
            }
        except ImportError:
            _KEYBOARD = {'chat_quick': lambda: None, 'inline': lambda: None}
    return _KEYBOARD

def get_cache():
    global _CACHE
    if _CACHE is None:
        try:
            from cache import cache
            _CACHE = cache
        except ImportError:
            class StubCache:
                async def get(self, key): return None
                async def set(self, key, value): pass
                async def delete(self, key): return False
                def get_stats(self): return {}
            _CACHE = StubCache()
    return _CACHE

def get_stats_module():
    global _STATS
    if _STATS is None:
        try:
            from statistics import (
                get_favorite_time, 
                get_comparison_stats,
                get_global_trends_info,
                format_daily_activity_chart,
                format_hourly_distribution_chart
            )
            _STATS = {
                'favorite_time': get_favorite_time,
                'comparison': get_comparison_stats,
                'global_trends': get_global_trends_info,
                'daily_chart': format_daily_activity_chart,
                'hourly_chart': format_hourly_distribution_chart
            }
        except ImportError as e:
            logger.error(f"Ошибка импорта statistics: {e}")
            _STATS = {
                'favorite_time': lambda uid: "📊 Статистика временно недоступна",
                'comparison': lambda uid: {'total_users': 0, 'avg_shleps': 0, 'percentile': 0, 'rank': 1},
                'global_trends': lambda: {},
                'daily_chart': lambda uid, days=7: "📊 Нет данных",
                'hourly_chart': lambda uid: "⏰ Нет данных"
            }
    return _STATS

def command_handler(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        try:
            message = update.message or (update.callback_query and update.callback_query.message)
            if not message:
                return
            
            result = await func(update, context, message, *args, **kwargs)
            return result
        except Exception as e:
            logger.error(f"Ошибка в {func.__name__}: {e}")
            try:
                message = update.message or (update.callback_query and update.callback_query.message)
                if message:
                    await message.reply_text("⚠️ Ошибка выполнения команды")
            except:
                pass
    return wrapper

def chat_only(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, message, *args, **kwargs):
        if update.effective_chat.type == "private":
            await message.reply_text("Эта команда работает только в группах!")
            return
        return await func(update, context, message, *args, **kwargs)
    return wrapper

def format_number(num):
    return f"{num:,}".replace(",", " ")

def calculate_level(shlep_count):
    if shlep_count <= 0:
        return {
            'level': 1,
            'progress': 0,
            'min_damage': 10,
            'max_damage': 15,
            'next_level_in': 10
        }
    
    level = (shlep_count // 10) + 1
    progress = (shlep_count % 10) * 10
    
    base_damage = 10
    damage_per_level = 0.5
    min_damage = int(base_damage + (level - 1) * damage_per_level)
    max_damage = min_damage + 5
    
    return {
        'level': min(level, 100),
        'progress': progress,
        'min_damage': min_damage,
        'max_damage': max_damage,
        'next_level_in': 10 - (shlep_count % 10) if (shlep_count % 10) < 10 else 0
    }

def get_damage_reaction(damage):
    if damage < 15: 
        return "Легкий шлёпок! 😌"
    if damage < 25: 
        return "Неплохо бьёшь! 😠"
    if damage < 35: 
        return "Ой, крепко! 💢"
    if damage < 45:
        return "Ай-яй-яй! 🤕"
    return "КОНТРА!!! 🚨"

def get_level_title(level):
    if level >= 50: 
        return ("👑 ЛЕГЕНДА ШЛЁПКОВ", "Ты - мастер! Твой шлёпок слышен в соседних чатах!")
    if level >= 30: 
        return ("💎 МАСТЕР ШЛЁПКОВ", "Отличный результат! Продолжай в том же духе!")
    if level >= 20: 
        return ("⭐ ПРОФЕССИОНАЛ", "Хорошая работа! Уже чувствуется твоя сила!")
    if level >= 10: 
        return ("🔥 АКТИВНЫЙ ШЛЁПАТЕЛЬ", "Продолжай шлёпать, чтобы увеличить свою силу!")
    return ("👊 НОВИЧОК", "Шлёпай больше, чтобы стать сильнее!")

def get_random_reaction():
    config = get_config()
    reactions = config.get('MISHOK_REACTIONS', [])
    if reactions:
        return random.choice(reactions)
    return "Ой! 👴"

@command_handler
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE, message):
    user = update.effective_user
    chat = update.effective_chat
    
    text = f"""👋 *Привет, {user.first_name}!*

Я — *Мишок Лысый*, виртуальный персонаж с идеально отполированной лысиной! 👴✨

*Теперь с продвинутой статистикой!* 📈
Детальный анализ твоей активности, сравнение с другими и глобальные тренды.

*Основные команды:*
/shlep — Шлёпнуть Мишка
/stats — Глобальная статистика
/level — Твой уровень
/my_stats — Детальная статистика
/trends — Глобальные тренды

*Для чатов:*
/chat_stats — Статистика чата
/chat_top — Топ игроков
/vote — Голосование
/duel — Дуэль

*Для начала:* /shlep"""
    
    keyboard = None
    if chat.type != "private":
        keyboard = get_keyboard()['inline']()
    
    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

@command_handler
async def shlep_command(update: Update, context: ContextTypes.DEFAULT_TYPE, message):
    db = get_db()
    cache = get_cache()
    user = update.effective_user
    chat = update.effective_chat
    
    username, user_count, _ = db['get_user_stats'](user.id)
    level_info = calculate_level(user_count)
    
    damage = random.randint(level_info['min_damage'], level_info['max_damage'])
    
    total_shleps, user_count, current_max_damage = db['add_shlep'](
        user.id, 
        user.username or user.first_name, 
        damage,
        chat.id if chat.type != "private" else None
    )
    
    await cache.delete("global_stats")
    await cache.delete(f"user_stats_{user.id}")
    if chat.type != "private":
        await cache.delete(f"chat_stats_{chat.id}")
    
    record_msg = f"\n🏆 *НОВЫЙ РЕКОРД!* 🏆\n" if damage > current_max_damage else ""
    
    level_info = calculate_level(user_count)
    title, _ = get_level_title(level_info['level'])
    
    text = f"""{get_random_reaction()}{record_msg}
💥 *Урон:* {damage} единиц
👤 *{user.first_name}*: {user_count} шлёпков

🎯 *Уровень {level_info['level']}* ({title})
📊 *До след. уровня:* {level_info['next_level_in']} шлёпков
⚡ *Диапазон урона:* {level_info['min_damage']}-{level_info['max_damage']}

📈 *Всего шлёпков в игре:* {format_number(total_shleps)}"""
    
    keyboard = None
    if chat.type != "private":
        keyboard = get_keyboard()['chat_quick']()
    
    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

@command_handler
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE, message):
    db = get_db()
    cache = get_cache()
    
    cache_key = "global_stats"
    cached = await cache.get(cache_key)
    
    if cached:
        total_shleps, last_shlep, max_damage, max_damage_user, max_damage_date = cached
    else:
        total_shleps, last_shlep, max_damage, max_damage_user, max_damage_date = db['get_stats']()
        await cache.set(cache_key, (total_shleps, last_shlep, max_damage, max_damage_user, max_damage_date))
    
    top_users = db['get_top_users'](10)
    
    text = f"""📊 *ГЛОБАЛЬНАЯ СТАТИСТИКА*

👑 *РЕКОРД УРОНА:* {max_damage} единиц
👤 *Рекордсмен:* {max_damage_user or 'Нет'}
📅 *Дата рекорда:* {max_damage_date.strftime('%d.%m.%Y %H:%M') if max_damage_date else '—'}

🔢 *Всего шлёпков:* {format_number(total_shleps)}
⏰ *Последний шлёпок:* {last_shlep.strftime('%d.%m.%Y %H:%M') if last_shlep else 'нет'}"""
    
    if top_users:
        text += "\n\n🏆 *ТОП ШЛЁПАТЕЛЕЙ:*\n"
        for i, (username, count) in enumerate(top_users[:5], 1):
            name = username or f"Игрок {i}"
            level = calculate_level(count)
            medal = ["🥇 ", "🥈 ", "🥉 "][i-1] if i <= 3 else ""
            
            text += f"\n{medal}{i}. {name}"
            text += f"\n   📊 {format_number(count)} | Ур. {level['level']}"
            text += f"\n   ⚡ Урон: {level['min_damage']}-{level['max_damage']}"
    
    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

@command_handler 
async def level_command(update: Update, context: ContextTypes.DEFAULT_TYPE, message):
    db = get_db()
    cache = get_cache()
    user = update.effective_user
    
    cache_key = f"user_stats_{user.id}"
    cached = await cache.get(cache_key)
    
    if cached:
        username, user_count, last_shlep = cached
    else:
        username, user_count, last_shlep = db['get_user_stats'](user.id)
        if user_count > 0:
            await cache.set(cache_key, (username, user_count, last_shlep))
    
    level_info = calculate_level(user_count)
    title, advice = get_level_title(level_info['level'])
    
    progress_bar_length = 10
    filled = min(level_info['progress'] // 10, progress_bar_length)
    empty = progress_bar_length - filled
    progress_bar = "█" * filled + "░" * empty
    
    text = f"""🎯 *ТВОЙ УРОВЕНЬ*

👤 *Игрок:* {user.first_name}
📊 *Шлёпков:* {format_number(user_count)}
🎯 *Уровень:* {level_info['level']} ({title})

{progress_bar} {level_info['progress']}%

⚡ *Урон:* {level_info['min_damage']}-{level_info['max_damage']}
🎯 *До след. уровня:* {level_info['next_level_in']} шлёпков

💡 *{advice}*"""
    
    if last_shlep:
        text += f"\n\n⏰ *Последний шлёпок:* {last_shlep.strftime('%d.%m.%Y %H:%M')}"
    
    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

@command_handler
async def my_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE, message):
    user = update.effective_user
    stats = get_stats_module()
    
    db = get_db()
    username, user_count, last_shlep = db['get_user_stats'](user.id)
    level_info = calculate_level(user_count)
    
    favorite_time = stats['favorite_time'](user.id)
    comparison = stats['comparison'](user.id)
    daily_chart = stats['daily_chart'](user.id, 7)
    
    text = f"""📈 *ТВОЯ ДЕТАЛЬНАЯ СТАТИСТИКА*

👤 *Игрок:* {user.first_name}
📊 *Всего шлёпков:* {format_number(user_count)}
🎯 *Уровень:* {level_info['level']}
⚡ *Диапазон урона:* {level_info['min_damage']}-{level_info['max_damage']}

{favorite_time}

📊 *Сравнение с другими:*
👥 *Всего игроков:* {comparison.get('total_users', 0)}
📈 *Среднее на игрока:* {comparison.get('avg_shleps', 0)}
🏆 *Твой ранг:* {comparison.get('rank', 1)}
📊 *Лучше чем:* {comparison.get('percentile', 0)}% игроков

📅 *Активность за неделю:*
{daily_chart}

*Используй /trends для глобальной статистики*"""
    
    if last_shlep:
        text += f"\n\n⏰ *Последний шлёпок:* {last_shlep.strftime('%d.%m.%Y %H:%M')}"
    
    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

@command_handler
async def trends_command(update: Update, context: ContextTypes.DEFAULT_TYPE, message):
    stats = get_stats_module()
    trends = stats['global_trends']()
    
    if not trends:
        await message.reply_text("📊 *ГЛОБАЛЬНЫЕ ТРЕНДЫ*\n\nДанные временно недоступны. Попробуйте позже.")
        return
    
    text = f"""📊 *ГЛОБАЛЬНЫЕ ТРЕНДЫ*

👥 *Активных за 24 часа:* {trends.get('active_users_24h', 0)}
👊 *Шлёпков за 24 часа:* {trends.get('shleps_24h', 0)}
📈 *Среднее на игрока:* {trends.get('avg_per_user_24h', 0)}

🔥 *Активных сегодня:* {trends.get('active_today', 0)}
⏰ *Текущий час:* {trends.get('current_hour', 0):02d}:00
👊 *Шлёпков в этом часу:* {trends.get('shleps_this_hour', 0)}
📈 *Прогноз на сегодня:* {trends.get('projected_today', 0)}"""

    db = get_db()
    top_users = db['get_top_users'](1)
    if top_users:
        top_user_id = 1
        hourly_chart = stats['hourly_chart'](top_user_id)
        text += f"\n\n⏰ *Распределение активности (топ-игрок):*\n{hourly_chart}"
    
    text += "\n\n*Используй /my_stats для персональной статистики*"
    
    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

@command_handler
async def detailed_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE, message):
    user = update.effective_user
    stats = get_stats_module()
    
    db = get_db()
    username, user_count, last_shlep = db['get_user_stats'](user.id)
    level_info = calculate_level(user_count)
    
    favorite_time = stats['favorite_time'](user.id)
    daily_chart = stats['daily_chart'](user.id, 14)
    hourly_chart = stats['hourly_chart'](user.id)
    
    text = f"""📊 *РАСШИРЕННАЯ СТАТИСТИКА*

👤 *Игрок:* {user.first_name}
📊 *Шлёпков:* {format_number(user_count)}
🎯 *Уровень:* {level_info['level']}

{favorite_time}

📅 *Активность за 2 недели:*
{daily_chart}

{hourly_chart}

*Команды статистики:*
/my_stats — Краткая статистика
/trends — Глобальные тренды
/stats — Общая статистика
/level — Уровень"""
    
    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

@command_handler
@chat_only
async def chat_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE, message):
    db = get_db()
    cache = get_cache()
    chat = update.effective_chat
    
    cache_key = f"chat_stats_{chat.id}"
    cached = await cache.get(cache_key)
    
    if cached:
        chat_stats = cached
    else:
        chat_stats = db['get_chat_stats'](chat.id)
        if chat_stats:
            await cache.set(cache_key, chat_stats)
    
    if not chat_stats:
        text = "📊 *СТАТИСТИКА ЧАТА*\n\nВ этом чате ещё не было шлёпков!\nИспользуй /shlep чтобы стать первым! 🎯"
    else:
        text = f"""📊 *СТАТИСТИКА ЧАТА*

👥 *Участников:* {chat_stats.get('total_users', 0)}
👊 *Всего шлёпков:* {format_number(chat_stats.get('total_shleps', 0))}
🏆 *Рекорд урона:* {chat_stats.get('max_damage', 0)} единиц
👑 *Рекордсмен:* {chat_stats.get('max_damage_user', 'Нет')}"""
        
        if chat_stats.get('active_today', 0) > 0:
            text += f"\n\n🔥 *Активных сегодня:* {chat_stats['active_today']}"
    
    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

@command_handler
@chat_only
async def chat_top_command(update: Update, context: ContextTypes.DEFAULT_TYPE, message):
    db = get_db()
    chat = update.effective_chat
    
    chat_top = db['get_chat_top_users'](chat.id, 10)
    
    if not chat_top:
        await message.reply_text("🏆 *ТОП ЧАТА*\n\nВ этом чате пока никто не шлёпал Мишка! Будь первым!")
        return
    
    text = "🏆 *ТОП ШЛЁПАТЕЛЕЙ ЧАТА:*\n\n"
    
    for i, (username, count) in enumerate(chat_top, 1):
        name = username or f"Игрок {i}"
        level = calculate_level(count)
        medal = ["🥇 ", "🥈 ", "🥉 "][i-1] if i <= 3 else ""
        
        text += f"{medal}{i}. {name}\n"
        text += f"   📊 {format_number(count)} | Ур. {level['level']}\n"
        text += f"   ⚡ Урон: {level['min_damage']}-{level['max_damage']}\n\n"
    
    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

@command_handler
@chat_only
async def vote_command(update: Update, context: ContextTypes.DEFAULT_TYPE, message):
    chat = update.effective_chat
    user = update.effective_user
    question = " ".join(context.args) if context.args else "Шлёпнуть Мишка?"
    
    await message.reply_text(
        f"🗳️ *ГОЛОСОВАНИЕ*\n\n{question}\n\nГолосование длится 5 минут!",
        parse_mode=ParseMode.MARKDOWN
    )

@command_handler
@chat_only
async def duel_command(update: Update, context: ContextTypes.DEFAULT_TYPE, message):
    user = update.effective_user
    
    if context.args:
        target = ' '.join(context.args)
        text = f"""⚔️ *ВЫЗОВ НА ДУЭЛЬ!*

{user.first_name} вызывает {target} на дуэль шлёпков!

📜 *Правила:*
• 5 минут на дуэль
• Побеждает тот, кто сделает больше шлёпков
• Победитель получает бонус"""
    else:
        text = """⚔️ *СИСТЕМА ДУЭЛЕЙ*

Используй `/duel @username` чтобы вызвать кого-то на дуэль!

📜 *Правила:*
• Дуэль длится 5 минут
• Побеждает тот, кто сделает больше шлёпков
• Победитель получает специальную роль"""
    
    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

@command_handler
@chat_only
async def roles_command(update: Update, context: ContextTypes.DEFAULT_TYPE, message):
    text = """👑 *РОЛИ В ЧАТЕ*

*Как получить роли:*
• 👑 Король шлёпков — быть топ-1 в чате
• 🎯 Самый меткий — нанести максимальный урон  
• ⚡ Спринтер — сделать 10+ шлёпков за 5 минут
• 💪 Силач — нанести урон 40+ единиц

*Используй /chat_top чтобы увидеть текущих лидеров!*"""
    
    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

@command_handler
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE, message):
    text = """🆘 *ПОМОЩЬ*

*Основные команды:*
/start — Начало работы
/shlep — Шлёпнуть Мишка  
/stats — Глобальная статистика
/level — Твой уровень
/my_stats — Детальная статистика
/detailed_stats — Расширенная статистика
/trends — Глобальные тренды
/mishok — О Мишке

*Для чатов:*
/chat_stats — Статистика чата
/chat_top — Топ игроков чата
/vote — Голосование
/duel — Дуэль
/roles — Роли в чате

*Теперь с сохранением прогресса!* 💾"""
    
    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

@command_handler
async def mishok_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE, message):
    config = get_config()
    await message.reply_text(config['MISHOK_INTRO'], parse_mode=ParseMode.MARKDOWN)

@command_handler
async def backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE, message):
    db = get_db()
    
    user = update.effective_user
    from config import ADMIN_ID
    
    if user.id != ADMIN_ID:
        await message.reply_text("⚠️ Эта команда только для администраторов!")
        return
    
    success = db['backup']()
    
    if success:
        await message.reply_text("✅ Бэкап базы данных создан успешно!")
    else:
        await message.reply_text("❌ Ошибка при создании бэкапа")

@command_handler
async def storage_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE, message):
    import os
    
    info = []
    info.append("📂 **Информация о хранилище:**")
    
    paths_to_check = [
        ("/root", "Основная папка"),
        ("/bothost", "Корень Bothost"),
        ("/bothost/storage", "Постоянное хранилище"),
        ("/bothost/storage/mishok_data.json", "Файл данных"),
        ("/bothost/storage/backups", "Папка бэкапов")
    ]
    
    for path, description in paths_to_check:
        exists = os.path.exists(path)
        size = 0
        if exists and os.path.isfile(path):
            size = os.path.getsize(path)
        elif exists and os.path.isdir(path):
            try:
                size = sum(os.path.getsize(os.path.join(path, f)) 
                          for f in os.listdir(path) if os.path.isfile(os.path.join(path, f)))
            except:
                size = 0
        
        status = "✅" if exists else "❌"
        size_str = f" ({size/1024:.1f} KB)" if size > 0 else ""
        info.append(f"{status} {description}: `{path}`{size_str}")
    
    info.append(f"\n💾 **Версия Бота:** Bothost Storage Ready")
    await message.reply_text("\n".join(info), parse_mode="Markdown")

async def inline_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, message):
    query = update.callback_query
    if not query:
        return
    
    await query.answer()
    data = query.data
    
    handlers = {
        "shlep_mishok": shlep_command,
        "stats_inline": stats_command,
        "level_inline": level_command,
        "mishok_info": mishok_info_command,
        "chat_stats": chat_stats_command,
        "chat_top": chat_top_command,
        "my_stats": my_stats_command,
        "trends": trends_command,
    }
    
    if data in handlers:
        await handlers[data](update, context)
    elif data.startswith("quick_"):
        await handle_quick_callback(update, context, data)
    else:
        await message.reply_text("⚙️ Эта функция в разработке")

async def handle_quick_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    query = update.callback_query
    if not query:
        return
    
    await query.answer()
    
    if data == "quick_shlep":
        await shlep_command(update, context)
    elif data == "quick_stats":
        await chat_stats_command(update, context)
    elif data == "quick_level":
        await level_command(update, context)
    elif data == "quick_my_stats":
        await my_stats_command(update, context)
    elif data == "quick_daily_top":
        await query.message.reply_text("📊 *ТОП ДНЯ*\n\nСобираем статистику...")
    elif data == "quick_vote":
        await query.message.reply_text("🗳️ *ГОЛОСОВАНИЕ*\n\nИспользуй /vote для создания голосования")
    elif data == "quick_duel":
        await query.message.reply_text("⚔️ *ДУЭЛЬ*\n\nИспользуй /duel @username для вызова")
    elif data == "quick_trends":
        await trends_command(update, context)

@command_handler
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, message):
    if update.effective_chat.type != "private":
        return
    
    text = update.message.text
    actions = {
        "👊 Шлёпнуть Мишка": shlep_command,
        "🎯 Уровень": level_command,
        "📊 Статистика": stats_command,
        "📈 Моя статистика": my_stats_command,
        "👴 О Мишке": mishok_info_command,
    }
    
    if text in actions:
        await actions[text](update, context)
    else:
        await message.reply_text("Используй кнопки ниже или команды из /help")

@command_handler
async def group_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE, message):
    if update.message.new_chat_members:
        for member in update.message.new_chat_members:
            if member.id == context.bot.id:
                text = """👴 *Мишок Лысый в чате!*

Теперь можно шлёпать меня по лысине прямо здесь!

*Основные команды:*
/shlep — шлёпнуть Мишка
/stats — статистика
/level — уровень
/my_stats — детальная статистика

*Для чата:*
/chat_stats — статистика чата
/chat_top — топ игроков
/vote — голосование
/duel — дуэль

*Прогресс сохраняется!* 💾"""
                
                await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Ошибка: {context.error}", exc_info=True)

def main():
    config = get_config()
    
    if not config['BOT_TOKEN']:
        logger.error("❌ BOT_TOKEN не установлен!")
        print("\n" + "="*50)
        print("ОШИБКА: BOT_TOKEN не найден!")
        print("1. Создайте файл .env")
        print("2. Добавьте: BOT_TOKEN=ваш_токен_от_BotFather")
        print("3. Или установите переменную окружения")
        print("="*50)
        sys.exit(1)
    
    app = Application.builder().token(config['BOT_TOKEN']).build()
    
    commands = [
        ("start", start_command),
        ("shlep", shlep_command),
        ("stats", stats_command),
        ("level", level_command),
        ("my_stats", my_stats_command),
        ("trends", trends_command),
        ("detailed_stats", detailed_stats_command),
        ("help", help_command),
        ("mishok", mishok_info_command),
        ("chat_stats", chat_stats_command),
        ("chat_top", chat_top_command),
        ("vote", vote_command),
        ("duel", duel_command),
        ("roles", roles_command),
        ("backup", backup_command),
        ("storage", storage_info_command),
    ]
    
    for name, handler in commands:
        app.add_handler(CommandHandler(name, handler))
    
    app.add_handler(CallbackQueryHandler(inline_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, group_welcome))
    app.add_error_handler(error_handler)
    
    logger.info("✅ Бот запущен с сохранением данных в Bothost Storage")
    print("\n" + "="*50)
    print("МИШОК ЛЫСЫЙ ЗАПУЩЕН НА BHOST!")
    print("="*50)
    print(f"• Данные сохраняются в: /bothost/storage/mishok_data.json")
    print(f"• Бэкапы создаются в: /bothost/storage/backups/")
    print(f"• Проверить хранилище: /storage")
    print(f"• Бот готов к работе!")
    print("="*50)
    
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
