#!/usr/bin/env python3

import logging
import random
import sys
import os
from datetime import datetime

os.environ['NUMPY_EXPERIMENTAL_ARRAY_FUNCTION'] = '0'

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
    logger.error(f"❌ Ошибка импорта telegram: {e}")
    TELEGRAM_AVAILABLE = False
    class Update: pass
    class ContextTypes: 
        class DEFAULT_TYPE: pass

try:
    from config import (
        BOT_TOKEN, MISHOK_REACTIONS, MISHOK_INTRO, STICKERS,
        ACHIEVEMENTS, DAILY_TASKS
    )
    CONFIG_AVAILABLE = True
except ImportError as e:
    logger.error(f"❌ Ошибка импорта config: {e}")
    CONFIG_AVAILABLE = False
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    MISHOK_REACTIONS = ["Ой, больно! 😠", "Эй, не шлёпай! 👴💢"]
    MISHOK_INTRO = "👴 *Мишок Лысый* - бот для шлёпков"
    STICKERS = {}
    ACHIEVEMENTS = {}
    DAILY_TASKS = []

try:
    from database import (
        init_db, add_shlep, get_stats, get_top_users, add_points, 
        get_user_points, get_user_stats
    )
    DATABASE_AVAILABLE = True
except ImportError as e:
    logger.error(f"❌ Ошибка импорта database: {e}")
    DATABASE_AVAILABLE = False
    def init_db(): logger.info("БД: заглушка init_db")
    def add_shlep(user_id, username): 
        logger.info(f"БД: заглушка add_shlep для {user_id}")
        return (0, 0)
    def get_stats(): return (0, None)
    def get_top_users(limit=10): return []
    def add_points(user_id, points): 
        logger.info(f"БД: заглушка add_points {points} для {user_id}")
        return 0
    def get_user_points(user_id): return 0
    def get_user_stats(user_id): return (None, 0, None)

try:
    from keyboard import (
        get_game_keyboard, get_inline_keyboard
    )
    KEYBOARD_AVAILABLE = True
except ImportError as e:
    logger.error(f"❌ Ошибка импорта keyboard: {e}")
    KEYBOARD_AVAILABLE = False
    def get_game_keyboard(): return None
    def get_inline_keyboard(): return None

SYSTEMS = {}

try:
    from levels import LevelSystem, MishokLevelSystem, SkillsSystem
    SYSTEMS['levels'] = LevelSystem()
    SYSTEMS['mishok_levels'] = MishokLevelSystem()
    SYSTEMS['skills'] = SkillsSystem()
    logger.info("✅ Система уровней загружена")
except Exception as e:
    logger.warning(f"⚠️ Система уровней не загружена: {e}")

try:
    from statistics import StatisticsSystem
    SYSTEMS['stats'] = StatisticsSystem()
    logger.info("✅ Система статистики загружена")
except Exception as e:
    logger.warning(f"⚠️ Система статистики не загружена: {e}")

try:
    from events import RecordsSystem, EventSystem
    SYSTEMS['records'] = RecordsSystem()
    SYSTEMS['events'] = EventSystem()
    logger.info("✅ Системы рекордов и событий загружены")
except Exception as e:
    logger.warning(f"⚠️ Системы рекордов/событий не загружены: {e}")

try:
    from goals import GlobalGoalsSystem
    SYSTEMS['goals'] = GlobalGoalsSystem()
    logger.info("✅ Система целей загружена")
except Exception as e:
    logger.warning(f"⚠️ Система целей не загружена: {e}")

try:
    from achievements import AchievementSystem
    from tasks import TaskSystem
    SYSTEMS['achievements'] = AchievementSystem()
    SYSTEMS['tasks'] = TaskSystem()
    logger.info("✅ Системы достижений и заданий загружены")
except Exception as e:
    logger.warning(f"⚠️ Системы достижений/заданий не загружены: {e}")

try:
    from utils import get_moscow_time, generate_animation
    UTILS_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ Утилиты не загружены")
    UTILS_AVAILABLE = False
    def get_moscow_time(): return datetime.now()
    def generate_animation(): return "✨"

if not TELEGRAM_AVAILABLE:
    logger.error("❌ Библиотека python-telegram-bot не установлена!")
    sys.exit(1)

if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN не установлен! Добавь его в .env файл")
    sys.exit(1)

if DATABASE_AVAILABLE:
    try:
        init_db()
        logger.info("✅ База данных инициализирована")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации БД: {e}")
else:
    logger.warning("⚠️ База данных недоступна, используется заглушка")

def format_number(num: int) -> str:
    return f"{num:,}".replace(",", " ")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not CONFIG_AVAILABLE:
        await update.message.reply_text(
            "❌ Конфигурация бота не загружена. Обратитесь к администратору.",
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
• Узнать информацию обо мне `/mishok`
• Прокачивать уровень и навыки `/level`
• Смотреть рекорды и достижения `/records`

*Игровые системы:* {len(SYSTEMS)} из 6 загружено

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
    await process_shlep(update, context, is_callback=False)

async def shlep_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await process_shlep(update, context, is_callback=True)

async def process_shlep(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback: bool):
    try:
        user = update.effective_user
        chat = update.effective_chat
        
        if 'tasks' in SYSTEMS:
            try:
                SYSTEMS['tasks'].init_user_tasks(user.id)
            except:
                pass
        
        total_shleps, user_count = add_shlep(user.id, user.username or user.first_name)
        
        event_multiplier = 1.0
        total_xp = 10
        level_info = {"level": 1, "progress": 0, "xp_current": 0, "xp_needed": 100}
        new_achievements = []
        completed_tasks = []
        new_strength_record = False
        slap_strength = random.uniform(10, 100)
        
        if 'events' in SYSTEMS:
            try:
                event_multiplier, active_events = SYSTEMS['events'].get_event_multiplier()
                total_xp = int(total_xp * event_multiplier)
            except Exception as e:
                logger.error(f"Ошибка системы событий: {e}")
        
        if 'levels' in SYSTEMS:
            try:
                level_info = SYSTEMS['levels'].add_xp(user.id, total_xp, "shlep")
            except Exception as e:
                logger.error(f"Ошибка системы уровней: {e}")
        
        if 'records' in SYSTEMS:
            try:
                new_strength_record, _ = SYSTEMS['records'].check_strength_record(user.id, slap_strength)
            except Exception as e:
                logger.error(f"Ошибка системы рекордов: {e}")
        
        if 'achievements' in SYSTEMS:
            try:
                new_achievements = SYSTEMS['achievements'].check_achievements(user.id, user_count)
            except Exception as e:
                logger.error(f"Ошибка системы достижений: {e}")
        
        if 'tasks' in SYSTEMS:
            try:
                completed_tasks = SYSTEMS['tasks'].update_task_progress(user.id)
            except Exception as e:
                logger.error(f"Ошибка системы заданий: {e}")
        
        if 'stats' in SYSTEMS:
            try:
                SYSTEMS['stats'].record_shlep(user.id)
            except Exception as e:
                logger.error(f"Ошибка системы статистики: {e}")
        
        if 'goals' in SYSTEMS:
            try:
                for goal in SYSTEMS['goals'].active_goals:
                    SYSTEMS['goals'].update_goal_progress(goal['id'])
            except Exception as e:
                logger.error(f"Ошибка системы целей: {e}")
        
        mishok_level_name = "Нежный Мишок"
        if 'mishok_levels' in SYSTEMS:
            try:
                mishok_level = SYSTEMS['mishok_levels'].get_mishok_level(total_shleps)
                mishok_level_name = mishok_level['name']
            except Exception as e:
                logger.error(f"Ошибка получения уровня Мишка: {e}")
        
        reaction = random.choice(MISHOK_REACTIONS) if MISHOK_REACTIONS else "Ой! 😠"
        
        message_lines = [
            f"{reaction}\n",
            f"📊 *Шлёпок №{format_number(total_shleps)}*",
            f"👤 *{user.first_name}*: {format_number(user_count)} шлёпков",
        ]
        
        if 'levels' in SYSTEMS:
            message_lines.append(f"🎯 Уровень: {level_info['level']} (+{total_xp} XP)")
            message_lines.append(f"📈 Прогресс: {level_info['progress']:.1f}%")
        
        message_lines.append(f"👴 *Уровень Мишка:* {mishok_level_name}")
        
        if event_multiplier != 1.0:
            message_lines.append(f"🎪 Множитель: x{event_multiplier:.1f}")
        
        if new_strength_record:
            message_lines.append(f"\n🏆 *НОВЫЙ РЕКОРД СИЛЫ!* {slap_strength:.1f} единиц!")
            add_points(user.id, 100)
        
        if new_achievements:
            for ach in new_achievements:
                message_lines.append(f"\n🎉 {ach['emoji']} *{ach['name']}*")
                add_points(user.id, ach.get('reward_points', 10))
        
        if completed_tasks:
            message_lines.append("\n📅 *Выполненные задания:*")
            for task in completed_tasks:
                message_lines.append(f"✅ {task['emoji']} {task['name']} (+{task['reward']} очков)")
                add_points(user.id, task['reward'])
        
        if random.random() < 0.1 and UTILS_AVAILABLE:
            try:
                animation = generate_animation()
                message_lines.append(f"\n{animation}")
            except:
                pass
        
        message_text = "\n".join(message_lines)
        
        if is_callback:
            await update.callback_query.edit_message_text(
                message_text,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            keyboard = get_inline_keyboard() if KEYBOARD_AVAILABLE and chat.type != "private" else None
            await update.message.reply_text(
                message_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard
            )
        
        if STICKERS and random.random() < 0.7:
            try:
                sticker_key = random.choice(list(STICKERS.keys()))
                if is_callback:
                    await update.callback_query.message.reply_sticker(STICKERS[sticker_key])
                else:
                    await update.message.reply_sticker(STICKERS[sticker_key])
            except Exception as e:
                logger.error(f"Ошибка отправки стикера: {e}")
    
    except Exception as e:
        logger.error(f"Критическая ошибка в process_shlep: {e}")
        try:
            if is_callback:
                await update.callback_query.message.reply_text("❌ Произошла ошибка при шлёпке!")
            else:
                await update.message.reply_text("❌ Произошла ошибка при шлёпке!")
        except:
            pass

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        total_shleps, last_shlep = get_stats()
        top_users = get_top_users(5)
        
        top_text_lines = []
        if top_users:
            for i, (username, count) in enumerate(top_users[:5], 1):
                name = username or f"Игрок {i}"
                top_text_lines.append(f"{i}. {name}: {format_number(count)} шлёпков")
        else:
            top_text_lines.append("Пока никто не шлёпал")
        
        top_text = "\n".join(top_text_lines)
        last_time = last_shlep.strftime("%d.%m.%Y %H:%M") if last_shlep else "никогда"
        
        stats_text = f"""
📊 *Статистика шлёпков*

🔢 *Всего шлёпков:* {format_number(total_shleps)}
⏰ *Последний шлёпок:* {last_time}

🏆 *Топ шлёпателей:*
{top_text}

*Глобальные системы:* {len(SYSTEMS)}/6 загружено
    """
        
        await update.message.reply_text(
            stats_text,
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.error(f"Ошибка команды /stats: {e}")
        await update.message.reply_text("❌ Ошибка загрузки статистики")

async def level_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if 'levels' not in SYSTEMS:
            await update.message.reply_text(
                "🎯 *Система уровней*\n\nСистема уровней временно недоступна. Продолжай шлёпать Мишка!",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        user = update.effective_user
        
        level_info = SYSTEMS['levels'].get_level_progress(user.id)
        points = get_user_points(user.id)
        
        text = f"""
🎯 *Твой уровень:* {level_info['level']}
⚡ *Опыт:* {format_number(level_info['xp_current'])}/{format_number(level_info['xp_needed'])}
📊 *Прогресс:* {level_info['progress']:.1f}%
💰 *Очков:* {format_number(points)}

*Следующий уровень через:* {format_number(level_info['next_level_in'])} XP
"""
        
        if 'skills' in SYSTEMS:
            try:
                user_skills = SYSTEMS['skills'].get_user_skills(user.id)
                if user_skills:
                    text += "\n*Твои навыки:*\n"
                    for skill_id, skill_info in user_skills.items():
                        text += f"• {skill_info['name']}: Ур. {skill_info['current_level']}\n"
            except:
                pass
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Ошибка команды /level: {e}")
        await update.message.reply_text("❌ Ошибка загрузки информации об уровне")

async def detailed_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if 'stats' not in SYSTEMS:
            await update.message.reply_text(
                "📈 *Детальная статистика*\n\nСистема детальной статистики временно недоступна.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        user = update.effective_user
        
        favorite_time = SYSTEMS['stats'].get_favorite_time(user.id)
        
        text = f"""
📈 *Детальная статистика*

{favorite_time}

*Статистика собирается автоматически*
*при каждом шлёпке командами:*
• `/shlep` — обычный шлёпок
• Inline-кнопка в группах
"""
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Ошибка команды /detailed_stats: {e}")
        await update.message.reply_text("❌ Ошибка загрузки статистики")

async def records_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if 'records' not in SYSTEMS:
            await update.message.reply_text(
                "🏆 *Рекорды*\n\nСистема рекордов временно недоступна.\nШлёпай больше, чтобы установить первые рекорды!",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        all_records = SYSTEMS['records'].get_all_records()
        
        if not all_records:
            text = "🏆 *Рекорды*\n\nПока нет ни одного рекорда. Будь первым!"
        else:
            text = "🏆 *Текущие рекорды:*\n\n"
            for record_type, record in all_records.items():
                timestamp = record.get('timestamp', datetime.now()).strftime("%d.%m.%Y")
                text += f"*{record['name']}:*\n"
                text += f"  👤 {record.get('username', 'Аноним')}\n"
                text += f"  🎯 {record['value']:.1f}\n"
                text += f"  📅 {timestamp}\n\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Ошибка команды /records: {e}")
        await update.message.reply_text("❌ Ошибка загрузки рекордов")

async def events_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if 'events' not in SYSTEMS:
            await update.message.reply_text(
                "🎪 *События*\n\nСистема событий временно недоступна.\nСкоро появятся специальные события с бонусами!",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        multiplier, active_events = SYSTEMS['events'].get_event_multiplier()
        
        text = "🎪 *События и бонусы*\n\n"
        
        if multiplier != 1.0:
            text += f"📈 *Текущий множитель опыта:* x{multiplier:.1f}\n\n"
        
        if active_events:
            text += "*🎉 Активные события:*\n"
            for event in active_events:
                text += f"\n*{event.get('name', 'Событие')}*\n"
                text += f"  {event.get('description', 'Бонусное событие')}\n"
                if 'ends_in' in event:
                    text += f"  ⏳ Заканчивается через: {event['ends_in']} мин\n"
        else:
            text += "Сейчас нет активных событий.\n\n"
            text += "События появляются в определённое время.\n"
            text += "Следи за обновлениями!"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Ошибка команды /events: {e}")
        await update.message.reply_text("❌ Ошибка загрузки событий")

async def goals_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if 'goals' not in SYSTEMS:
            await update.message.reply_text(
                "🎯 *Глобальные цели*\n\nСистема целей временно недоступна.\nСкоро появятся глобальные цели для всего сообщества!",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        global_stats = SYSTEMS['goals'].get_global_stats()
        total_shleps = global_stats.get('total_shleps', 0)
        progress_percent = (total_shleps / 1000000 * 100) if total_shleps > 0 else 0
        
        bar_length = 20
        filled = int(progress_percent / 100 * bar_length)
        progress_bar = "█" * filled + "░" * (bar_length - filled)
        
        text = f"""
🎯 *Глобальная цель: 1,000,000 шлёпков*

📊 *Прогресс:* {format_number(total_shleps)} / 1,000,000
{progress_bar} {progress_percent:.1f}%

👥 *Активных сегодня:* {global_stats.get('active_today', 0)}
🎯 *Шлёпков сегодня:* {format_number(global_stats.get('today_shleps', 0))}

*Присоединяйся к сообществу!*
Каждый шлёпок приближает нас к цели! 👊
"""
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Ошибка команды /goals: {e}")
        await update.message.reply_text(
            "🎯 *Цель сообщества:* 1,000,000 шлёпков!\nШлёпай больше, чтобы помочь достичь цели!",
            parse_mode=ParseMode.MARKDOWN
        )

async def upgrade_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if 'skills' not in SYSTEMS:
            await update.message.reply_text(
                "⚡ *Улучшение навыков*\n\nСистема навыков временно недоступна.\nСкоро ты сможешь прокачивать свои умения!",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        text = """
⚡ *Улучшение навыков*

*Доступные навыки:*
• Меткий шлёпок — увеличивает получаемый опыт
• Серия ударов — шанс на дополнительный шлёпок
• Критический удар — шанс на двойной опыт

*Скоро появится возможность улучшать навыки!*

А пока просто шлёпай Мишка командой `/shlep`
"""
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Ошибка команды /upgrade: {e}")
        await update.message.reply_text("❌ Ошибка загрузки информации о навыках")

async def achievements_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if 'achievements' not in SYSTEMS:
            await update.message.reply_text(
                "🏆 *Достижения*\n\nСистема достижений временно недоступна.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        user = update.effective_user
        achievements = SYSTEMS['achievements'].get_user_achievements(user.id)
        
        if not achievements:
            text = "🏆 *Твои достижения*\n\nПока нет достижений. Продолжай шлёпать!"
        else:
            text = "🏆 *Твои достижения:*\n\n"
            for ach in achievements:
                date = ach['achieved_at'].strftime("%d.%m.%Y") if 'achieved_at' in ach else ""
                text += f"{ach['emoji']} *{ach['name']}*\n"
                text += f"  {ach['description']}\n"
                if date:
                    text += f"  📅 Получено: {date}\n"
                text += "\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Ошибка команды /achievements: {e}")
        await update.message.reply_text("🏆 *Достижения*\n\nСистема достижений скоро будет доступна!")

async def tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if 'tasks' not in SYSTEMS:
            await update.message.reply_text(
                "📅 *Ежедневные задания*\n\nСистема заданий временно недоступна.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        user = update.effective_user
        tasks = SYSTEMS['tasks'].get_user_tasks(user.id)
        
        if not tasks:
            text = "📅 *Ежедневные задания*\n\nЗадания появятся после первого шлёпка!"
        else:
            text = "📅 *Ежедневные задания:*\n\n"
            for task in tasks:
                status = "✅ Выполнено" if task['completed'] else f"⏳ {task['progress']}/{task['required']}"
                text += f"{task['emoji']} *{task['name']}*\n"
                text += f"  {task['description']}\n"
                text += f"  {status}\n"
                text += f"  🎁 Награда: {task['reward']} очков\n\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Ошибка команды /tasks: {e}")
        await update.message.reply_text("📅 *Ежедневные задания*\n\nСистема заданий скоро будет доступна!")

async def rating_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        from tasks import RatingSystem
        rating_system = RatingSystem()
        
        daily = rating_system.get_daily_rating()
        weekly = rating_system.get_weekly_rating()
        
        user = update.effective_user
        daily_pos, daily_count = rating_system.get_user_daily_position(user.id)
        weekly_pos, weekly_count = rating_system.get_user_weekly_position(user.id)
        
        text = "🏆 *Рейтинги*\n\n"
        
        if daily:
            text += "*📊 Топ за день:*\n"
            for i, (uid, username, count) in enumerate(daily[:5], 1):
                name = username or f"Игрок {i}"
                text += f"{i}. {name}: {format_number(count)} шлёпков\n"
            text += "\n"
        
        if weekly:
            text += "*📈 Топ за неделю:*\n"
            for i, (uid, username, count) in enumerate(weekly[:5], 1):
                name = username or f"Игрок {i}"
                text += f"{i}. {name}: {format_number(count)} шлёпков\n"
            text += "\n"
        
        if daily_pos:
            text += f"*👤 Твоя позиция:*\n"
            text += f"• За день: #{daily_pos} ({format_number(daily_count)} шлёпков)\n"
            text += f"• За неделю: #{weekly_pos} ({format_number(weekly_count)} шлёпков)\n"
        else:
            text += "Сделай первый шлёпок, чтобы попасть в рейтинг!\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Ошибка команды /rating: {e}")
        await update.message.reply_text("🏆 *Рейтинги*\n\nСистема рейтингов скоро будет доступна!")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🆘 *Помощь по командам*

*Основные команды:*
/start — Начало работы с ботом
/shlep — Шлёпнуть Мишка по лысине
/stats — Общая статистика шлёпков
/mishok — Информация о Мишке

*Игровые системы:*
/level — Твой уровень и прогресс
/detailed_stats — Детальная статистика
/records — Рекорды бота
/events — Активные события
/goals — Глобальные цели
/upgrade — Улучшение навыков

*Дополнительные команды:*
/achievements — Достижения
/tasks — Ежедневные задания
/rating — Рейтинги игроков

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
        "📈 Статистика": detailed_stats_command,
        "📊 Статистика": stats_command,
        "🏆 Рекорды": records_command,
        "🎪 События": events_command,
        "🎯 Цели": goals_command,
        "⚡ Навыки": upgrade_command,
        "👴 О Мишке": mishok_info_command,
        "📅 Задания": tasks_command,
        "🏆 Рейтинг": rating_command,
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
/stats — статистика
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
        elif data == "records_inline":
            await records_command(update, context)
        elif data == "events_inline":
            await events_command(update, context)
        elif data == "goals_inline":
            await goals_command(update, context)
        elif data == "help_in_group":
            await help_command(update, context)
        else:
            await query.message.reply_text("🔄 Эта функция скоро будет доступна!")
    except Exception as e:
        logger.error(f"Ошибка в inline_handler: {e}")
        await query.message.reply_text("❌ Ошибка обработки команды")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} вызвал ошибку: {context.error}")
    
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "❌ Произошла ошибка. Попробуй снова.",
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            pass

def main():
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN не найден! Проверь .env файл.")
        return
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("shlep", shlep_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("mishok", mishok_info_command))
    application.add_handler(CommandHandler("help", help_command))
    
    application.add_handler(CommandHandler("level", level_command))
    application.add_handler(CommandHandler("detailed_stats", detailed_stats_command))
    application.add_handler(CommandHandler("records", records_command))
    application.add_handler(CommandHandler("events", events_command))
    application.add_handler(CommandHandler("goals", goals_command))
    application.add_handler(CommandHandler("upgrade", upgrade_command))
    
    application.add_handler(CommandHandler("achievements", achievements_command))
    application.add_handler(CommandHandler("tasks", tasks_command))
    application.add_handler(CommandHandler("rating", rating_command))
    
    application.add_handler(CallbackQueryHandler(shlep_callback, pattern="^shlep_mishok$"))
    application.add_handler(CallbackQueryHandler(inline_handler))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, group_welcome))
    
    application.add_error_handler(error_handler)
    
    logger.info("=" * 50)
    logger.info("🚀 ЗАПУСК БОТА 'МИШОК ЛЫСЫЙ'")
    logger.info("=" * 50)
    
    logger.info(f"📦 Загружено систем: {len(SYSTEMS)} из 6")
    if SYSTEMS:
        logger.info(f"✅ Системы: {', '.join(SYSTEMS.keys())}")
    else:
        logger.warning("⚠️ Ни одна система не загружена, бот работает в базовом режиме")
    
    if CONFIG_AVAILABLE:
        logger.info(f"✅ Конфигурация: {len(MISHOK_REACTIONS)} реакций, {len(STICKERS)} стикеров")
    else:
        logger.warning("⚠️ Конфигурация не загружена")
    
    if DATABASE_AVAILABLE:
        logger.info("✅ База данных доступна")
    else:
        logger.warning("⚠️ База данных недоступна, используется заглушка")
    
    logger.info("🤖 Бот готов к работе...")
    
    try:
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
    except Exception as e:
        logger.error(f"💥 КРИТИЧЕСКАЯ ОШИБКА: {e}")
        logger.error("Бот остановлен")

if __name__ == "__main__":
    main()
