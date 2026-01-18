#!/usr/bin/env python3
"""
🤖 Бот "Мишок Лысый" - Telegram бот для шлёпков по виртуальной лысине
Основной файл с импортами всех систем и обработкой команд
"""

import logging
import random
import sys
import os
from datetime import datetime
from typing import Optional, Dict, Any

# ========== НАСТРОЙКА ОКРУЖЕНИЯ ==========
# Решаем проблему с NumPy
os.environ['NUMPY_EXPERIMENTAL_ARRAY_FUNCTION'] = '0'

# ========== НАСТРОЙКА ЛОГИРОВАНИЯ ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# ========== ИМПОРТ TELEGRAM API ==========
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
    # Заглушки для тестирования
    class Update: pass
    class ContextTypes: 
        class DEFAULT_TYPE: pass

# ========== ИМПОРТ КОНФИГУРАЦИИ (ОБЯЗАТЕЛЬНО) ==========
try:
    from config import (
        BOT_TOKEN, MISHOK_REACTIONS, MISHOK_INTRO, STICKERS,
        ACHIEVEMENTS, DAILY_TASKS
    )
    CONFIG_AVAILABLE = True
except ImportError as e:
    logger.error(f"❌ Ошибка импорта config: {e}")
    CONFIG_AVAILABLE = False
    # Минимальная конфигурация для работы
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    MISHOK_REACTIONS = ["Ой, больно! 😠", "Эй, не шлёпай! 👴💢"]
    MISHOK_INTRO = "👴 *Мишок Лысый* - бот для шлёпков"
    STICKERS = {}
    ACHIEVEMENTS = {}
    DAILY_TASKS = []

# ========== ИМПОРТ БАЗЫ ДАННЫХ ==========
try:
    from database import (
        init_db, add_shlep, get_stats, get_top_users, add_points, 
        get_user_points, get_user_stats
    )
    DATABASE_AVAILABLE = True
except ImportError as e:
    logger.error(f"❌ Ошибка импорта database: {e}")
    DATABASE_AVAILABLE = False
    # Заглушки для функций БД
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

# ========== ИМПОРТ КЛАВИАТУР ==========
try:
    from keyboard import (
        get_game_keyboard, get_inline_keyboard, get_achievements_keyboard,
        get_tasks_keyboard, get_rating_keyboard
    )
    KEYBOARD_AVAILABLE = True
except ImportError as e:
    logger.error(f"❌ Ошибка импорта keyboard: {e}")
    KEYBOARD_AVAILABLE = False
    def get_game_keyboard(): return None
    def get_inline_keyboard(): return None
    def get_achievements_keyboard(): return None
    def get_tasks_keyboard(): return None
    def get_rating_keyboard(): return None

# ========== ИМПОРТ СИСТЕМ (С ЗАЩИТОЙ ОТ ОШИБОК) ==========
SYSTEMS = {}

# 1. Система уровней
try:
    from levels import LevelSystem, MishokLevelSystem, SkillsSystem
    SYSTEMS['levels'] = LevelSystem()
    SYSTEMS['mishok_levels'] = MishokLevelSystem()
    SYSTEMS['skills'] = SkillsSystem()
    logger.info("✅ Система уровней загружена")
except ImportError as e:
    logger.warning(f"⚠️ Система уровней не загружена: {e}")

# 2. Система статистики
try:
    from statistics import StatisticsSystem
    SYSTEMS['stats'] = StatisticsSystem()
    logger.info("✅ Система статистики загружена")
except ImportError as e:
    logger.warning(f"⚠️ Система статистики не загружена: {e}")

# 3. Система рекордов и событий
try:
    from events import RecordsSystem, EventSystem
    SYSTEMS['records'] = RecordsSystem()
    SYSTEMS['events'] = EventSystem()
    logger.info("✅ Системы рекордов и событий загружены")
except ImportError as e:
    logger.warning(f"⚠️ Системы рекордов/событий не загружены: {e}")

# 4. Система целей
try:
    from goals import GlobalGoalsSystem
    SYSTEMS['goals'] = GlobalGoalsSystem()
    logger.info("✅ Система целей загружена")
except ImportError as e:
    logger.warning(f"⚠️ Система целей не загружена: {e}")

# 5. Система достижений и заданий
try:
    from achievements import AchievementSystem
    from tasks import TaskSystem, RatingSystem
    SYSTEMS['achievements'] = AchievementSystem()
    SYSTEMS['tasks'] = TaskSystem()
    SYSTEMS['rating'] = RatingSystem()
    logger.info("✅ Системы достижений и заданий загружены")
except ImportError as e:
    logger.warning(f"⚠️ Системы достижений/заданий не загружены: {e}")

# 6. Утилиты
try:
    from utils import get_moscow_time, format_time_remaining, generate_animation
    UTILS_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ Утилиты не загружены")
    UTILS_AVAILABLE = False
    def get_moscow_time(): return datetime.now()
    def format_time_remaining(): return "00:00"
    def generate_animation(): return "✨"

# ========== ПРОВЕРКА ДОСТУПНОСТИ КРИТИЧЕСКИХ КОМПОНЕНТОВ ==========
if not TELEGRAM_AVAILABLE:
    logger.error("❌ Библиотека python-telegram-bot не установлена!")
    sys.exit(1)

if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN не установлен! Добавь его в .env файл")
    sys.exit(1)

# ========== ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ ==========
if DATABASE_AVAILABLE:
    try:
        init_db()
        logger.info("✅ База данных инициализирована")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации БД: {e}")
else:
    logger.warning("⚠️ База данных недоступна, используется заглушка")

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

def format_number(num: int) -> str:
    """Форматирование чисел с разделителями"""
    return f"{num:,}".replace(",", " ")

def get_user_display_name(update: Update) -> str:
    """Получить отображаемое имя пользователя"""
    user = update.effective_user
    if user.username:
        return f"@{user.username}"
    elif user.first_name:
        return user.first_name
    else:
        return f"User {user.id}"

# ========== ОБРАБОТЧИКИ КОМАНД ==========

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
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
    """Обработчик команды /mishok"""
    await update.message.reply_text(
        MISHOK_INTRO,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_inline_keyboard() if KEYBOARD_AVAILABLE and update.effective_chat.type != "private" else None
    )

async def shlep_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /shlep"""
    await process_shlep(update, context, is_callback=False)

async def shlep_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик inline-кнопки шлёпка"""
    query = update.callback_query
    await query.answer()
    await process_shlep(update, context, is_callback=True)

async def process_shlep(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback: bool):
    """Основная логика обработки шлёпка"""
    user = update.effective_user
    chat = update.effective_chat
    
    # 1. Регистрируем шлёпок в БД
    total_shleps, user_count = add_shlep(user.id, user.username or user.first_name)
    
    # 2. Инициализируем переменные для систем
    event_multiplier = 1.0
    total_xp = 10
    level_info = {"level": 1, "progress": 0, "xp_current": 0, "xp_needed": 100}
    new_achievements = []
    completed_tasks = []
    new_strength_record = False
    slap_strength = random.uniform(10, 100)
    
    # 3. Обрабатываем системы, если они доступны
    
    # Система событий (множитель опыта)
    if 'events' in SYSTEMS:
        try:
            event_multiplier, active_events = SYSTEMS['events'].get_event_multiplier()
            total_xp = int(total_xp * event_multiplier)
        except Exception as e:
            logger.error(f"Ошибка системы событий: {e}")
    
    # Система уровней и навыков
    if 'levels' in SYSTEMS:
        try:
            # Добавляем XP
            level_info = SYSTEMS['levels'].add_xp(user.id, total_xp, "shlep")
            
            # Применяем навыки
            if 'skills' in SYSTEMS:
                user_skills = SYSTEMS['skills'].get_user_skills(user.id)
                # Здесь можно добавить логику применения навыков
        except Exception as e:
            logger.error(f"Ошибка системы уровней: {e}")
    
    # Система рекордов
    if 'records' in SYSTEMS:
        try:
            new_strength_record, _ = SYSTEMS['records'].check_strength_record(user.id, slap_strength)
        except Exception as e:
            logger.error(f"Ошибка системы рекордов: {e}")
    
    # Система достижений
    if 'achievements' in SYSTEMS:
        try:
            new_achievements = SYSTEMS['achievements'].check_achievements(user.id, user_count)
        except Exception as e:
            logger.error(f"Ошибка системы достижений: {e}")
    
    # Система заданий
    if 'tasks' in SYSTEMS:
        try:
            completed_tasks = SYSTEMS['tasks'].update_task_progress(user.id)
        except Exception as e:
            logger.error(f"Ошибка системы заданий: {e}")
    
    # Система статистики
    if 'stats' in SYSTEMS:
        try:
            SYSTEMS['stats'].record_shlep(user.id)
        except Exception as e:
            logger.error(f"Ошибка системы статистики: {e}")
    
    # Система целей
    if 'goals' in SYSTEMS:
        try:
            for goal in SYSTEMS['goals'].active_goals:
                SYSTEMS['goals'].update_goal_progress(goal['id'])
        except Exception as e:
            logger.error(f"Ошибка системы целей: {e}")
    
    # 4. Получаем уровень Мишка
    mishok_level_name = "Нежный Мишок"
    if 'mishok_levels' in SYSTEMS:
        try:
            mishok_level = SYSTEMS['mishok_levels'].get_mishok_level(total_shleps)
            mishok_level_name = mishok_level['name']
        except Exception as e:
            logger.error(f"Ошибка получения уровня Мишка: {e}")
    
    # 5. Выбираем случайную реакцию
    reaction = random.choice(MISHOK_REACTIONS) if MISHOK_REACTIONS else "Ой! 😠"
    
    # 6. Формируем сообщение
    message_lines = [
        f"{reaction}\n",
        f"📊 *Шлёпок №{format_number(total_shleps)}*",
        f"👤 *{user.first_name}*: {format_number(user_count)} шлёпков",
    ]
    
    # Добавляем уровень игрока
    if 'levels' in SYSTEMS:
        message_lines.append(f"🎯 Уровень: {level_info['level']} (+{total_xp} XP)")
        message_lines.append(f"📈 Прогресс: {level_info['progress']:.1f}%")
    
    message_lines.append(f"👴 *Уровень Мишка:* {mishok_level_name}")
    
    # Добавляем информацию о событии
    if event_multiplier != 1.0:
        message_lines.append(f"🎪 Множитель: x{event_multiplier:.1f}")
    
    # Добавляем информацию о новом рекорде
    if new_strength_record:
        message_lines.append(f"\n🏆 *НОВЫЙ РЕКОРД СИЛЫ!* {slap_strength:.1f} единиц!")
        add_points(user.id, 100)  # Награда за рекорд
    
    # Добавляем информацию о новых достижениях
    if new_achievements:
        for ach in new_achievements:
            message_lines.append(f"\n🎉 {ach['emoji']} *{ach['name']}*")
            add_points(user.id, ach.get('reward_points', 10))
    
    # Добавляем информацию о выполненных заданиях
    if completed_tasks:
        message_lines.append("\n📅 *Выполненные задания:*")
        for task in completed_tasks:
            message_lines.append(f"✅ {task['emoji']} {task['name']} (+{task['reward']} очков)")
            add_points(user.id, task['reward'])
    
    # Добавляем анимацию (редко)
    if random.random() < 0.1 and UTILS_AVAILABLE:
        try:
            animation = generate_animation()
            message_lines.append(f"\n{animation}")
        except:
            pass
    
    # Объединяем все строки
    message_text = "\n".join(message_lines)
    
    # 7. Отправляем сообщение
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
    
    # 8. Отправляем стикер (если есть)
    if STICKERS and random.random() < 0.7:  # 70% шанс отправить стикер
        try:
            sticker_key = random.choice(list(STICKERS.keys()))
            if is_callback:
                await update.callback_query.message.reply_sticker(STICKERS[sticker_key])
            else:
                await update.message.reply_sticker(STICKERS[sticker_key])
        except Exception as e:
            logger.error(f"Ошибка отправки стикера: {e}")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /stats"""
    total_shleps, last_shlep = get_stats()
    top_users = get_top_users(5)
    
    # Формируем топ пользователей
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

async def level_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /level"""
    if 'levels' not in SYSTEMS:
        await update.message.reply_text(
            "🎯 *Система уровней*\n\n"
            "Система уровней временно недоступна. Продолжай шлёпать Мишка!",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    user = update.effective_user
    
    try:
        level_info = SYSTEMS['levels'].get_level_progress(user.id)
        
        # Получаем очки пользователя
        points = get_user_points(user.id)
        
        text = f"""
🎯 *Твой уровень:* {level_info['level']}
⚡ *Опыт:* {format_number(level_info['xp_current'])}/{format_number(level_info['xp_needed'])}
📊 *Прогресс:* {level_info['progress']:.1f}%
💰 *Очков:* {format_number(points)}

*Следующий уровень через:* {format_number(level_info['next_level_in'])} XP
"""
        
        # Добавляем информацию о навыках, если система доступна
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
        await update.message.reply_text(
            "❌ Ошибка загрузки информации об уровне. Попробуй позже.",
            parse_mode=ParseMode.MARKDOWN
        )

async def detailed_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /detailed_stats"""
    if 'stats' not in SYSTEMS:
        await update.message.reply_text(
            "📈 *Детальная статистика*\n\n"
            "Система детальной статистики временно недоступна.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    user = update.effective_user
    
    try:
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
        await update.message.reply_text(
            "❌ Ошибка загрузки детальной статистики.",
            parse_mode=ParseMode.MARKDOWN
        )

async def records_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /records"""
    if 'records' not in SYSTEMS:
        await update.message.reply_text(
            "🏆 *Рекорды*\n\n"
            "Система рекордов временно недоступна.\n"
            "Шлёпай больше, чтобы установить первые рекорды!",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
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
        await update.message.reply_text(
            "❌ Ошибка загрузки рекордов.",
            parse_mode=ParseMode.MARKDOWN
        )

async def events_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /events"""
    if 'events' not in SYSTEMS:
        await update.message.reply_text(
            "🎪 *События*\n\n"
            "Система событий временно недоступна.\n"
            "Скоро появятся специальные события с бонусами!",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
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
        await update.message.reply_text(
            "❌ Ошибка загрузки событий.",
            parse_mode=ParseMode.MARKDOWN
        )

async def goals_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /goals"""
    if 'goals' not in SYSTEMS:
        await update.message.reply_text(
            "🎯 *Глобальные цели*\n\n"
            "Система целей временно недоступна.\n"
            "Скоро появятся глобальные цели для всего сообщества!",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        global_stats = SYSTEMS['goals'].get_global_stats()
        total_shleps = global_stats.get('total_shleps', 0)
        progress_percent = (total_shleps / 1000000 * 100) if total_shleps > 0 else 0
        
        # Создаём прогресс-бар
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
            "🎯 *Цель сообщества:* 1,000,000 шлёпков!\n"
            "Шлёпай больше, чтобы помочь достичь цели!",
            parse_mode=ParseMode.MARKDOWN
        )

async def upgrade_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /upgrade"""
    if 'skills' not in SYSTEMS:
        await update.message.reply_text(
            "⚡ *Улучшение навыков*\n\n"
            "Система навыков временно недоступна.\n"
            "Скоро ты сможешь прокачивать свои умения!",
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

async def achievements_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /achievements"""
    await update.message.reply_text(
        "🏆 *Достижения*\n\n"
        "Система достижений скоро будет доступна!\n"
        "Получай достижения за количество шлёпков.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_achievements_keyboard() if KEYBOARD_AVAILABLE else None
    )

async def tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /tasks"""
    await update.message.reply_text(
        "📅 *Ежедневные задания*\n\n"
        "Система заданий скоро будет доступна!\n"
        "Выполняй задания каждый день и получай награды.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_tasks_keyboard() if KEYBOARD_AVAILABLE else None
    )

async def rating_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /rating"""
    await update.message.reply_text(
        "🏆 *Рейтинги*\n\n"
        "Система рейтингов скоро будет доступна!\n"
        "Соревнуйся с другими игроками!",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_rating_keyboard() if KEYBOARD_AVAILABLE else None
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
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
    """Обработчик нажатий кнопок в личных сообщениях"""
    text = update.message.text
    chat = update.effective_chat
    
    if chat.type != "private":
        return
    
    # Сопоставление текста кнопок с командами
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
    """Приветствие при добавлении бота в группу"""
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

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Update {update} вызвал ошибку: {context.error}")
    
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "❌ Произошла ошибка. Попробуй снова или свяжись с администратором.",
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            pass

# ========== НАСТРОЙКА И ЗАПУСК БОТА ==========

def main():
    """Основная функция запуска бота"""
    # Проверка токена
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN не найден! Проверь .env файл.")
        return
    
    # Создание приложения
    application = Application.builder().token(BOT_TOKEN).build()
    
    # ===== РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ КОМАНД =====
    
    # Основные команды
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("shlep", shlep_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("mishok", mishok_info_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Команды игровых систем
    application.add_handler(CommandHandler("level", level_command))
    application.add_handler(CommandHandler("detailed_stats", detailed_stats_command))
    application.add_handler(CommandHandler("records", records_command))
    application.add_handler(CommandHandler("events", events_command))
    application.add_handler(CommandHandler("goals", goals_command))
    application.add_handler(CommandHandler("upgrade", upgrade_command))
    
    # Дополнительные команды
    application.add_handler(CommandHandler("achievements", achievements_command))
    application.add_handler(CommandHandler("tasks", tasks_command))
    application.add_handler(CommandHandler("rating", rating_command))
    
    # ===== РЕГИСТРАЦИЯ INLINE-ОБРАБОТЧИКОВ =====
    application.add_handler(CallbackQueryHandler(shlep_callback, pattern="^shlep_mishok$"))
    
    # ===== РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ СООБЩЕНИЙ =====
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, group_welcome))
    
    # ===== РЕГИСТРАЦИЯ ОБРАБОТЧИКА ОШИБОК =====
    application.add_error_handler(error_handler)
    
    # ===== ЗАПУСК БОТА =====
    logger.info("=" * 50)
    logger.info("🚀 ЗАПУСК БОТА 'МИШОК ЛЫСЫЙ'")
    logger.info("=" * 50)
    
    # Информация о загруженных системах
    logger.info(f"📦 Загружено систем: {len(SYSTEMS)} из 6")
    if SYSTEMS:
        logger.info(f"✅ Системы: {', '.join(SYSTEMS.keys())}")
    else:
        logger.warning("⚠️ Ни одна система не загружена, бот работает в базовом режиме")
    
    # Информация о конфигурации
    if CONFIG_AVAILABLE:
        logger.info(f"✅ Конфигурация: {len(MISHOK_REACTIONS)} реакций, {len(STICKERS)} стикеров")
    else:
        logger.warning("⚠️ Конфигурация не загружена")
    
    # Информация о БД
    if DATABASE_AVAILABLE:
        logger.info("✅ База данных доступна")
    else:
        logger.warning("⚠️ База данных недоступна, используется заглушка")
    
    logger.info("🤖 Бот готов к работе...")
    
    try:
        # Запуск бота
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
    except Exception as e:
        logger.error(f"💥 КРИТИЧЕСКАЯ ОШИБКА: {e}")
        logger.error("Бот остановлен")

if __name__ == "__main__":
    main()
