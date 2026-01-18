import logging
import random
from datetime import datetime
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters, JobQueue
)
from telegram.constants import ParseMode

# Импорт конфигурации
from config import BOT_TOKEN, MISHOK_REACTIONS, MISHOK_INTRO, STICKERS

# Импорт систем
from database import init_db, add_shlep, get_stats, get_top_users, add_points
from keyboard import (
    get_main_keyboard, get_inline_keyboard, get_achievements_keyboard,
    get_tasks_keyboard, get_rating_keyboard, get_game_keyboard
)
from achievements import AchievementSystem
from tasks import TaskSystem, RatingSystem
from utils import get_moscow_time, format_time_remaining, generate_animation

# Импорт новых систем (которые мы уже создали)
from levels import LevelSystem, MishokLevelSystem, SkillsSystem
from statistics import StatisticsSystem
from events import RecordsSystem, EventSystem
from goals import GlobalGoalsSystem

# Инициализация всех систем
achievement_system = AchievementSystem()
task_system = TaskSystem()
rating_system = RatingSystem()
level_system = LevelSystem()
mishok_level_system = MishokLevelSystem()
skills_system = SkillsSystem()
stats_system = StatisticsSystem()
records_system = RecordsSystem()
event_system = EventSystem()
goals_system = GlobalGoalsSystem()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация БД
init_db()

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

def get_user_display_name(user):
    """Получить отображаемое имя пользователя"""
    if user.username:
        return f"@{user.username}"
    elif user.first_name:
        return user.first_name
    else:
        return f"User {user.id}"

# ========== ОСНОВНЫЕ КОМАНДЫ ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /start"""
    user = update.effective_user
    chat = update.effective_chat
    
    welcome_text = f"""
👋 Привет, {user.first_name}!

Я бот с *Мишком Лысым* — самым терпеливым лысым персонажем в Telegram!
Теперь с полноценной игровой системой:

🎯 *Уровни и прокачка*
📊 *Детальная статистика* 
🏆 *Рекорды и достижения*
🎪 *События и цели*

В личных сообщениях используй кнопки ниже.
В группах — команду /shlep или кнопку под сообщением.
    """
    
    if chat.type == "private":
        await update.message.reply_text(
            welcome_text,
            reply_markup=get_game_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            f"{user.first_name} хочет шлёпать Мишка! Используй /shlep",
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
    """Основная логика шлёпка со всеми системами"""
    user = update.effective_user
    chat = update.effective_chat
    
    # ===== 1. ПРОВЕРКА СОБЫТИЙ =====
    event_multiplier, active_events = event_system.get_event_multiplier()
    
    # ===== 2. РАСЧЁТ XP =====
    base_xp = 10
    
    # Применяем навыки пользователя
    user_skills = skills_system.get_user_skills(user.id)
    
    # Навык: Меткий шлёпок (увеличивает XP)
    if 'accurate_slap' in user_skills:
        accurate_level = user_skills['accurate_slap']['current_level']
        if accurate_level > 0:
            base_xp *= (1 + user_skills['accurate_slap']['current_effect'])
    
    # Навык: Критический удар (шанс на 2x XP)
    is_critical = False
    if 'critical_slap' in user_skills:
        critical_chance = user_skills['critical_slap']['current_effect']
        if random.random() < critical_chance:
            base_xp *= 2
            is_critical = True
    
    # Применяем множитель события
    total_xp = int(base_xp * event_multiplier)
    
    # ===== 3. ОБНОВЛЕНИЕ СТАТИСТИКИ =====
    # Добавляем шлёпок в основную статистику
    total_shleps, user_count = add_shlep(user.id, user.username or user.first_name)
    
    # Добавляем XP пользователю
    level_info = level_system.add_xp(user.id, total_xp, "shlep")
    
    # Записываем в детальную статистику
    stats_system.record_shlep(user.id)
    
    # ===== 4. ПРОВЕРКА РЕКОРДОВ =====
    # Сила шлёпка (случайное значение от 1 до 100 * множитель)
    slap_strength = random.random() * 100 * event_multiplier
    new_strength_record, record_value = records_system.check_strength_record(
        user.id, slap_strength
    )
    
    # ===== 5. ПРОВЕРКА ДОСТИЖЕНИЙ =====
    new_achievements = achievement_system.check_achievements(user.id, user_count)
    
    # ===== 6. ОБНОВЛЕНИЕ ЗАДАНИЙ =====
    completed_tasks = task_system.update_task_progress(user.id)
    
    # ===== 7. ОБНОВЛЕНИЕ ГЛОБАЛЬНЫХ ЦЕЛЕЙ =====
    for goal in goals_system.active_goals:
        goals_system.update_goal_progress(goal['id'])
    
    # ===== 8. ПОЛУЧАЕМ УРОВЕНЬ МИШКА =====
    mishok_level = mishok_level_system.get_mishok_level(total_shleps)
    
    # ===== 9. ВЫБОР РЕАКЦИИ =====
    # Выбираем реакцию в зависимости от уровня Мишка
    if mishok_level['reactions'] == 'legendary':
        reactions = [r for r in MISHOK_REACTIONS if '🔥' in r or '⚡' in r]
    elif mishok_level['reactions'] == 'epic':
        reactions = [r for r in MISHOK_REACTIONS if '💢' in r or '✨' in r]
    else:
        reactions = MISHOK_REACTIONS
    
    reaction = random.choice(reactions)
    
    # ===== 10. ФОРМИРОВАНИЕ СООБЩЕНИЯ =====
    message_text = f"""
{reaction}

📊 *Шлёпок №{total_shleps:,}*
👤 {user.first_name}: {user_count} шлёпков | Ур. {level_info['level']}
⚡ Опыт: +{total_xp} XP
📈 Прогресс: {level_info['progress']:.1f}% до {level_info['level'] + 1} уровня
👴 *Уровень Мишка:* {mishok_level['name']}
    """
    
    # Добавляем информацию о событии
    if active_events:
        event_text = "\n".join([f"🎪 {e['name']}: {e['description']}" for e in active_events])
        message_text += f"\n\n{event_text}"
    
    # Добавляем информацию о критическом ударе
    if is_critical:
        message_text += "\n\n💥 *КРИТИЧЕСКИЙ УДАР!* x2 XP"
    
    # Добавляем информацию о новом рекорде
    if new_strength_record:
        message_text += f"\n\n🏆 *НОВЫЙ РЕКОРД СИЛЫ!* {slap_strength:.1f} единиц!"
    
    # Добавляем информацию о новых достижениях
    if new_achievements:
        for ach in new_achievements:
            message_text += f"\n🎉 *Новое достижение!* {ach['emoji']} {ach['name']}"
            points = ach.get('points', 10)
            total_points = add_points(user.id, points)
            message_text += f" (+{points} очков)"
    
    # Добавляем информацию о выполненных задачах
    if completed_tasks:
        message_text += "\n\n📅 *Выполненные задания:*"
        for task in completed_tasks:
            message_text += f"\n✅ {task['emoji']} {task['name']} (+{task['reward']} очков)"
            add_points(user.id, task['reward'])
    
    # Добавляем ASCII анимацию (с вероятностью 10%)
    if random.random() < 0.1:
        animation = generate_animation()
        message_text += f"\n\n{animation}"
    
    # ===== 11. ОТПРАВКА СООБЩЕНИЯ =====
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
    
    # ===== 12. ОТПРАВКА СТИКЕРА =====
    sticker_key = random.choice(list(STICKERS.keys()))
    if STICKERS.get(sticker_key):
        try:
            if is_callback:
                await update.callback_query.message.reply_sticker(STICKERS[sticker_key])
            else:
                await update.message.reply_sticker(STICKERS[sticker_key])
        except:
            pass  # Если стикер не найден

# ========== КОМАНДЫ СТАТИСТИКИ ==========

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Базовая статистика (/stats)"""
    total_shleps, last_shlep = get_stats()
    
    # Получаем топ пользователей
    top_users = get_top_users(5)
    
    top_text = "\n".join([
        f"{i+1}. {user[0] or 'Аноним'}: {user[1]} шлёпков" 
        for i, user in enumerate(top_users)
    ]) if top_users else "Пока никто не шлёпал"
    
    last_time = last_shlep.strftime("%d.%m.%Y %H:%M") if last_shlep else "никогда"
    
    stats_text = f"""
📊 *Статистика шлёпков*

🔢 Всего шлёпков: *{total_shleps:,}*
⏰ Последний шлёпок: *{last_time}*

🏆 *Топ шлёпателей:*
{top_text}

Мишок устал, но держится! 💪
    """
    
    await update.message.reply_text(
        stats_text,
        parse_mode=ParseMode.MARKDOWN
    )

async def detailed_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Детальная статистика (/detailed_stats)"""
    user = update.effective_user
    
    # Получаем любимое время
    favorite_time = stats_system.get_favorite_time(user.id)
    
    # Получаем глобальную статистику
    global_stats = goals_system.get_global_stats()
    
    # Получаем распределение по времени суток
    hourly_dist = stats_system.get_hourly_distribution(user.id)
    
    # Определяем самое активное время
    if any(hourly_dist):
        max_hour = hourly_dist.index(max(hourly_dist))
        time_of_day = {
            (0, 6): "ночью 🌙",
            (7, 12): "утром 🌅", 
            (13, 17): "днём ☀️",
            (18, 23): "вечером 🌆"
        }
        
        for (start, end), desc in time_of_day.items():
            if start <= max_hour <= end:
                peak_time = desc
                break
    else:
        peak_time = "нет данных"
    
    text = f"""
📈 *Детальная статистика*

{favorite_time}
📅 Пиковая активность: {peak_time}
⏰ Чаще всего шлёпаешь в {max_hour}:00

*Глобальная статистика сообщества:*
👥 Активных сегодня: {global_stats['active_today']}
🎯 Шлёпков сегодня: {global_stats['today_shleps']:,}
🏆 Рекорд за день: {global_stats['daily_record']:,}
📊 Всего шлёпков: {global_stats['total_shleps']:,}
📈 Среднее на игрока: {global_stats['average_per_user']:.1f}
    """
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

# ========== КОМАНДЫ УРОВНЕЙ И НАВЫКОВ ==========

async def level_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Информация о уровне (/level)"""
    user = update.effective_user
    level_info = level_system.get_level_progress(user.id)
    user_skills = skills_system.get_user_skills(user.id)
    
    # Получаем общее количество очков
    from database import get_connection
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT points FROM user_points WHERE user_id = %s", (user.id,))
            result = cur.fetchone()
            points = result[0] if result else 0
    
    text = f"""
🎯 *Твой уровень:* {level_info['level']}
⚡ *Опыт:* {level_info['xp_current']:,}/{level_info['xp_needed']:,}
📊 *Прогресс:* {level_info['progress']:.1f}%
💰 *Очков:* {points}

*Навыки:*
    """
    
    skill_emojis = {
        'accurate_slap': '🎯',
        'combo_slap': '👊', 
        'critical_slap': '💥'
    }
    
    for skill_id, skill_info in user_skills.items():
        emoji = skill_emojis.get(skill_id, '⚡')
        text += f"\n{emoji} *{skill_info['name']}*: Ур. {skill_info['current_level']}/{skill_info['max_level']}"
        if skill_info['next_cost']:
            text += f" (След. уровень: {skill_info['next_cost']} очков)"
        text += f"\n  └ {skill_info['description']}\n"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def upgrade_skill_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Улучшить навык (/upgrade [навык])"""
    user = update.effective_user
    
    if not context.args:
        # Показываем список доступных навыков
        user_skills = skills_system.get_user_skills(user.id)
        
        text = "⚡ *Улучшение навыков*\n\n"
        text += "Доступные навыки:\n"
        
        skill_list = {
            'accurate': ('🎯 Меткий шлёпок', 'accurate_slap'),
            'combo': ('👊 Серия ударов', 'combo_slap'),
            'critical': ('💥 Критический удар', 'critical_slap')
        }
        
        for key, (name, skill_id) in skill_list.items():
            if skill_id in user_skills:
                skill = user_skills[skill_id]
                text += f"\n`/upgrade {key}` - {name} (Ур. {skill['current_level']})"
                if skill['next_cost']:
                    text += f" - {skill['next_cost']} очков"
        
        text += "\n\nПример: `/upgrade accurate`"
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        return
    
    skill_key = context.args[0].lower()
    skill_map = {
        'accurate': 'accurate_slap',
        'combo': 'combo_slap', 
        'critical': 'critical_slap'
    }
    
    if skill_key not in skill_map:
        await update.message.reply_text(
            "❌ Неизвестный навык. Используй /upgrade без аргументов для списка.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    skill_id = skill_map[skill_key]
    success, message = skills_system.upgrade_skill(user.id, skill_id)
    
    if success:
        await update.message.reply_text(f"✅ {message}", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(f"❌ {message}", parse_mode=ParseMode.MARKDOWN)

# ========== КОМАНДЫ РЕКОРДОВ ==========

async def records_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Рекорды (/records)"""
    all_records = records_system.get_all_records()
    
    if not all_records:
        text = "🏆 Рекордов пока нет. Будь первым!"
    else:
        text = "🏆 *Текущие рекорды:*\n\n"
        
        for record_type, record in all_records.items():
            timestamp = record['timestamp'].strftime("%d.%m.%Y %H:%M") if record['timestamp'] else "недавно"
            
            # Форматируем значение в зависимости от типа рекорда
            if record_type == 'strongest_slap':
                value_text = f"{record['value']:.1f} силы"
            elif record_type == 'fastest_slap':
                value_text = f"{record['value']:.1f} шлёпков/мин"
            elif record_type == 'longest_combo':
                value_text = f"{int(record['value'])} ударов подряд"
            else:
                value_text = f"{record['value']:.1f}"
            
            text += f"*{record['name']}:*\n"
            text += f"  👤 {record['username']}\n"
            text += f"  🎯 {value_text}\n"
            text += f"  ⏰ {timestamp}\n\n"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

# ========== КОМАНДЫ СОБЫТИЙ ==========

async def events_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """События (/events)"""
    _, active_events = event_system.get_event_multiplier()
    upcoming_events = event_system.get_upcoming_events()
    
    text = "🎪 *События и бонусы*\n\n"
    
    # Текущий множитель
    current_multiplier, _ = event_system.get_event_multiplier()
    if current_multiplier != 1.0:
        text += f"📈 *Текущий множитель опыта:* x{current_multiplier:.1f}\n\n"
    
    if active_events:
        text += "*🎉 Активные сейчас:*\n"
        for event in active_events:
            text += f"\n*{event['name']}*\n"
            text += f"  {event['description']}\n"
            text += f"  ⏳ Заканчивается через: {event['ends_in']} мин\n"
    else:
        text += "Сейчас нет активных событий.\n\n"
    
    if upcoming_events:
        text += "\n*⏰ Скоро начнутся:*\n"
        for event in upcoming_events[:3]:  # Показываем только 3 ближайших
            starts_in = f"через {event['starts_in']} минут" if event['starts_in'] > 0 else "скоро"
            text += f"\n⏰ *{event['name']}* - {starts_in}\n"
            text += f"  Множитель: x{event['multiplier']:.1f}\n"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

# ========== КОМАНДЫ ЦЕЛЕЙ ==========

async def goals_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Глобальные цели (/goals)"""
    user = update.effective_user
    contributions = goals_system.get_community_contributions(user.id)
    global_stats = goals_system.get_global_stats()
    
    text = "🎯 *Глобальные цели сообщества*\n\n"
    
    # Прогресс к миллиону
    progress_percent = (global_stats['total_shleps'] / 1000000 * 100)
    progress_bar_length = 20
    filled = int(progress_percent / 100 * progress_bar_length)
    progress_bar = "█" * filled + "░" * (progress_bar_length - filled)
    
    text += f"🎯 *Цель: 1,000,000 шлёпков*\n"
    text += f"📊 {global_stats['total_shleps']:,} / 1,000,000\n"
    text += f"{progress_bar} {progress_percent:.1f}%\n\n"
    
    text += "*Твой вклад в цели:*\n"
    
    if contributions:
        for goal in contributions:
            goal_progress_bar_length = 10
            goal_filled = int(goal['progress'] / 100 * goal_progress_bar_length)
            goal_progress_bar = "█" * goal_filled + "░" * (goal_progress_bar_length - goal_filled)
            
            text += f"\n*{goal['name']}*\n"
            text += f"{goal_progress_bar} {goal['progress']:.1f}%\n"
            text += f"🎯 {goal['current']:,}/{goal['target']:,}\n"
            text += f"👤 Твой вклад: {goal['user_contribution']} шлёпков\n"
            text += f"🏆 {goal['user_percentage']:.2f}% от общего\n"
    else:
        text += "\nУ тебя пока нет вклада в цели. Шлёпай больше!"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

# ========== КОМАНДЫ ДОСТИЖЕНИЙ ==========

async def achievements_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Система достижений (/achievements)"""
    await update.message.reply_text(
        "🎯 *Система достижений*\n\n"
        "Получайте достижения за шлёпки! Чем больше шлёпаете, тем круче достижения!",
        reply_markup=get_achievements_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

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
            achieved_at = ach['achieved_at'].strftime("%d.%m.%Y") if 'achieved_at' in ach else ""
            text += f"{ach['emoji']} *{ach['name']}*\n"
            text += f"  └ {ach['description']}"
            if achieved_at:
                text += f" ({achieved_at})"
            text += "\n\n"
    
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

# ========== КОМАНДЫ ЗАДАНИЙ ==========

async def tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ежедневные задания (/tasks)"""
    user = update.effective_user
    task_system.init_user_tasks(user.id)
    
    await update.message.reply_text(
        "📅 *Ежедневные задания*\n\n"
        "Выполняй задания каждый день и получай награды! Задания обновляются в 00:00 по МСК.",
        reply_markup=get_tasks_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

async def my_tasks_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Мои задания на сегодня"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    tasks = task_system.get_user_tasks(user.id)
    
    text = "📅 *Твои задания на сегодня:*\n\n"
    time_left = format_time_remaining()
    
    total_reward = 0
    completed_count = 0
    
    for task in tasks:
        status = "✅" if task['completed'] else "⏳"
        progress = f"{task['progress']}/{task['required']}"
        reward = f"+{task['reward']} очков"
        
        text += f"{task['emoji']} *{task['name']}*\n"
        text += f"  └ {status} {progress} | {reward}\n\n"
        
        if task['completed']:
            completed_count += 1
            total_reward += task['reward']
    
    text += f"⏰ *До конца дня:* {time_left}\n"
    text += f"✅ *Выполнено:* {completed_count}/{len(tasks)}\n"
    text += f"💰 *Всего наград:* {total_reward} очков"
    
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)

# ========== КОМАНДЫ РЕЙТИНГА ==========

async def rating_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Рейтинги (/rating)"""
    await update.message.reply_text(
        "🏆 *Рейтинги*\n\n"
        "Соревнуйся с другими в количестве шлёпков!",
        reply_markup=get_rating_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

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

# ========== ОБРАБОТЧИК КНОПОК ==========

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кнопок в личных сообщениях"""
    text = update.message.text
    chat = update.effective_chat
    
    if chat.type != "private":
        return
    
    # Определяем какая кнопка нажата
    button_actions = {
        "👊 Шлёпнуть Мишка": lambda: process_shlep(update, context, False),
        "🎯 Уровень": lambda: level_command(update, context),
        "📈 Статистика": lambda: detailed_stats_command(update, context),
        "📊 Статистика": lambda: stats_command(update, context),
        "🏆 Рекорды": lambda: records_command(update, context),
        "🎪 События": lambda: events_command(update, context),
        "🎯 Цели": lambda: goals_command(update, context),
        "⚡ Навыки": lambda: upgrade_skill_command(update, context),
        "👴 О Мишке": lambda: mishok_info(update, context),
        "📅 Задания": lambda: tasks_command(update, context),
        "🏆 Рейтинг": lambda: rating_command(update, context)
    }
    
    if text in button_actions:
        await button_actions[text]()
    else:
        await update.message.reply_text(
            "Используй кнопки ниже или команды!",
            reply_markup=get_game_keyboard()
        )

# ========== ДРУГИЕ ОБРАБОТЧИКИ ==========

async def group_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветствие при добавлении в группу"""
    if update.message.new_chat_members:
        for member in update.message.new_chat_members:
            if member.id == context.bot.id:
                welcome_text = """
👴 *Мишок Лысый в чате!*

Теперь можно шлёпать меня по лысине прямо здесь!

Используй:
/shlep - шлёпнуть Мишка
/level - твой уровень
/stats - статистика
/events - активные события

Или нажми кнопку ниже для быстрого шлёпка!
                """
                await update.message.reply_text(
                    welcome_text,
                    reply_markup=get_inline_keyboard(),
                    parse_mode=ParseMode.MARKDOWN
                )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ошибок"""
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ Произошла ошибка. Попробуй снова или свяжись с разработчиком."
        )

# ========== ЗАПУСК БОТА ==========

def main():
    """Запуск бота"""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not found!")
        return
    
    # Создаём приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # ===== ОСНОВНЫЕ КОМАНДЫ =====
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("shlep", shlep_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("mishok", mishok_info))
    
    # ===== НОВЫЕ КОМАНДЫ (системы 1-5) =====
    application.add_handler(CommandHandler("level", level_command))
    application.add_handler(CommandHandler("detailed_stats", detailed_stats_command))
    application.add_handler(CommandHandler("records", records_command))
    application.add_handler(CommandHandler("events", events_command))
    application.add_handler(CommandHandler("goals", goals_command))
    application.add_handler(CommandHandler("upgrade", upgrade_skill_command))
    
    # ===== КОМАНДЫ ИЗ ПРЕДЫДУЩИХ СИСТЕМ =====
    application.add_handler(CommandHandler("achievements", achievements_command))
    application.add_handler(CommandHandler("tasks", tasks_command))
    application.add_handler(CommandHandler("rating", rating_command))
    
    # ===== INLINE-КНОПКИ =====
    application.add_handler(CallbackQueryHandler(shlep_callback, pattern="^shlep_mishok$"))
    
    # Достижения
    application.add_handler(CallbackQueryHandler(my_achievements_callback, pattern="^my_achievements$"))
    application.add_handler(CallbackQueryHandler(next_achievement_callback, pattern="^next_achievement$"))
    
    # Задания
    application.add_handler(CallbackQueryHandler(my_tasks_callback, pattern="^my_tasks$"))
    
    # Рейтинг
    application.add_handler(CallbackQueryHandler(daily_rating_callback, pattern="^daily_rating$"))
    application.add_handler(CallbackQueryHandler(weekly_rating_callback, pattern="^weekly_rating$"))
    
    # ===== СООБЩЕНИЯ =====
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, group_welcome))
    
    # ===== ОШИБКИ =====
    application.add_error_handler(error_handler)
    
    # ===== ЗАПУСК =====
    logger.info("🤖 Бот Мишок Лысый запускается...")
    logger.info("🎮 Доступные системы: Уровни, Статистика, Рекорды, События, Цели")
    
    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.error(f"Ошибка запуска бота: {e}")

if __name__ == "__main__":
    main()
