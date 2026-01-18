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
    logger.error(f"Ошибка импорта telegram: {e}")
    TELEGRAM_AVAILABLE = False
    class Update: pass
    class ContextTypes: 
        class DEFAULT_TYPE: pass

try:
    from config import (
        BOT_TOKEN, MISHOK_REACTIONS, MISHOK_INTRO, STICKERS,
        ACHIEVEMENTS
    )
    CONFIG_AVAILABLE = True
except ImportError as e:
    logger.error(f"Ошибка импорта config: {e}")
    CONFIG_AVAILABLE = False
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    MISHOK_REACTIONS = ["Ой, больно! 😠", "Эй, не шлёпай! 👴💢"]
    MISHOK_INTRO = "👴 *Мишок Лысый* - бот для шлёпков"
    STICKERS = {}
    ACHIEVEMENTS = {}

try:
    from database import (
        init_db, add_shlep, get_stats, get_top_users, add_points, 
        get_user_points, get_user_stats
    )
    DATABASE_AVAILABLE = True
except ImportError as e:
    logger.error(f"Ошибка импорта database: {e}")
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
        get_game_keyboard, get_inline_keyboard, get_skills_keyboard,
        get_achievements_keyboard, get_stats_keyboard, get_goals_keyboard,
        get_upgrade_skill_keyboard, get_back_button, get_confirm_keyboard
    )
    KEYBOARD_AVAILABLE = True
except ImportError as e:
    logger.error(f"Ошибка импорта keyboard: {e}")
    KEYBOARD_AVAILABLE = False
    def get_game_keyboard(): return None
    def get_inline_keyboard(): return None
    def get_skills_keyboard(): return None
    def get_achievements_keyboard(): return None
    def get_stats_keyboard(): return None
    def get_goals_keyboard(): return None
    def get_upgrade_skill_keyboard(*args, **kwargs): return None
    def get_back_button(*args, **kwargs): return None
    def get_confirm_keyboard(*args, **kwargs): return None

SYSTEMS = {}

try:
    from levels import LevelSystem, MishokLevelSystem, SkillsSystem
    SYSTEMS['levels'] = LevelSystem()
    SYSTEMS['mishok_levels'] = MishokLevelSystem()
    SYSTEMS['skills'] = SkillsSystem()
    logger.info("Система уровней загружена")
except Exception as e:
    logger.warning(f"Система уровней не загружена: {e}")

try:
    from statistics import StatisticsSystem
    SYSTEMS['stats'] = StatisticsSystem()
    logger.info("Система статистики загружена")
except Exception as e:
    logger.warning(f"Система статистики не загружена: {e}")

try:
    from goals import GlobalGoalsSystem
    SYSTEMS['goals'] = GlobalGoalsSystem()
    logger.info("Система целей загружена")
except Exception as e:
    logger.warning(f"Система целей не загружена: {e}")

try:
    from achievements import AchievementSystem
    SYSTEMS['achievements'] = AchievementSystem()
    logger.info("Система достижений загружена")
except Exception as e:
    logger.warning(f"Система достижений не загружена: {e}")

try:
    from utils import get_moscow_time, generate_animation
    UTILS_AVAILABLE = True
except ImportError:
    logger.warning("Утилиты не загружены")
    UTILS_AVAILABLE = False
    def get_moscow_time(): return datetime.now()
    def generate_animation(): return "✨"

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
• Узнать информацию обо мне `/mishok`
• Прокачивать уровень и навыки `/level`
• Смотреть достижения `/achievements`
• Улучшать навыки `/upgrade`
• Смотреть цели сообщества `/goals`
• Детальная статистика `/detailed_stats`

*Игровые системы:* {len(SYSTEMS)} из 4 загружено

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
        
        total_shleps, user_count = add_shlep(user.id, user.username or user.first_name)
        
        base_xp = 10
        skill_effects = {'total_xp': base_xp, 'extra_shlep': False, 'critical': False}
        
        if 'skills' in SYSTEMS:
            try:
                skill_effects = SYSTEMS['skills'].apply_skill_effects(user.id, base_xp)
            except Exception as e:
                logger.error(f"Ошибка применения навыков: {e}")
        
        total_xp = skill_effects['total_xp']
        level_info = {"level": 1, "progress": 0, "xp_current": 0, "xp_needed": 100}
        new_achievements = []
        
        if 'levels' in SYSTEMS:
            try:
                level_info = SYSTEMS['levels'].add_xp(user.id, total_xp, "shlep")
            except Exception as e:
                logger.error(f"Ошибка системы уровней: {e}")
        
        if 'achievements' in SYSTEMS:
            try:
                new_achievements = SYSTEMS['achievements'].check_achievements(user.id, user_count)
            except Exception as e:
                logger.error(f"Ошибка системы достижений: {e}")
        
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
        mishok_xp_bonus = 1.0
        if 'mishok_levels' in SYSTEMS:
            try:
                mishok_level = SYSTEMS['mishok_levels'].get_mishok_level(total_shleps)
                mishok_level_name = mishok_level['name']
                mishok_xp_bonus = mishok_level['xp_bonus']
                total_xp = int(total_xp * mishok_xp_bonus)
            except Exception as e:
                logger.error(f"Ошибка получения уровня Мишка: {e}")
        
        reaction = random.choice(MISHOK_REACTIONS) if MISHOK_REACTIONS else "Ой! 😠"
        
        message_lines = [
            f"{reaction}\n",
            f"📊 *Шлёпок №{format_number(total_shleps)}*",
            f"👤 *{user.first_name}*: {format_number(user_count)} шлёпков",
        ]
        
        if 'levels' in SYSTEMS:
            xp_text = f"+{format_number(total_xp)} XP"
            if skill_effects.get('critical'):
                xp_text = f"💥 КРИТИЧЕСКИЙ! {xp_text}"
            message_lines.append(f"🎯 Уровень: {level_info['level']} ({xp_text})")
            message_lines.append(f"📈 Прогресс: {level_info['progress']:.1f}%")
        
        message_lines.append(f"👴 *Уровень Мишка:* {mishok_level_name}")
        
        if mishok_xp_bonus > 1.0:
            message_lines.append(f"✨ Бонус Мишка: +{int((mishok_xp_bonus - 1) * 100)}% XP")
        
        if skill_effects.get('accuracy_bonus', 0) > 0:
            message_lines.append(f"🎯 Бонус меткости: +{int(skill_effects['accuracy_bonus'] * 100)}% XP")
        
        if skill_effects.get('extra_shlep'):
            message_lines.append(f"👊 Серия ударов! Дополнительный шлёпок!")
        
        if new_achievements:
            for ach in new_achievements:
                message_lines.append(f"\n🎉 {ach['emoji']} *{ach['name']}*")
                add_points(user.id, ach.get('reward_points', 10))
        
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
        
        if skill_effects.get('extra_shlep'):
            await asyncio.sleep(1)
            extra_reaction = random.choice(["Ещё раз! 👊", "Двойной удар! 💥", "Комбо! 🎯"])
            await update.effective_message.reply_text(
                f"{extra_reaction}\nСерия ударов активирована! +{base_xp} XP",
                parse_mode=ParseMode.MARKDOWN
            )
    
    except Exception as e:
        logger.error(f"Критическая ошибка в process_shlep: {e}")
        try:
            if is_callback:
                await update.callback_query.message.reply_text("Произошла ошибка при шлёпке!")
            else:
                await update.message.reply_text("Произошла ошибка при шлёпке!")
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

*Глобальные системы:* {len(SYSTEMS)}/4 загружено
    """
        
        await update.message.reply_text(
            stats_text,
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.error(f"Ошибка команды /stats: {e}")
        await update.message.reply_text("Ошибка загрузки статистики")

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
                        if skill_info['current_level'] > 0:
                            text += f"• {skill_info['name']}: Ур. {skill_info['current_level']}\n"
            except Exception as e:
                logger.error(f"Ошибка получения навыков: {e}")
        
        keyboard = None
        if KEYBOARD_AVAILABLE:
            keyboard = get_back_button("main")
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Ошибка команды /level: {e}")
        await update.message.reply_text("Ошибка загрузки информации об уровне")

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
        activity_summary = SYSTEMS['stats'].get_activity_summary(user.id)
        comparison_stats = SYSTEMS['stats'].get_comparison_stats(user.id)
        
        text = f"""
📈 *Детальная статистика*

{favorite_time}

*Твоя активность:*
• Активных дней: {activity_summary['active_days']}
• Всего шлёпков: {format_number(activity_summary['total_shleps'])}
• Среднее в день: {activity_summary['daily_avg']}
• Рекордный день: {activity_summary['best_day_count']} шлёпков

*Сравнение с другими:*
• Всего игроков: {comparison_stats['total_users']}
• Среднее на игрока: {comparison_stats['avg_shleps']}
• Ты лучше, чем {comparison_stats['percentile']}% игроков
• Твой ранг: #{comparison_stats['rank']}
"""
        
        keyboard = get_stats_keyboard() if KEYBOARD_AVAILABLE else None
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Ошибка команды /detailed_stats: {e}")
        await update.message.reply_text("Ошибка загрузки статистики")

async def goals_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if 'goals' not in SYSTEMS:
            await update.message.reply_text(
                "🎯 *Глобальные цели*\n\nСистема целей временно недоступна.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        user = update.effective_user
        global_stats = SYSTEMS['goals'].get_global_stats()
        user_contributions = SYSTEMS['goals'].get_user_contributions(user.id)
        active_goals = SYSTEMS['goals'].get_active_goals_with_progress()
        
        text = f"""
🎯 *Глобальные цели сообщества*

*Общая статистика:*
• Всего шлёпков: {format_number(global_stats['total_shleps'])}
• Активных сегодня: {global_stats['active_today']}
• Шлёпков сегодня: {format_number(global_stats['today_shleps'])}
• Активных целей: {global_stats['active_goals']}
• Завершённых целей: {global_stats['completed_goals']}

*Твой вклад:*
"""
        
        if user_contributions:
            for contrib in user_contributions:
                text += f"\n• {contrib['name']}: {contrib['user_contribution']} шлёпков ({contrib['user_percentage']:.1f}%)"
        else:
            text += "\nПока нет вклада в цели"
        
        if active_goals:
            text += "\n\n*Активные цели:*"
            for goal in active_goals[:3]:
                progress_bar = "█" * int(goal['progress_percent'] / 5) + "░" * (20 - int(goal['progress_percent'] / 5))
                text += f"\n\n{goal['name']}"
                text += f"\n{progress_bar} {goal['progress_percent']:.1f}%"
                text += f"\n{format_number(goal['current'])} / {format_number(goal['target'])}"
                if goal.get('days_left') is not None:
                    text += f"\nОсталось дней: {goal['days_left']}"
        
        keyboard = get_goals_keyboard() if KEYBOARD_AVAILABLE else None
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
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
                "⚡ *Улучшение навыков*\n\nСистема навыков временно недоступна.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        user = update.effective_user
        points = get_user_points(user.id)
        user_skills = SYSTEMS['skills'].get_user_skills(user.id)
        
        text = f"""
⚡ *Улучшение навыков*

*Твои очки:* {format_number(points)}

*Доступные навыки:*
"""
        
        for skill_id, skill_info in user_skills.items():
            level_text = f"Ур. {skill_info['current_level']}/{skill_info['max_level']}"
            if skill_info['can_upgrade']:
                cost_text = f"💰 {skill_info['next_cost']} очков"
                text += f"\n• {skill_info['name']} ({level_text}) - {cost_text}"
            else:
                text += f"\n• {skill_info['name']} ({level_text}) - ⭐ Макс. уровень"
        
        text += "\n\n*Используй кнопки ниже для просмотра и улучшения навыков*"
        
        keyboard = get_skills_keyboard() if KEYBOARD_AVAILABLE else None
            
        await update.message.reply_text(
            text, 
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Ошибка команды /upgrade: {e}")
        await update.message.reply_text("Ошибка загрузки информации о навыках")

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
        achievements_progress = SYSTEMS['achievements'].get_achievements_progress(user.id)
        next_achievement = SYSTEMS['achievements'].get_next_achievement(
            get_user_stats(user.id)[1] if get_user_stats(user.id) else 0
        )
        
        if not achievements:
            text = "🏆 *Твои достижения*\n\nПока нет достижений. Продолжай шлёпать!"
        else:
            text = f"🏆 *Твои достижения:* {len(achievements)}/{len(achievements_progress)}\n\n"
            for ach in achievements[:5]:
                date = ach['achieved_at'].strftime("%d.%m.%Y") if 'achieved_at' in ach else ""
                text += f"{ach['emoji']} *{ach['name']}*\n"
                text += f"  {ach['description']}\n"
                if date:
                    text += f"  📅 Получено: {date}\n"
                text += "\n"
        
        if next_achievement:
            text += f"\n🎯 *Следующее достижение:*\n"
            text += f"{next_achievement['emoji']} *{next_achievement['name']}*\n"
            text += f"Осталось шлёпков: {next_achievement['remaining']}\n"
        
        keyboard = get_achievements_keyboard() if KEYBOARD_AVAILABLE else None
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Ошибка команды /achievements: {e}")
        await update.message.reply_text("Система достижений скоро будет доступна!")

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
/goals — Глобальные цели
/upgrade — Улучшение навыков
/achievements — Достижения

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
        "🎯 Цели": goals_command,
        "⚡ Навыки": upgrade_command,
        "👴 О Мишке": mishok_info_command,
        "🏆 Достижения": achievements_command,
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
        elif data == "goals_inline":
            await goals_command(update, context)
        elif data == "help_in_group":
            await help_command(update, context)
        elif data.startswith("skill_"):
            await handle_skill_callback(update, context, data)
        elif data.startswith("achievement_"):
            await handle_achievement_callback(update, context, data)
        elif data.startswith("upgrade_"):
            await handle_upgrade_callback(update, context, data)
        elif data.startswith("back_"):
            await handle_back_callback(update, context, data)
        elif data.startswith("stats_"):
            await handle_stats_callback(update, context, data)
        elif data.startswith("goals_"):
            await handle_goals_callback(update, context, data)
        else:
            await query.message.reply_text("Эта функция скоро будет доступна!")
    except Exception as e:
        logger.error(f"Ошибка в inline_handler: {e}")
        await query.message.reply_text("Ошибка обработки команды")

async def handle_skill_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    query = update.callback_query
    
    if data == "skill_accurate_info":
        text = """
🎯 *Меткий шлёпок*

*Эффект:* Увеличивает получаемый опыт на 10% за уровень
*Макс. уровень:* 10
*Текущий уровень:* 0

*Стоимость улучшения:*
1 уровень: 50 очков
2 уровень: 100 очков
3 уровень: 200 очков
4 уровень: 400 очков
5 уровень: 800 очков
6 уровень: 1600 очков
7 уровень: 3200 очков
8 уровень: 6400 очков
9 уровень: 12800 очков
10 уровень: 25600 очков
"""
        keyboard = get_back_button("skills")
        await query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    elif data == "skill_combo_info":
        text = """
👊 *Серия ударов*

*Эффект:* Шанс сделать дополнительный шлёпок (5% за уровень)
*Макс. уровень:* 5
*Текущий уровень:* 0

*Стоимость улучшения:*
1 уровень: 100 очков
2 уровень: 250 очков
3 уровень: 500 очков
4 уровень: 1000 очков
5 уровень: 2000 очков
"""
        keyboard = get_back_button("skills")
        await query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    elif data == "skill_critical_info":
        text = """
💥 *Критический удар*

*Эффект:* Шанс на критический удар (2x опыт, 5% за уровень)
*Макс. уровень:* 5
*Текущий уровень:* 0

*Стоимость улучшения:*
1 уровень: 200 очков
2 уровень: 500 очков
3 уровень: 1000 очков
4 уровень: 2000 очков
5 уровень: 5000 очков
"""
        keyboard = get_back_button("skills")
        await query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    elif data == "skills_cost":
        text = """
💰 *Стоимость улучшения навыков*

*Меткий шлёпок:*
Уровень 1: 50 очков
Уровень 2: 100 очков
Уровень 3: 200 очков
...
Уровень 10: 25600 очков

*Серия ударов:*
Уровень 1: 100 очков
Уровень 2: 250 очков
...
Уровень 5: 2000 очков

*Критический удар:*
Уровень 1: 200 очков
Уровень 2: 500 очков
...
Уровень 5: 5000 очков
"""
        keyboard = get_back_button("skills")
        await query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    elif data == "upgrade_skill_menu":
        await upgrade_command(update, context)
    elif data == "my_skills":
        user = update.effective_user
        user_skills = SYSTEMS['skills'].get_user_skills(user.id)
        
        text = "⚡ *Твои навыки:*\n\n"
        for skill_id, skill_info in user_skills.items():
            effect_text = ""
            if skill_id == 'accurate_slap':
                effect_text = f"+{int(skill_info['current_effect'] * 100)}% XP"
            elif skill_id == 'combo_slap':
                effect_text = f"{int(skill_info['current_effect'] * 100)}% шанс доп. шлёпка"
            elif skill_id == 'critical_slap':
                effect_text = f"{int(skill_info['current_effect'] * 100)}% шанс крит. удара"
            
            text += f"{skill_info['name']}\n"
            text += f"Уровень: {skill_info['current_level']}/{skill_info['max_level']}\n"
            text += f"Эффект: {effect_text}\n\n"
        
        keyboard = get_back_button("skills")
        await query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    else:
        await query.message.reply_text("Информация о навыке скоро будет доступна!")

async def handle_upgrade_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    query = update.callback_query
    
    if data.startswith("upgrade_"):
        skill_id = data.replace("upgrade_", "")
        user = update.effective_user
        
        success, message = SYSTEMS['skills'].upgrade_skill(user.id, skill_id)
        
        if success:
            text = f"✅ {message}"
            points = get_user_points(user.id)
            text += f"\n\n💰 Осталось очков: {format_number(points)}"
        else:
            text = f"❌ {message}"
        
        keyboard = get_back_button("skills")
        await query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

async def handle_achievement_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    query = update.callback_query
    
    if data == "my_achievements":
        await achievements_command(update, context)
    elif data == "next_achievement":
        user = update.effective_user
        user_stats = get_user_stats(user.id)
        current_count = user_stats[1] if user_stats else 0
        next_achievement = SYSTEMS['achievements'].get_next_achievement(current_count)
        
        if next_achievement:
            text = f"""
🎯 *Следующее достижение:*

{next_achievement['emoji']} *{next_achievement['name']}*
{next_achievement['description']}

*Прогресс:* {current_count}/{next_achievement['threshold']}
*Осталось:* {next_achievement['remaining']} шлёпков
*Награда:* {next_achievement.get('reward_points', 10)} очков
"""
        else:
            text = "🎉 *Поздравляю!* Ты достиг всех доступных достижений!"
        
        keyboard = get_back_button("achievements")
        await query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    elif data == "achievements_progress":
        user = update.effective_user
        achievements_progress = SYSTEMS['achievements'].get_achievements_progress(user.id)
        
        text = "🏆 *Прогресс по достижениям:*\n\n"
        for ach in achievements_progress:
            progress_bar = "█" * int(ach['progress_percent'] / 10) + "░" * (10 - int(ach['progress_percent'] / 10))
            status = "✅" if ach['achieved'] else "⏳"
            text += f"{status} {ach['emoji']} {ach['name']}\n"
            if not ach['achieved']:
                text += f"{progress_bar} {ach['current']}/{ach['threshold']}\n\n"
            else:
                text += "Завершено!\n\n"
        
        keyboard = get_back_button("achievements")
        await query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    elif data == "achievements_stats":
        user = update.effective_user
        achievements = SYSTEMS['achievements'].get_user_achievements(user.id)
        achievements_progress = SYSTEMS['achievements'].get_achievements_progress(user.id)
        
        total_achievements = len(achievements_progress)
        completed = len(achievements)
        percentage = (completed / total_achievements * 100) if total_achievements > 0 else 0
        
        text = f"""
📊 *Статистика достижений*

Всего достижений: {total_achievements}
Завершено: {completed} ({percentage:.1f}%)
Осталось: {total_achievements - completed}

*Награды получено:*
"""
        
        total_points = 0
        for ach in achievements:
            total_points += ach.get('reward_points', 0)
        
        text += f"Очков: {format_number(total_points)}"
        
        keyboard = get_back_button("achievements")
        await query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    else:
        await query.message.reply_text("Информация о достижении скоро будет доступна!")

async def handle_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    query = update.callback_query
    
    if data == "activity_stats":
        user = update.effective_user
        activity_summary = SYSTEMS['stats'].get_activity_summary(user.id)
        
        text = f"""
📊 *Активность*

Активных дней: {activity_summary['active_days']}
Всего шлёпков: {format_number(activity_summary['total_shleps'])}
Среднее в день: {activity_summary['daily_avg']}
"""
        
        if activity_summary['best_day']:
            text += f"Рекордный день: {activity_summary['best_day'].strftime('%d.%m.%Y')} - {activity_summary['best_day_count']} шлёпков\n"
        
        if activity_summary['last_active']:
            text += f"Последняя активность: {activity_summary['last_active'].strftime('%d.%m.%Y %H:%M')}"
        
        keyboard = get_back_button("stats")
        await query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    elif data == "hourly_stats":
        user = update.effective_user
        hourly_dist = SYSTEMS['stats'].get_hourly_distribution(user.id, 30)
        
        text = "⏰ *Распределение по часам (за 30 дней):*\n\n"
        
        max_count = max(hourly_dist) if hourly_dist else 0
        for hour in range(24):
            count = hourly_dist[hour]
            if max_count > 0:
                bar_length = int(count / max_count * 20)
                bar = "█" * bar_length + "░" * (20 - bar_length)
            else:
                bar = "░" * 20
            
            text += f"{hour:02d}:00 {bar} {count}\n"
        
        keyboard = get_back_button("stats")
        await query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    elif data == "global_stats":
        if 'stats' in SYSTEMS:
            global_trends = SYSTEMS['stats'].get_global_trends()
            
            text = f"""
🌐 *Глобальная статистика*

*За последние 24 часа:*
Активных игроков: {global_trends['active_users_24h']}
Всего шлёпков: {global_trends['shleps_24h']}
Активных сегодня: {global_trends['active_today']}

*Текущий час ({global_trends['current_hour']}:00):*
Шлёпков в этом часу: {global_trends['shleps_this_hour']}
"""
        else:
            text = "Глобальная статистика временно недоступна"
        
        keyboard = get_back_button("stats")
        await query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    elif data == "compare_stats":
        user = update.effective_user
        comparison_stats = SYSTEMS['stats'].get_comparison_stats(user.id)
        
        text = f"""
👥 *Сравнение с другими игроками*

Всего игроков: {comparison_stats['total_users']}
Среднее на игрока: {comparison_stats['avg_shleps']} шлёпков
Ты лучше, чем {comparison_stats['percentile']}% игроков
Твой ранг: #{comparison_stats['rank']}
"""
        
        if comparison_stats['percentile'] >= 90:
            text += "\n🎖 Ты в топ-10% игроков! Отличный результат!"
        elif comparison_stats['percentile'] >= 75:
            text += "\n🏅 Ты в топ-25% игроков! Хорошая работа!"
        elif comparison_stats['percentile'] >= 50:
            text += "\n🎯 Ты лучше среднего! Продолжай в том же духе!"
        
        keyboard = get_back_button("stats")
        await query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    elif data == "activity_chart":
        text = "📈 *График активности*\n\nФункция графиков скоро будет доступна!\nА пока используй другие виды статистики."
        keyboard = get_back_button("stats")
        await query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    elif data == "goals_stats":
        await goals_command(update, context)
    else:
        await query.message.reply_text("Эта функция статистики скоро будет доступна!")

async def handle_goals_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    query = update.callback_query
    
    if data == "active_goals":
        if 'goals' in SYSTEMS:
            active_goals = SYSTEMS['goals'].get_active_goals_with_progress()
            
            if not active_goals:
                text = "🎯 *Активные цели*\n\nНа данный момент нет активных целей."
            else:
                text = "🎯 *Активные цели:*\n\n"
                for goal in active_goals:
                    progress_bar = "█" * int(goal['progress_percent'] / 5) + "░" * (20 - int(goal['progress_percent'] / 5))
                    text += f"{goal['name']}\n"
                    text += f"{goal['description']}\n"
                    text += f"{progress_bar} {goal['progress_percent']:.1f}%\n"
                    text += f"{format_number(goal['current'])} / {format_number(goal['target'])}\n"
                    if goal.get('days_left') is not None:
                        text += f"⏳ Осталось дней: {goal['days_left']}\n"
                    text += f"🏆 Награда: {goal['reward']['value']} {goal['reward']['type']}\n\n"
        else:
            text = "Система целей временно недоступна"
        
        keyboard = get_back_button("goals")
        await query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    elif data == "completed_goals":
        if 'goals' in SYSTEMS:
            completed_goals = SYSTEMS['goals'].completed_goals
            
            if not completed_goals:
                text = "🏆 *Завершённые цели*\n\nПока нет завершённых целей."
            else:
                text = "🏆 *Завершённые цели:*\n\n"
                for goal in completed_goals[:5]:
                    text += f"{goal['name']}\n"
                    text += f"Завершено: {goal.get('completed_at', '').strftime('%d.%m.%Y') if goal.get('completed_at') else 'неизвестно'}\n"
                    text += f"Награда: {goal['reward']['value']} {goal['reward']['type']}\n\n"
        else:
            text = "Система целей временно недоступна"
        
        keyboard = get_back_button("goals")
        await query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    elif data == "my_contributions":
        user = update.effective_user
        if 'goals' in SYSTEMS:
            contributions = SYSTEMS['goals'].get_user_contributions(user.id)
            
            if not contributions:
                text = "📊 *Мой вклад в цели*\n\nПока нет активного вклада в цели сообщества."
            else:
                text = "📊 *Мой вклад в цели:*\n\n"
                for contrib in contributions:
                    text += f"{contrib['name']}\n"
                    text += f"Прогресс цели: {contrib['progress']:.1f}%\n"
                    text += f"Мой вклад: {contrib['user_contribution']} шлёпков\n"
                    text += f"Моя доля: {contrib['user_percentage']:.1f}%\n\n"
        else:
            text = "Система целей временно недоступна"
        
        keyboard = get_back_button("goals")
        await query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    elif data == "goals_progress":
        await goals_command(update, context)
    else:
        await query.message.reply_text("Эта функция целей скоро будет доступна!")

async def handle_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    query = update.callback_query
    
    if data == "back_main":
        await start_command(update, context)
    elif data == "back_skills":
        await upgrade_command(update, context)
    elif data == "back_stats":
        await detailed_stats_command(update, context)
    elif data == "back_goals":
        await goals_command(update, context)
    elif data == "back_achievements":
        await achievements_command(update, context)
    else:
        await query.message.reply_text("Возврат в меню")

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

def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не найден! Проверь .env файл.")
        return
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("shlep", shlep_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("mishok", mishok_info_command))
    application.add_handler(CommandHandler("help", help_command))
    
    application.add_handler(CommandHandler("level", level_command))
    application.add_handler(CommandHandler("detailed_stats", detailed_stats_command))
    application.add_handler(CommandHandler("goals", goals_command))
    application.add_handler(CommandHandler("upgrade", upgrade_command))
    application.add_handler(CommandHandler("achievements", achievements_command))
    
    application.add_handler(CallbackQueryHandler(inline_handler))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, group_welcome))
    
    application.add_error_handler(error_handler)
    
    logger.info("=" * 50)
    logger.info("ЗАПУСК БОТА 'МИШОК ЛЫСЫЙ'")
    logger.info("=" * 50)
    
    logger.info(f"Загружено систем: {len(SYSTEMS)} из 4")
    if SYSTEMS:
        logger.info(f"Системы: {', '.join(SYSTEMS.keys())}")
    else:
        logger.warning("Ни одна система не загружена, бот работает в базовом режиме")
    
    if CONFIG_AVAILABLE:
        logger.info(f"Конфигурация: {len(MISHOK_REACTIONS)} реакций, {len(STICKERS)} стикеров")
    else:
        logger.warning("Конфигурация не загружена")
    
    if DATABASE_AVAILABLE:
        logger.info("База данных доступна")
    else:
        logger.warning("База данных недоступна, используется заглушка")
    
    logger.info("Бот готов к работе...")
    
    try:
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
    except Exception as e:
        logger.error(f"КРИТИЧЕСКАЯ ОШИБКА: {e}")
        logger.error("Бот остановлен")

if __name__ == "__main__":
    main()
