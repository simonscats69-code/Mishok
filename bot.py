import logging
import random
from datetime import datetime
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
from telegram.constants import ParseMode

# ========== ИМПОРТЫ С ЗАЩИТОЙ ОТ ОШИБОК ==========

# 1. Конфигурация (обязательно)
try:
    from config import BOT_TOKEN, MISHOK_REACTIONS, MISHOK_INTRO, STICKERS
except ImportError as e:
    logging.error(f"❌ Ошибка импорта config: {e}")
    # Минимальные значения для работы
    BOT_TOKEN = ""
    MISHOK_REACTIONS = ["Ой, больно! 😠", "Эй, не шлёпай! 👴💢"]
    MISHOK_INTRO = "👴 *Мишок Лысый* - бот для шлёпков"
    STICKERS = {}

# 2. База данных (обязательно)
try:
    from database import init_db, add_shlep, get_stats, get_top_users, add_points, get_user_points
except ImportError as e:
    logging.error(f"❌ Ошибка импорта database: {e}")
    # Заглушки
    def init_db(): logging.info("БД: заглушка init_db")
    def add_shlep(user_id, username): 
        logging.info(f"БД: заглушка add_shlep для {user_id}")
        return (0, 0)
    def get_stats(): return (0, None)
    def get_top_users(limit=10): return []
    def add_points(user_id, points): 
        logging.info(f"БД: заглушка add_points {points} для {user_id}")
        return 0
    def get_user_points(user_id): return 0

# 3. Клавиатуры (обязательно)
try:
    from keyboard import (
        get_game_keyboard, get_inline_keyboard, get_achievements_keyboard,
        get_tasks_keyboard, get_rating_keyboard
    )
except ImportError as e:
    logging.error(f"❌ Ошибка импорта keyboard: {e}")
    # Заглушки
    def get_game_keyboard(): return None
    def get_inline_keyboard(): return None
    def get_achievements_keyboard(): return None
    def get_tasks_keyboard(): return None
    def get_rating_keyboard(): return None

# 4. Системы (опционально, с защитой)
SYSTEMS = {}

# Уровни
try:
    from levels import LevelSystem, MishokLevelSystem, SkillsSystem
    SYSTEMS['levels'] = LevelSystem()
    SYSTEMS['mishok_levels'] = MishokLevelSystem()
    SYSTEMS['skills'] = SkillsSystem()
    logging.info("✅ Система уровней загружена")
except ImportError as e:
    logging.warning(f"⚠️ Система уровней не загружена: {e}")

# Статистика
try:
    from statistics import StatisticsSystem
    SYSTEMS['stats'] = StatisticsSystem()
    logging.info("✅ Система статистики загружена")
except ImportError as e:
    logging.warning(f"⚠️ Система статистики не загружена: {e}")

# Рекорды и события
try:
    from events import RecordsSystem, EventSystem
    SYSTEMS['records'] = RecordsSystem()
    SYSTEMS['events'] = EventSystem()
    logging.info("✅ Системы рекордов и событий загружены")
except ImportError as e:
    logging.warning(f"⚠️ Системы рекордов/событий не загружены: {e}")

# Цели
try:
    from goals import GlobalGoalsSystem
    SYSTEMS['goals'] = GlobalGoalsSystem()
    logging.info("✅ Система целей загружена")
except ImportError as e:
    logging.warning(f"⚠️ Система целей не загружена: {e}")

# Достижения и задания
try:
    from achievements import AchievementSystem
    from tasks import TaskSystem, RatingSystem
    SYSTEMS['achievements'] = AchievementSystem()
    SYSTEMS['tasks'] = TaskSystem()
    SYSTEMS['rating'] = RatingSystem()
    logging.info("✅ Системы достижений и заданий загружены")
except ImportError as e:
    logging.warning(f"⚠️ Системы достижений/заданий не загружены: {e}")

# Утилиты
try:
    from utils import get_moscow_time, format_time_remaining, generate_animation
except ImportError:
    # Заглушки для утилит
    def get_moscow_time(): return datetime.now()
    def format_time_remaining(): return "00:00"
    def generate_animation(): return "✨"

# ========== НАСТРОЙКА ЛОГИРОВАНИЯ ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== ИНИЦИАЛИЗАЦИЯ ==========
init_db()

# ========== ОСНОВНЫЕ КОМАНДЫ ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /start"""
    user = update.effective_user
    chat = update.effective_chat
    
    welcome_text = f"""
👋 Привет, {user.first_name}!

Я бот с *Мишком Лысым* — самым терпеливым лысым персонажем в Telegram!

🎮 *Доступные системы:*
{ '✅ Уровни и прокачка' if 'levels' in SYSTEMS else '❌ Уровни (скоро)' }
{ '✅ Детальная статистика' if 'stats' in SYSTEMS else '❌ Статистика (скоро)' }
{ '✅ Рекорды и события' if 'records' in SYSTEMS else '❌ Рекорды (скоро)' }
{ '✅ Глобальные цели' if 'goals' in SYSTEMS else '❌ Цели (скоро)' }

*Основные команды:*
/shlep - шлёпнуть Мишка
/level - твой уровень
/stats - статистика
/events - активные события
/goals - глобальные цели
/records - рекорды
    """
    
    if chat.type == "private":
        await update.message.reply_text(
            welcome_text,
            reply_markup=get_game_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            f"👋 {user.first_name}, используй /shlep чтобы шлёпнуть Мишка!",
            reply_markup=get_inline_keyboard()
        )

async def mishok_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Информация о Мишке (/mishok)"""
    await update.message.reply_text(
        MISHOK_INTRO,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_inline_keyboard() if update.effective_chat.type != "private" else None
    )

# ========== ОСНОВНАЯ ЛОГИКА ШЛЁПКА ==========

async def shlep_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /shlep"""
    await process_shlep(update, context, is_callback=False)

async def shlep_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка inline-кнопки"""
    query = update.callback_query
    await query.answer()
    await process_shlep(update, context, is_callback=True)

async def process_shlep(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback: bool):
    """Основная логика шлёпка"""
    user = update.effective_user
    chat = update.effective_chat
    
    # 1. БАЗОВАЯ СТАТИСТИКА
    total_shleps, user_count = add_shlep(user.id, user.username or user.first_name)
    
    # 2. ПЕРЕМЕННЫЕ ДЛЯ СИСТЕМ
    event_multiplier = 1.0
    total_xp = 10
    level_info = {"level": 1, "progress": 0}
    new_achievements = []
    completed_tasks = []
    new_strength_record = False
    slap_strength = 0
    
    # 3. СИСТЕМА УРОВНЕЙ
    if 'levels' in SYSTEMS:
        try:
            # Навыки
            user_skills = SYSTEMS['skills'].get_user_skills(user.id)
            
            # Базовый XP
            base_xp = 10
            
            # Меткий шлёпок
            if 'accurate_slap' in user_skills:
                accurate_level = user_skills['accurate_slap']['current_level']
                if accurate_level > 0:
                    base_xp *= (1 + user_skills['accurate_slap']['current_effect'])
            
            # Критический удар
            if 'critical_slap' in user_skills:
                critical_chance = user_skills['critical_slap']['current_effect']
                if random.random() < critical_chance:
                    base_xp *= 2
            
            # Множитель событий
            if 'events' in SYSTEMS:
                event_multiplier, _ = SYSTEMS['events'].get_event_multiplier()
            
            total_xp = int(base_xp * event_multiplier)
            
            # Добавляем XP
            level_info = SYSTEMS['levels'].add_xp(user.id, total_xp, "shlep")
        except Exception as e:
            logger.error(f"Ошибка системы уровней: {e}")
    
    # 4. ДЕТАЛЬНАЯ СТАТИСТИКА
    if 'stats' in SYSTEMS:
        try:
            SYSTEMS['stats'].record_shlep(user.id)
        except:
            pass
    
    # 5. РЕКОРДЫ
    if 'records' in SYSTEMS:
        try:
            slap_strength = random.random() * 100 * event_multiplier
            new_strength_record, _ = SYSTEMS['records'].check_strength_record(user.id, slap_strength)
        except:
            pass
    
    # 6. ГЛОБАЛЬНЫЕ ЦЕЛИ
    if 'goals' in SYSTEMS:
        try:
            for goal in SYSTEMS['goals'].active_goals:
                SYSTEMS['goals'].update_goal_progress(goal['id'])
        except:
            pass
    
    # 7. ДОСТИЖЕНИЯ
    if 'achievements' in SYSTEMS:
        try:
            new_achievements = SYSTEMS['achievements'].check_achievements(user.id, user_count)
        except:
            pass
    
    # 8. ЗАДАНИЯ
    if 'tasks' in SYSTEMS:
        try:
            completed_tasks = SYSTEMS['tasks'].update_task_progress(user.id)
        except:
            pass
    
    # 9. УРОВЕНЬ МИШКА
    mishok_level_name = "Нежный Мишок"
    if 'mishok_levels' in SYSTEMS:
        try:
            mishok_level = SYSTEMS['mishok_levels'].get_mishok_level(total_shleps)
            mishok_level_name = mishok_level['name']
        except:
            pass
    
    # 10. РЕАКЦИЯ
    reaction = random.choice(MISHOK_REACTIONS)
    
    # 11. ФОРМИРОВАНИЕ СООБЩЕНИЯ
    message_text = f"""
{reaction}

📊 *Шлёпок №{total_shleps:,}*
👤 {user.first_name}: {user_count} шлёпков
"""
    
    # Добавляем уровень
    if 'levels' in SYSTEMS:
        message_text += f"🎯 Ур. {level_info['level']} (+{total_xp} XP)\n"
    
    message_text += f"👴 *Уровень Мишка:* {mishok_level_name}\n"
    
    # Добавляем множитель
    if event_multiplier != 1.0:
        message_text += f"🎪 Множитель: x{event_multiplier:.1f}\n"
    
    # Новый рекорд
    if new_strength_record:
        message_text += f"\n🏆 *НОВЫЙ РЕКОРД!* {slap_strength:.1f} силы!\n"
    
    # Новые достижения
    if new_achievements:
        for ach in new_achievements:
            message_text += f"\n🎉 {ach['emoji']} *{ach['name']}*"
            add_points(user.id, 10)
    
    # Выполненные задания
    if completed_tasks:
        message_text += "\n\n📅 *Выполнено:*"
        for task in completed_tasks:
            message_text += f"\n✅ {task['emoji']} {task['name']} (+{task['reward']} очков)"
            add_points(user.id, task['reward'])
    
    # Анимация
    if random.random() < 0.1:
        try:
            animation = generate_animation()
            message_text += f"\n\n{animation}"
        except:
            pass
    
    # 12. ОТПРАВКА
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
    
    # 13. СТИКЕР
    if STICKERS:
        try:
            sticker_key = random.choice(list(STICKERS.keys()))
            if is_callback:
                await update.callback_query.message.reply_sticker(STICKERS[sticker_key])
            else:
                await update.message.reply_sticker(STICKERS[sticker_key])
        except:
            pass

# ========== КОМАНДЫ СИСТЕМ ==========

async def level_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /level"""
    if 'levels' not in SYSTEMS:
        await update.message.reply_text("🎯 Система уровней скоро будет доступна!")
        return
    
    user = update.effective_user
    try:
        level_info = SYSTEMS['levels'].get_level_progress(user.id)
        user_skills = SYSTEMS['skills'].get_user_skills(user.id)
        
        points = get_user_points(user.id)
        
        text = f"""
🎯 *Твой уровень:* {level_info['level']}
⚡ *Опыт:* {level_info['xp_current']:,}/{level_info['xp_needed']:,}
📊 *Прогресс:* {level_info['progress']:.1f}%
💰 *Очков:* {points}

*Навыки:*
"""
        
        for skill_id, skill_info in user_skills.items():
            text += f"\n{skill_info['name']}: Ур. {skill_info['current_level']}"
            if skill_info['next_cost']:
                text += f" (След.: {skill_info['next_cost']} очков)"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Ошибка команды level: {e}")
        await update.message.reply_text("❌ Ошибка загрузки уровня")

async def detailed_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /detailed_stats"""
    if 'stats' not in SYSTEMS:
        await update.message.reply_text("📊 Детальная статистика скоро будет доступна!")
        return
    
    user = update.effective_user
    try:
        favorite_time = SYSTEMS['stats'].get_favorite_time(user.id)
        
        text = f"""
📈 *Детальная статистика*

{favorite_time}

*Статистика обновляется после каждого шлёпка!*
"""
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    except:
        await update.message.reply_text("📊 Используй /stats для базовой статистики")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /stats"""
    total_shleps, last_shlep = get_stats()
    top_users = get_top_users(5)
    
    top_text = "\n".join([
        f"{i+1}. {user[0] or 'Аноним'}: {user[1]} шлёпков" 
        for i, user in enumerate(top_users)
    ]) if top_users else "Пока никто не шлёпал"
    
    last_time = last_shlep.strftime("%d.%m.%Y %H:%M") if last_shlep else "никогда"
    
    text = f"""
📊 *Статистика шлёпков*

🔢 Всего шлёпков: *{total_shleps:,}*
⏰ Последний шлёпок: *{last_time}*

🏆 *Топ шлёпателей:*
{top_text}
"""
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def records_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /records"""
    if 'records' not in SYSTEMS:
        await update.message.reply_text("🏆 Система рекордов скоро будет доступна!")
        return
    
    try:
        all_records = SYSTEMS['records'].get_all_records()
        
        if not all_records:
            text = "🏆 Рекордов пока нет. Будь первым!"
        else:
            text = "🏆 *Текущие рекорды:*\n\n"
            for record_type, record in all_records.items():
                text += f"*{record['name']}:*\n"
                text += f"  👤 {record['username']}\n"
                text += f"  🎯 {record['value']:.1f}\n\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    except:
        await update.message.reply_text("🏆 Шлёпай больше чтобы установить рекорды!")

async def events_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /events"""
    if 'events' not in SYSTEMS:
        await update.message.reply_text("🎪 Система событий скоро будет доступна!")
        return
    
    try:
        multiplier, active_events = SYSTEMS['events'].get_event_multiplier()
        
        text = "🎪 *События*\n\n"
        
        if multiplier != 1.0:
            text += f"📈 *Текущий множитель опыта:* x{multiplier:.1f}\n\n"
        
        if active_events:
            text += "*Активные события:*\n"
            for event in active_events:
                text += f"\n🎉 {event['name']}\n"
                text += f"  {event['description']}\n"
        else:
            text += "Сейчас нет активных событий."
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    except:
        await update.message.reply_text("🎪 События появятся скоро!")

async def goals_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /goals"""
    if 'goals' not in SYSTEMS:
        await update.message.reply_text("🎯 Система целей скоро будет доступна!")
        return
    
    try:
        global_stats = SYSTEMS['goals'].get_global_stats()
        total_shleps = global_stats.get('total_shleps', 0)
        progress = (total_shleps / 1000000 * 100)
        
        text = f"""
🎯 *Глобальная цель: 1,000,000 шлёпков*

📊 *Прогресс:* {total_shleps:,} / 1,000,000
📈 {progress:.1f}%

👥 *Активных сегодня:* {global_stats.get('active_today', 0)}
"""
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    except:
        await update.message.reply_text("🎯 Цель: 1,000,000 шлёпков всем сообществом!")

async def upgrade_skill_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /upgrade"""
    if 'skills' not in SYSTEMS:
        await update.message.reply_text("⚡ Система навыков скоро будет доступна!")
        return
    
    await update.message.reply_text(
        "⚡ Используй:\n"
        "/upgrade accurate - Меткий шлёпок\n"
        "/upgrade combo - Серия ударов\n"
        "/upgrade critical - Критический удар"
    )

# ========== ЗАПУСК ==========

def main():
    """Запуск бота"""
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN не найден!")
        return
    
    # Проверка систем
    loaded_systems = [name for name in SYSTEMS.keys()]
    logger.info(f"✅ Загружено систем: {len(loaded_systems)}")
    if loaded_systems:
        logger.info(f"📦 Системы: {', '.join(loaded_systems)}")
    
    # Создание приложения
    application = Application.builder().token(BOT_TOKEN).build()
    
    # ===== ОСНОВНЫЕ КОМАНДЫ =====
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("shlep", shlep_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("mishok", mishok_info))
    
    # ===== СИСТЕМНЫЕ КОМАНДЫ =====
    application.add_handler(CommandHandler("level", level_command))
    application.add_handler(CommandHandler("detailed_stats", detailed_stats_command))
    application.add_handler(CommandHandler("records", records_command))
    application.add_handler(CommandHandler("events", events_command))
    application.add_handler(CommandHandler("goals", goals_command))
    application.add_handler(CommandHandler("upgrade", upgrade_skill_command))
    
    # ===== INLINE КНОПКИ =====
    application.add_handler(CallbackQueryHandler(shlep_callback, pattern="^shlep_mishok$"))
    
    # ===== ЗАПУСК =====
    logger.info("🚀 Бот Мишок Лысый запускается...")
    
    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.error(f"💥 Ошибка запуска бота: {e}")

if __name__ == "__main__":
    main()
