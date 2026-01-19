import logging
import random
import sys
import os
from datetime import datetime
from functools import wraps

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.constants import ParseMode
from telegram.helpers import escape_markdown

from config import BOT_TOKEN, MISHOK_REACTIONS, MISHOK_INTRO
from database import add_shlep, get_stats, get_top_users, get_user_stats, get_chat_stats, get_chat_top_users, backup_database, check_data_integrity
from keyboard import get_chat_quick_actions, get_inline_keyboard, get_game_keyboard, get_chat_vote_keyboard
from cache import cache
from statistics import get_favorite_time, get_comparison_stats, get_global_trends_info, format_daily_activity_chart, format_hourly_distribution_chart
from utils import format_number as fmt_num

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def command_handler(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            return await func(update, context)
        except Exception as e:
            logger.error(f"Ошибка в {func.__name__}: {e}", exc_info=True)
            try:
                if update.message:
                    await update.message.reply_text("⚠️ Ошибка выполнения команды")
                elif update.callback_query:
                    await update.callback_query.message.reply_text("⚠️ Ошибка выполнения команды")
            except:
                pass
    return wrapper

def chat_only(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_chat.type == "private":
            message = update.message or (update.callback_query and update.callback_query.message)
            if message:
                await message.reply_text("Эта команда работает только в группах!")
            return
        return await func(update, context)
    return wrapper

def format_num(num): 
    return f"{num:,}".replace(",", " ")

def calc_level(cnt):
    if cnt <= 0: 
        return {'level': 1, 'progress': 0, 'min': 10, 'max': 25, 'next': 10}
    
    lvl = (cnt // 10) + 1
    prog = (cnt % 10) * 10
    
    if lvl > 1000:
        min_dmg = 10 + 1000 * 2 + (lvl - 1000) * 1
        max_dmg = 15 + 1000 * 3 + (lvl - 1000) * 2
    else:
        min_dmg = int(10 * (1.02 ** min(lvl - 1, 100)))
        max_dmg = int(20 * (1.08 ** min(lvl - 1, 100)))
    
    if max_dmg <= min_dmg: 
        max_dmg = min_dmg + 10
    
    return {
        'level': lvl,
        'progress': prog,
        'min': min_dmg,
        'max': max_dmg,
        'next': 10 - (cnt % 10) if (cnt % 10) < 10 else 0
    }

def level_title(lvl):
    if lvl >= 1000: return ("🌌 ВСЕЛЕНСКИЙ ШЛЁПКО-БОГ", "Ты создал свою вселенную шлёпков!")
    if lvl >= 950: return ("⚡ АБСОЛЮТНЫЙ ПОВЕЛИТЕЛЬ", "Даже боги трепещут перед тобой!")
    if lvl >= 900: return ("🔥 БЕССМЕРТНЫЙ ТИТАН", "Твоя сила преодолела смерть!")
    if lvl >= 850: return ("🌟 ХРАНИТЕЛЬ ГАЛАКТИКИ", "Целые галактики под твоей властью!")
    if lvl >= 800: return ("👑 ВЛАСТЕЛИН ВСЕХ ИЗМЕРЕНИЙ", "Пространство и время подчиняются тебе!")
    if lvl >= 750: return ("💎 БОЖЕСТВЕННЫЙ АРХИТЕКТОР", "Ты строишь реальность шлёпками!")
    if lvl >= 700: return ("⭐ ВЕЧНЫЙ ИМПЕРАТОР", "Твоя империя будет существовать вечно!")
    if lvl >= 650: return ("🌠 КОСМИЧЕСКИЙ ДЕМИУРГ", "Создаёшь звёзды одним шлёпком!")
    if lvl >= 600: return ("⚡ ПРЕВОСХОДНЫЙ БОГО-ЦАРЬ", "Ты — высшая форма существования!")
    if lvl >= 550: return ("🔥 МИРОТВОРЕЦ ВСЕЛЕННОЙ", "Твоим шлёпком устанавливается мир!")
    if lvl >= 500: return ("🌟 ВЕРХОВНЫЙ БОГ ШЛЁПКОВ", "Тебе поклоняются миллионы!")
    if lvl >= 450: return ("👑 НЕБЕСНЫЙ ПАТРИАРХ", "Твоя династия будет править вечно!")
    if lvl >= 400: return ("💎 ЗВЁЗДНЫЙ МОНАРХ", "Царствуешь среди звёзд!")
    if lvl >= 350: return ("⭐ ГАЛАКТИЧЕСКИЙ ИМПЕРАТОР", "Подчинена целая галактика!")
    if lvl >= 300: return ("🌠 ПОВЕЛИТЕЛЬ ТЫСЯЧИ МИРОВ", "Миллионы планет под твоим контролем!")
    if lvl >= 250: return ("⚡ БОЖЕСТВЕННЫЙ ВЛАСТЕЛИН", "Ты достиг божественного статуса!")
    if lvl >= 200: return ("🔥 ЦАРЬ ВСЕХ ШЛЁПКОВ", "Коронация состоялась!")
    if lvl >= 150: return ("🌟 ЛЕГЕНДАРНЫЙ ИМПЕРАТОР", "Твоё имя войдёт в легенды!")
    if lvl >= 100: return ("👑 ВЕЛИКИЙ ПОВЕЛИТЕЛЬ", "Власть над континентами!")
    if lvl >= 50: return ("💎 МАГИСТР ШЛЁПКОВ", "Уважаемый мастер!")
    if lvl >= 20: return ("⭐ ПРОФЕССИОНАЛ", "Уже что-то получается!")
    if lvl >= 10: return ("🔥 УВЕРЕННЫЙ НОВИЧОК", "Начинаешь понимать основы!")
    if lvl >= 5: return ("👊 ЗЕЛЁНЫЙ САЛАГ", "Ещё путаешься, но стараешься!")
    return ("🌱 ПОЛНЫЙ ДОХЛЯК", "Ты только начал... очень слабо!")

def get_reaction(): 
    return random.choice(MISHOK_REACTIONS)

async def get_message_from_update(update: Update):
    return update.message or (update.callback_query and update.callback_query.message)

@command_handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await get_message_from_update(update)
    if not msg:
        return
    
    safe_name = escape_markdown(update.effective_user.first_name, version=1)
    
    text = f"""👋 Привет, {safe_name}!
Я — Мишок Лысый 👴✨
Команды:
/shlep — Шлёпнуть
/stats — Статистика  
/level — Уровень
/my_stats — Детально
/trends — Тренды
Для чатов: /chat_stats, /chat_top, /vote, /duel
Начни: /shlep"""
    
    if update.effective_chat.type == "private":
        kb = get_game_keyboard()
    else:
        kb = get_inline_keyboard()
    
    await msg.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)

@command_handler
async def shlep(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await get_message_from_update(update)
    if not msg:
        return
    
    user = update.effective_user
    chat = update.effective_chat
    
    username = user.username or user.first_name
    _, cnt, _ = get_user_stats(user.id)
    lvl = calc_level(cnt)
    
    dmg = random.randint(lvl['min'], lvl['max'])
    total, cnt, max_dmg = add_shlep(
        user.id, 
        username, 
        dmg, 
        chat.id if chat.type != "private" else None
    )
    
    await cache.delete("global_stats")
    await cache.delete(f"user_stats_{user.id}")
    if chat.type != "private":
        await cache.delete(f"chat_stats_{chat.id}")
    
    rec = "\n🏆 НОВЫЙ РЕКОРД!\n" if dmg > max_dmg else ""
    lvl = calc_level(cnt)
    title, _ = level_title(lvl['level'])
    
    text = f"""{get_reaction()}{rec}💥 Урон: {dmg}
👤 {user.first_name}: {cnt} шлёпков
🎯 Уровень {lvl['level']} ({title})
📊 До уровня: {lvl['next']}
⚡ Диапазон урона: {lvl['min']}-{lvl['max']}
📈 Всего шлёпков в игре: {format_num(total)}"""
    
    kb = get_chat_quick_actions() if chat.type != "private" else None
    await msg.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)

@command_handler 
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await get_message_from_update(update)
    if not msg:
        return
    
    cached = await cache.get("global_stats")
    if cached:
        total, last, maxd, maxu, maxdt = cached
    else:
        total, last, maxd, maxu, maxdt = get_stats()
        await cache.set("global_stats", (total, last, maxd, maxu, maxdt))
    
    top = get_top_users(10)
    
    maxu_safe = escape_markdown(maxu or 'Нет', version=1)
    
    text = f"""📊 ГЛОБАЛЬНАЯ СТАТИСТИКА
👑 РЕКОРД УРОНА: {maxd} единиц
👤 Рекордсмен: {maxu_safe}
📅 Дата рекорда: {maxdt.strftime('%d.%m.%Y %H:%M') if maxdt else '—'}
🔢 Всего шлёпков: {format_num(total)}
⏰ Последний шлёпок: {last.strftime('%d.%m.%Y %H:%M') if last else 'нет'}"""
    
    if top:
        text += "\n\n🏆 ТОП ШЛЁПАТЕЛЕЙ:\n"
        for i, (u, c) in enumerate(top[:5], 1):
            u_safe = escape_markdown(u or f'Игрок{i}', version=1)
            lvl = calc_level(c)
            medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else ""
            text += f"\n{medal}{i}. {u_safe}"
            text += f"\n   📊 {format_num(c)} | Ур. {lvl['level']}"
            text += f"\n   ⚡ Урон: {lvl['min']}-{lvl['max']}"
    
    await msg.reply_text(text, parse_mode=ParseMode.MARKDOWN)

@command_handler 
async def level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await get_message_from_update(update)
    if not msg:
        return
    
    user = update.effective_user
    
    cached = await cache.get(f"user_stats_{user.id}")
    if cached:
        u, cnt, last = cached
    else:
        u, cnt, last = get_user_stats(user.id)
        await cache.set(f"user_stats_{user.id}", (u, cnt, last))
    
    lvl = calc_level(cnt)
    title, advice = level_title(lvl['level'])
    bar = "█" * min(lvl['progress'] // 10, 10) + "░" * (10 - min(lvl['progress'] // 10, 10))
    
    safe_name = escape_markdown(user.first_name, version=1)
    safe_advice = escape_markdown(advice, version=1)
    
    text = f"""🎯 ТВОЙ УРОВЕНЬ
👤 Игрок: {safe_name}
📊 Шлёпков: {format_num(cnt)}
🎯 Уровень: {lvl['level']} ({escape_markdown(title, version=1)}) 
{bar} {lvl['progress']}%
⚡ Диапазон урона: {lvl['min']}-{lvl['max']}
🎯 До след. уровня: {lvl['next']} шлёпков
💡 {safe_advice}"""
    
    if last:
        text += f"\n⏰ Последний шlёпок: {last.strftime('%d.%m.%Y %H:%M')}"
    
    await msg.reply_text(text, parse_mode=ParseMode.MARKDOWN)

@command_handler
async def my_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await get_message_from_update(update)
    if not msg:
        return
    
    user = update.effective_user
    
    _, cnt, last = get_user_stats(user.id)
    lvl = calc_level(cnt)
    compare_stats = get_comparison_stats(user.id)
    
    safe_name = escape_markdown(user.first_name, version=1)
    
    text = f"""📈 ТВОЯ ДЕТАЛЬНАЯ СТАТИСТИКА
👤 Игрок: {safe_name}
📊 Всего шlёпков: {format_num(cnt)}
🎯 Уровень: {lvl['level']}
⚡ Диапазон урона: {lvl['min']}-{lvl['max']}
{get_favorite_time(user.id)}
📊 Сравнение с другими:
👥 Всего игроков: {compare_stats.get('total_users', 0)}
📈 Среднее на игрока: {compare_stats.get('avg_shleps', 0)}
🏆 Твой ранг: {compare_stats.get('rank', 1)}
📊 Лучше чем: {compare_stats.get('percentile', 0)}% игроков
📅 Активность за неделю:
{format_daily_activity_chart(user.id, 7)}"""
    
    if last:
        text += f"\n⏰ Последний шлёпок: {last.strftime('%d.%m.%Y %H:%M')}"
    
    await msg.reply_text(text, parse_mode=ParseMode.MARKDOWN)

@command_handler
async def trends(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await get_message_from_update(update)
    if not msg:
        return
    
    trends_data = get_global_trends_info()
    
    if not trends_data:
        await msg.reply_text("📊 Данные временно недоступны")
        return
    
    text = f"""📊 ГЛОБАЛЬНЫЕ ТРЕНДЫ
👥 Активных за 24 часа: {trends_data.get('active_users_24h', 0)}
👊 Шлёпков за 24 часа: {trends_data.get('shleps_24h', 0)}
📈 Среднее на игрока: {trends_data.get('avg_per_user_24h', 0)}
🔥 Активных сегодня: {trends_data.get('active_today', 0)}
⏰ Текущий час: {trends_data.get('current_hour', 0):02d}:00
👊 Шлёпков в этом часу: {trends_data.get('shleps_this_hour', 0)}"""
    
    await msg.reply_text(text, parse_mode=ParseMode.MARKDOWN)

@command_handler
async def detailed_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await get_message_from_update(update)
    if not msg:
        return
    
    user = update.effective_user
    
    _, cnt, _ = get_user_stats(user.id)
    
    safe_name = escape_markdown(user.first_name, version=1)
    
    text = f"""📊 РАСШИРЕННАЯ СТАТИСТИКА
👤 Игрок: {safe_name}
📊 Шлёпков: {format_num(cnt)}
{get_favorite_time(user.id)}
📅 Активность за 2 недели:
{format_daily_activity_chart(user.id, 14)}
{format_hourly_distribution_chart(user.id)}
Команды статистики:
/my_stats — Краткая статистика
/trends — Глобальные тренды
/stats — Общая статистика
/level — Уровень"""
    
    await msg.reply_text(text, parse_mode=ParseMode.MARKDOWN)

@command_handler
@chat_only
async def chat_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await get_message_from_update(update)
    if not msg:
        return
    
    chat = update.effective_chat
    
    cached = await cache.get(f"chat_stats_{chat.id}")
    if cached:
        cs = cached
    else:
        cs = get_chat_stats(chat.id)
        await cache.set(f"chat_stats_{chat.id}", cs)
    
    if not cs:
        text = "📊 СТАТИСТИКА ЧАТА\n\nВ этом чате ещё не было шлёпков!\nИспользуй /shlep чтобы стать первым! 🎯"
    else:
        max_user_safe = escape_markdown(cs.get('max_damage_user', 'Нет'), version=1)
        text = f"""📊 СТАТИСТИКА ЧАТА
👥 Участников: {cs.get('total_users', 0)}
👊 Всего шлёпков: {format_num(cs.get('total_shleps', 0))}
🏆 Рекорд урона: {cs.get('max_damage', 0)} единиц
👑 Рекордсмен: {max_user_safe}"""
    
    await msg.reply_text(text, parse_mode=ParseMode.MARKDOWN)

@command_handler
@chat_only
async def chat_top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await get_message_from_update(update)
    if not msg:
        return
    
    chat = update.effective_chat
    top = get_chat_top_users(chat.id, 10)
    
    if not top:
        await msg.reply_text("🏆 ТОП ЧАТА\n\nВ этом чате пока никто не шлёпал Мишка! Будь первым!")
        return
    
    text = "🏆 ТОП ШЛЁПАТЕЛЕЙ ЧАТА:\n\n"
    for i, (u, c) in enumerate(top, 1):
        u_safe = escape_markdown(u, version=1)
        lvl = calc_level(c)
        medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else ""
        text += f"{medal}{i}. {u_safe}\n"
        text += f"   📊 {format_num(c)} | Ур. {lvl['level']}\n"
        text += f"   ⚡ Урон: {lvl['min']}-{lvl['max']}\n\n"
    
    await msg.reply_text(text, parse_mode=ParseMode.MARKDOWN)

@command_handler
@chat_only
async def vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await get_message_from_update(update)
    if not msg:
        return
    
    question = " ".join(context.args) if context.args else "Шлёпнуть Мишка?"
    kb = get_chat_vote_keyboard()
    
    question_safe = escape_markdown(question, version=1)
    
    await msg.reply_text(
        f"🗳️ ГОЛОСОВАНИЕ\n\n{question_safe}\n\nГолосование длится 5 минут!",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb
    )
    
    logger.info(f"Голосование создано: {question} в чате {update.effective_chat.id}")

@command_handler
@chat_only
async def duel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await get_message_from_update(update)
    if not msg:
        return
    
    user = update.effective_user
    
    if context.args:
        target = ' '.join(context.args)
        target_safe = escape_markdown(target, version=1)
        user_safe = escape_markdown(user.first_name, version=1)
        text = f"""⚔️ ВЫЗОВ НА ДУЭЛЬ!
{user_safe} вызывает {target_safe} на дуэль шлёпков!
📜 Правила:
• 5 минут на дуэль
• Побеждает тот, кто сделает больше шлёпков
• Победитель получает бонус"""
    else:
        text = """⚔️ СИСТЕМА ДУЭЛЕЙ
Используй `/duel @username` чтобы вызвать кого-то на дуэль!
📜 Правила:
• Дуэль длится 5 минут
• Побеждает тот, кто сделает больше шlёпков
• Победитель получает специальную роль"""
    
    await msg.reply_text(text, parse_mode=ParseMode.MARKDOWN)

@command_handler
@chat_only
async def roles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await get_message_from_update(update)
    if not msg:
        return
    
    text = """👑 РОЛИ В ЧАТЕ
Как получить роли:
• 👑 Король шлёпков — быть топ-1 в чате
• 🎯 Самый меткий — нанести максимальный урон  
• ⚡ Спринтер — сделать 10+ шлёпков за 5 минут
• 💪 Силач — нанести урон 40+ единиц
Используй /chat_top чтобы увидеть текущих лидеров!"""
    await msg.reply_text(text, parse_mode=ParseMode.MARKDOWN)

@command_handler
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await get_message_from_update(update)
    if not msg:
        return
    
    text = """🆘 ПОМОЩЬ
Основные команды:
/start — Начало работы
/shlep — Шлёпнуть Мишка  
/stats — Глобальная статистика
/level — Твой уровень
/my_stats — Детальная статистика
/detailed_stats — Расширенная статистика
/trends — Глобальные тренды
/mishok — О Мишке
Для чатов:
/chat_stats — Статистика чата
/chat_top — Топ игроков чата
/vote — Голосование
/duel — Дуэль
/roles — Роли в чате
Теперь с сохранением прогресса! 💾"""
    await msg.reply_text(text, parse_mode=ParseMode.MARKDOWN)

@command_handler
async def mishok(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        msg = await get_message_from_update(update)
        if not msg:
            return
        
        mishok_safe = escape_markdown(MISHOK_INTRO, version=1)
        
        await msg.reply_text(
            mishok_safe,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
        logger.info(f"Команда 'О Мишке' выполнена для пользователя {update.effective_user.id}")
        
    except Exception as e:
        logger.error(f"Ошибка в mishok: {e}", exc_info=True)
        try:
            if update.message:
                await update.message.reply_text(
                    "ℹ️ Информация о Мишке:\n\nЯ — Мишок Лысый, бот для шлёпок! Используй /help для команд.",
                    parse_mode=ParseMode.MARKDOWN
                )
            elif update.callback_query:
                await update.callback_query.message.reply_text(
                    "ℹ️ Информация о Мишке:\n\nЯ — Мишок Лысый, бот для шлёпок!",
                    parse_mode=ParseMode.MARKDOWN
                )
        except Exception as e2:
            logger.error(f"Не удалось отправить сообщение об ошибке: {e2}")

@command_handler
async def backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await get_message_from_update(update)
    if not msg:
        return
    
    ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
    if update.effective_user.id != ADMIN_ID:
        await msg.reply_text("⚠️ Эта команда только для администраторов!")
        return
    
    ok, result = backup_database()
    await msg.reply_text("✅ Бэкап создан!" if ok else f"❌ Ошибка: {result}")

@command_handler
async def storage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await get_message_from_update(update)
    if not msg:
        return
    
    import os
    text = "📂 Информация о хранилище:\n"
    
    paths = [
        ("/root", "Основная папка"),
        ("/bothost", "Корень Bothost"),
        ("/bothost/storage", "Постоянное хранилище"),
        (os.path.join(os.path.dirname(__file__), "mishok_data.json"), "Файл данных"),
        ("/mnt/storage", "Основное хранилище (альтернативное)"),
        ("/data", "Общее хранилище")
    ]
    
    for p, d in paths:
        ex = os.path.exists(p)
        if ex and os.path.isfile(p):
            sz = os.path.getsize(p)
            text += f"{'✅' if ex else '❌'} {d}: {p} ({sz/1024:.1f} KB)\n"
        else:
            text += f"{'✅' if ex else '❌'} {d}: {p}\n"
    
    text += f"\n💾 Версия Бота: Bothost Storage Ready"
    await msg.reply_text(text, parse_mode=ParseMode.MARKDOWN)

@command_handler
async def check_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверить целостность данных"""
    msg = await get_message_from_update(update)
    if not msg:
        return
    
    try:
        result = check_data_integrity()
        
        text = "🔍 ПРОВЕРКА ЦЕЛОСТНОСТИ ДАННЫХ\n\n"
        text += f"📊 Статистика:\n"
        text += f"👥 Пользователей: {result['stats']['users']}\n"
        text += f"💬 Чатов: {result['stats']['chats']}\n"
        text += f"👊 Всего шлёпков: {result['stats']['total_shleps']}\n\n"
        
        if result['errors']:
            text += "❌ КРИТИЧЕСКИЕ ОШИБКИ:\n"
            for error in result['errors']:
                text += f"• {error}\n"
            text += "\n"
        else:
            text += "✅ Критических ошибок нет\n\n"
        
        if result['warnings']:
            text += "⚠️ ПРЕДУПРЕЖДЕНИЯ:\n"
            for warning in result['warnings'][:5]:  # Показываем первые 5
                text += f"• {warning}\n"
            if len(result['warnings']) > 5:
                text += f"... и ещё {len(result['warnings']) - 5} предупреждений\n"
        else:
            text += "✅ Предупреждений нет\n"
        
        await msg.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        await msg.reply_text(f"❌ Ошибка проверки: {str(e)}")

@command_handler
async def fix_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Исправить структуру данных"""
    from database import ensure_data_file
    
    msg = await get_message_from_update(update)
    if not msg:
        return
    
    # Только для админа
    ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
    if update.effective_user.id != ADMIN_ID:
        await msg.reply_text("⚠️ Эта команда только для администраторов!")
        return
    
    try:
        await msg.reply_text("🔄 Исправление структуры данных...")
        
        # Вызываем функцию исправления
        ensure_data_file()
        
        # Проверяем результат
        from database import load_data, get_stats
        data = load_data()
        total, last, maxd, maxu, maxdt = get_stats()
        
        text = "✅ СТРУКТУРА ДАННЫХ ИСПРАВЛЕНА\n\n"
        text += f"👥 Пользователей: {len(data.get('users', {}))}\n"
        text += f"💬 Чатов: {len(data.get('chats', {}))}\n"
        text += f"👊 Всего шлёпков: {total}\n"
        text += f"💥 Максимальный урон: {maxd}\n"
        text += f"👑 Рекордсмен: {maxu or 'Нет'}\n\n"
        text += "Бот теперь будет работать корректно с файлом /data/mishok_data.json"
        
        await msg.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        await msg.reply_text(f"❌ Ошибка исправления: {str(e)}")

@command_handler
async def data_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Информация о файле данных"""
    import os
    import json
    from datetime import datetime
    
    msg = await get_message_from_update(update)
    if not msg:
        return
    
    DATA_FILE = "/data/mishok_data.json"
    
    text = "📁 ИНФОРМАЦИЯ О ФАЙЛЕ ДАННЫХ\n\n"
    
    if os.path.exists(DATA_FILE):
        size = os.path.getsize(DATA_FILE)
        modified = datetime.fromtimestamp(os.path.getmtime(DATA_FILE))
        
        text += f"📍 Путь: {DATA_FILE}\n"
        text += f"📏 Размер: {size:,} байт\n".replace(",", " ")
        text += f"📅 Изменен: {modified.strftime('%d.%m.%Y %H:%M:%S')}\n"
        
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                text += f"\n📊 СОДЕРЖИМОЕ:\n"
                text += f"• Пользователей: {len(data.get('users', {}))}\n"
                text += f"• Чатов: {len(data.get('chats', {}))}\n"
                text += f"• Всего шлёпков: {data.get('global_stats', {}).get('total_shleps', 0)}\n"
                text += f"• Макс. урон: {data.get('global_stats', {}).get('max_damage', 0)}\n"
                text += f"• Записей в истории: {len(data.get('records', []))}\n"
                
                # Проверяем структуру
                required_keys = ["users", "chats", "global_stats", "timestamps", "records"]
                missing_keys = [k for k in required_keys if k not in data]
                if missing_keys:
                    text += f"\n⚠️ Отсутствуют ключи: {missing_keys}\n"
                else:
                    text += "\n✅ Структура корректна\n"
                    
        except Exception as e:
            text += f"\n❌ Ошибка чтения файла: {str(e)}\n"
    else:
        text += f"❌ Файл не найден: {DATA_FILE}\n"
        text += "Используйте /fix_data для создания файла с правильной структурой"
    
    await msg.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def handle_vote(update: Update, context: ContextTypes.DEFAULT_TYPE, vote_type: str):
    try:
        query = update.callback_query
        if not query:
            return
        
        user = update.effective_user
        username = user.username or user.first_name
        
        vote_texts = {
            "vote_yes": "👍 За",
            "vote_no": "👎 Против", 
            "vote_abstain": "🤷 Воздержаться"
        }
        
        vote_text = vote_texts.get(vote_type, "Неизвестно")
        
        original_text = query.message.text
        vote_line = f"• {username}: {vote_text}"
        
        if "Результаты:" not in original_text:
            new_text = original_text + f"\n\n📊 Результаты:\n{vote_line}"
        else:
            lines = original_text.split('\n')
            results_start = -1
            
            for i, line in enumerate(lines):
                if "Результаты:" in line:
                    results_start = i
                    break
            
            if results_start >= 0:
                user_voted = False
                for j in range(results_start + 1, len(lines)):
                    if username in lines[j]:
                        lines[j] = vote_line
                        user_voted = True
                        break
                
                if not user_voted:
                    lines.insert(results_start + 1, vote_line)
                
                new_text = '\n'.join(lines)
            else:
                new_text = original_text + f"\n\n📊 Результаты:\n{vote_line}"
        
        await query.message.edit_text(
            new_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_chat_vote_keyboard()
        )
        
        await query.answer(f"Ваш голос: {vote_text}", show_alert=False)
        
        logger.info(f"Голос зарегистрирован: {username} → {vote_text}")
        
    except Exception as e:
        logger.error(f"Ошибка обработки голоса: {e}", exc_info=True)
        try:
            await query.answer("❌ Ошибка при регистрации голоса", show_alert=True)
        except:
            pass

async def inline_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    
    await query.answer()
    data = query.data
    
    logger.info(f"Callback received: {data}")
    
    if data == "shlep_mishok":
        await shlep(update, context)
    elif data == "stats_inline":
        await stats(update, context)
    elif data == "level_inline":
        await level(update, context)
    elif data == "chat_top":
        await chat_top(update, context)
    elif data == "my_stats":
        await my_stats(update, context)
    elif data == "trends":
        await trends(update, context)
    elif data == "help_inline":
        await help_cmd(update, context)
    elif data == "mishok_info":
        await mishok(update, context)
    elif data in ["vote_yes", "vote_no", "vote_abstain"]:
        await handle_vote(update, context, data)
    elif data.startswith("quick_"):
        await quick_handler(update, context, data)
    else:
        await query.message.reply_text("⚙️ Эта функция в разработке")

async def quick_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    query = update.callback_query
    if not query:
        return
    
    await query.answer()
    
    if data == "quick_shlep":
        await shlep(update, context)
    elif data == "quick_stats":
        await chat_stats(update, context)
    elif data == "quick_level":
        await level(update, context)
    elif data == "quick_my_stats":
        await my_stats(update, context)
    elif data == "quick_trends":
        await trends(update, context)
    elif data == "quick_vote":
        await vote(update, context)
    elif data == "quick_duel":
        await duel(update, context)
    elif data == "quick_daily_top":
        await query.message.reply_text("📊 ТОП ДНЯ\n\nСобираем статистику...")
    else:
        await query.message.reply_text("⚙️ В разработке")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    
    if not update.message:
        return
    
    text = update.message.text
    logger.info(f"Button pressed: {text}")
    
    try:
        if text in ["👊 Шлёпнуть Мишка", "👊 Шлёпнуть", "Шлёпнуть Мишка"]:
            await shlep(update, context)
        elif text == "🎯 Уровень":
            await level(update, context)
        elif text == "📊 Статистика":
            await stats(update, context)
        elif text == "📈 Моя статистика":
            await my_stats(update, context)
        elif text == "📊 Тренды":
            await trends(update, context)
        elif text == "❓ Помощь":
            await help_cmd(update, context)
        elif text in ["👴 О Мишке", "О Мишке"]:
            await mishok(update, context)
        else:
            logger.warning(f"Неизвестная кнопка: {text}")
            await update.message.reply_text(
                "Неизвестная команда. Используйте /help для списка команд.",
                parse_mode=ParseMode.MARKDOWN
            )
    except Exception as e:
        logger.error(f"Ошибка в button_handler: {e}", exc_info=True)
        await update.message.reply_text(
            "⚠️ Произошла ошибка при обработке команды. Попробуйте ещё раз.",
            parse_mode=ParseMode.MARKDOWN
        )

async def group_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.new_chat_members:
        for m in update.message.new_chat_members:
            if m.id == context.bot.id:
                await update.message.reply_text(
                    "👴 Мишок Лысый в чате!\n\n"
                    "Теперь можно шлёпать меня по лысине прямо здесь!\n"
                    "Основные команды:\n"
                    "/shlep — шлёпнуть Мишка\n"
                    "/stats — статистика\n"
                    "/level — уровень\n"
                    "/my_stats — детальная статистика\n"
                    "Для чата:\n"
                    "/chat_stats — статистика чата\n"
                    "/chat_top — топ игроков\n"
                    "/vote — голосование\n"
                    "/duel — дуэль\n"
                    "Прогресс сохраняется! 💾",
                    parse_mode=ParseMode.MARKDOWN
                )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Ошибка: {context.error}", exc_info=True)

def main():
    if not BOT_TOKEN:
        logger.error("❌ Нет токена бота! Установите BOT_TOKEN в config.py или .env файле")
        sys.exit(1)
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    commands = [
        ("start", start),
        ("shlep", shlep),
        ("stats", stats),
        ("level", level),
        ("my_stats", my_stats),
        ("trends", trends),
        ("detailed_stats", detailed_stats),
        ("help", help_cmd),
        ("mishok", mishok),
        ("chat_stats", chat_stats),
        ("chat_top", chat_top),
        ("vote", vote),
        ("duel", duel),
        ("roles", roles),
        ("backup", backup),
        ("storage", storage),
        ("check_data", check_data),  # Новая команда
        ("fix_data", fix_data),      # Новая команда
        ("data_info", data_info),    # Новая команда
    ]
    
    for name, handler in commands:
        app.add_handler(CommandHandler(name, handler))
    
    app.add_handler(CallbackQueryHandler(inline_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, group_welcome))
    app.add_error_handler(error_handler)
    
    logger.info("=" * 50)
    logger.info("✅ Мишок Лысый запущен!")
    logger.info("=" * 50)
    
    print("\n" + "=" * 50)
    print("МИШОК ЛЫСЫЙ ЗАПУЩЕН!")
    print("=" * 50)
    print(f"• Токен: {'есть' if BOT_TOKEN else 'НЕТ!'}")
    print(f"• Команд: {len(commands)}")
    print(f"• Бот готов к работе!")
    print("=" * 50)
    
    try:
        app.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        )
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске бота: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
