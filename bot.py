import logging
import random
import sys
import os
import json
import asyncio
import re
from datetime import datetime, timedelta
from functools import wraps

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.constants import ParseMode
from telegram.helpers import escape_markdown

from config import BOT_TOKEN, MISHOK_REACTIONS, MISHOK_INTRO
from database import add_shlep, get_stats, get_top_users, get_user_stats, get_chat_stats, get_chat_top_users, backup_database, check_data_integrity, repair_data_structure, create_duel_invite, accept_duel_invite, decline_duel_invite, get_active_duel, add_shlep_to_duel, finish_duel, surrender_duel, get_user_active_duel, cleanup_expired_duels, update_duel_message_id, save_vote_data, get_vote_data, delete_vote_data, get_user_vote
from keyboard import get_shlep_session_keyboard, get_shlep_start_keyboard, get_chat_vote_keyboard, get_inline_keyboard, get_game_keyboard, get_duel_invite_keyboard, get_duel_active_keyboard, get_duel_finished_keyboard
from cache import cache
from statistics import get_favorite_time, get_comparison_stats, get_global_trends_info, format_daily_activity_chart, format_hourly_distribution_chart

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

VOTE_DATA_FILE = "data/votes.json"

shlep_sessions = {}

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
    if lvl >= 750: return ("💎 БОЖЕСТВЕННЫЙ АРХИТЕКТОР", "Ты строишь реальность шlёпками!")
    if lvl >= 700: return ("⭐ ВЕЧНЫЙ ИМПЕРАТОР", "Твоя империя будет существовать вечно!")
    if lvl >= 650: return ("🌠 КОСМИЧЕСКИЙ ДЕМИУРГ", "Создаёшь звёзды одним шlёпком!")
    if lvl >= 600: return ("⚡ ПРЕВОСХОДНЫЙ БОГО-ЦАРЬ", "Ты — высшая форма существования!")
    if lvl >= 550: return ("🔥 МИРОТВОРЕЦ ВСЕЛЕННОЙ", "Твоим шlёпком устанавливается мир!")
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

async def update_duel_message(context: ContextTypes.DEFAULT_TYPE, duel_id: str, 
                            chat_id: int = None, message_id: int = None):
    duel = get_active_duel(duel_id)
    
    if not duel and chat_id and message_id:
        from database import load_data
        data = load_data()
        
        for hist_duel in data.get("duels", {}).get("history", []):
            if hist_duel.get("id") == duel_id:
                duel = hist_duel
                break
        
        if not duel:
            return False
    
    if not duel:
        return False
    
    ends_at = datetime.fromisoformat(duel["ends_at"])
    now = datetime.now()
    
    if now >= ends_at and "finished_at" not in duel:
        result = finish_duel(duel_id)
        duel = get_active_duel(duel_id) or duel
    
    remaining = (ends_at - now).seconds if now < ends_at else 0
    minutes = remaining // 60
    seconds = remaining % 60
    
    total_damage = duel["challenger_damage"] + duel["target_damage"]
    
    if total_damage > 0:
        challenger_percent = (duel["challenger_damage"] / total_damage) * 100
        target_percent = (duel["target_damage"] / total_damage) * 100
    else:
        challenger_percent = 50
        target_percent = 50
    
    bar_length = 20
    challenger_bar = "█" * int(challenger_percent / 100 * bar_length)
    target_bar = "█" * int(target_percent / 100 * bar_length)
    
    def format_damage(dmg):
        return f"{dmg:,}".replace(",", " ")
    
    if duel["challenger_damage"] > duel["target_damage"]:
        leader = f"👑 {duel['challenger_name']} лидирует!"
    elif duel["target_damage"] > duel["challenger_damage"]:
        leader = f"👑 {duel['target_name']} лидирует!"
    else:
        leader = "⚖️ Ничья!"
    
    if "finished_at" in duel or now >= ends_at:
        if duel.get("winner_name"):
            result_text = f"🏆 ПОБЕДИТЕЛЬ: {duel['winner_name']}!\n🎯 Награда: +{duel.get('reward', 0)} к урону\n\n"
        else:
            result_text = "🤝 НИЧЬЯ!\n\n"
        
        text = (
            f"⚔️ ДУЭЛЬ ЗАВЕРШЕНА\n\n"
            f"{result_text}"
            f"Итоговый счёт:\n"
            f"👤 {duel['challenger_name']}:\n"
            f"   🔥 Урон: {format_damage(duel['challenger_damage'])}\n"
            f"   👊 Шлёпков: {duel['challenger_shleps']}\n"
            f"   📊 Средний урон: {format_damage(duel['challenger_damage'] // max(duel['challenger_shleps'], 1))}\n\n"
            f"👤 {duel['target_name']}:\n"
            f"   🔥 Урон: {format_damage(duel['target_damage'])}\n"
            f"   👊 Шлёпков: {duel['target_shleps']}\n"
            f"   📊 Средний урон: {format_damage(duel['target_damage'] // max(duel['target_shleps'], 1))}\n\n"
            f"⏱️ Длительность: 5 минут\n"
            f"📈 Общий урон: {format_damage(total_damage)}"
        )
        
        kb = get_duel_finished_keyboard(duel_id)
    else:
        text = (
            f"⚔️ ДУЭЛЬ В РЕАЛЬНОМ ВРЕМЕНИ\n\n"
            f"{leader}\n\n"
            f"Прогресс:\n"
            f"👤 {duel['challenger_name']}:\n"
            f"   {challenger_bar} {challenger_percent:.1f}%\n"
            f"   🔥 Урон: {format_damage(duel['challenger_damage'])}\n"
            f"   👊 Шлёпков: {duel['challenger_shleps']}\n\n"
            f"👤 {duel['target_name']}:\n"
            f"   {target_bar} {target_percent:.1f}%\n"
            f"   🔥 Урон: {format_damage(duel['target_damage'])}\n"
            f"   👊 Шлёпков: {duel['target_shleps']}\n\n"
            f"⏱️ Осталось времени: {minutes:02d}:{seconds:02d}\n"
            f"🎯 Награда: +{duel['reward']} к урону победителю\n"
            f"📊 Общий урон: {format_damage(total_damage)}"
        )
        
        if duel.get("history"):
            text += "\n\nПоследние действия:\n"
            for action in duel["history"][-3:]:
                time_ago = (now - datetime.fromisoformat(action["timestamp"])).seconds
                text += f"• {action['user_name']}: {format_damage(action['damage'])} урона ({time_ago} сек назад)\n"
        
        kb = get_duel_active_keyboard(duel_id)
    
    try:
        if message_id and chat_id:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=kb
            )
            return True
        elif chat_id and duel.get("message_id"):
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=duel["message_id"],
                text=text,
                reply_markup=kb
            )
            return True
    except Exception as e:
        logger.error(f"Ошибка обновления сообщения дуэли: {e}")
    
    return False

async def perform_shlep(update: Update, context: ContextTypes.DEFAULT_TYPE, edit_message=None):
    try:
        user = update.effective_user
        chat = update.effective_chat
        
        username = user.username or user.first_name
        _, cnt, _ = get_user_stats(user.id)
        lvl = calc_level(cnt)
        
        base_dmg = random.randint(lvl['min'], lvl['max'])
        
        from database import load_data
        data = load_data()
        user_data = data["users"].get(str(user.id), {})
        bonus_damage = user_data.get("bonus_damage", 0)
        
        total_damage = base_dmg + bonus_damage
        
        from database import get_user_active_duel, add_shlep_to_duel
        active_duel = get_user_active_duel(user.id)
        
        duel_result = None
        if active_duel:
            duel_result = add_shlep_to_duel(active_duel["id"], user.id, total_damage)
            
            if active_duel.get("message_id") and active_duel.get("chat_id"):
                await update_duel_message(context, active_duel["id"], 
                                        active_duel["chat_id"], active_duel["message_id"])
        
        try:
            total, cnt, max_dmg = add_shlep(
                user.id, 
                username, 
                total_damage, 
                chat.id if chat.type != "private" else None
            )
        except KeyError as e:
            repair_data_structure()
            
            total, cnt, max_dmg = add_shlep(
                user.id, 
                username, 
                total_damage, 
                chat.id if chat.type != "private" else None
            )
        
        await cache.delete("global_stats")
        await cache.delete(f"user_stats_{user.id}")
        if chat.type != "private":
            await cache.delete(f"chat_stats_{chat.id}")
        
        rec = "\n🏆 НОВЫЙ РЕКОРД!\n" if total_damage > max_dmg else ""
        lvl = calc_level(cnt)
        title, _ = level_title(lvl['level'])
        
        duel_info = ""
        if active_duel:
            opponent = active_duel["target_name"] if user.id == active_duel["challenger_id"] else active_duel["challenger_name"]
            duel_info = f"\n⚔️ Дуэль с {opponent}: +{total_damage} урона"
            if bonus_damage > 0:
                duel_info += f" ({base_dmg} + {bonus_damage} бонус)"
        
        text = f"{get_reaction()}{rec}{duel_info}\n💥 Урон: {total_damage}\n👤 {user.first_name}: {cnt} шлёпков\n🎯 Уровень {lvl['level']} ({title})\n📊 До уровня: {lvl['next']}\n⚡ Диапазон урона: {lvl['min']}-{lvl['max']}\n📈 Всего шлёпков в игре: {format_num(total)}"
        
        kb = get_shlep_session_keyboard()
        
        if edit_message:
            try:
                await edit_message.edit_text(text, reply_markup=kb)
                return edit_message
            except Exception as e:
                logger.warning(f"Не удалось отредактировать сообщение: {e}")
                return await edit_message.reply_text(text, reply_markup=kb)
        else:
            msg = await get_message_from_update(update)
            if msg:
                return await msg.reply_text(text, reply_markup=kb)
        
    except Exception as e:
        logger.error(f"Ошибка в perform_shlep: {e}", exc_info=True)
        msg = await get_message_from_update(update)
        if msg:
            await msg.reply_text("⚠️ Произошла ошибка при обработке шлёпка. Попробуйте еще раз.")

@command_handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await get_message_from_update(update)
    if not msg:
        return
    
    safe_name = escape_markdown(update.effective_user.first_name, version=1)
    
    text = f"👋 Привет, {safe_name}!\nЯ — Мишок Лысый 👴✨\n\n"
    
    if update.effective_chat.type == "private":
        text += """Начни шлёпать прямо сейчас!

Просто нажми кнопку ниже или используй команды:

👊 /shlep — Шлёпнуть Мишка
📊 /stats — Глобальная статистика
🎯 /level — Твой уровень и прогресс
📈 /my_stats — Детальная статистика
📊 /trends — Глобальные тренды
❓ /help — Помощь по командам
👴 /mishok — О Мишке

Новая фича: Теперь шлёпай в одном окне без спама сообщений!"""
        
        kb = get_shlep_start_keyboard()
        await msg.reply_text(text, reply_markup=kb)
    else:
        text += """Я бот для шлёпков!

Команды для чата:
👊 /shlep — Шлёпнуть Мишка
📊 /chat_stats — Статистика чата
🏆 /chat_top — Топ игроков
🗳️ /vote [вопрос] — Голосование
⚔️ /duel @username — Дуэль
👑 /roles — Роли в чате

Личные команды (в лс с ботом):
📊 /stats — Глобальная статистика
🎯 /level — Твой уровень
📈 /my_stats — Детальная статистика

Нажми кнопку ниже или введи команду!"""
        
        kb = get_inline_keyboard()
        await msg.reply_text(text, reply_markup=kb)

@command_handler
async def shlep(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await perform_shlep(update, context)

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
    
    text = f"📊 ГЛОБАЛЬНАЯ СТАТИСТИКА\n👑 РЕКОРД УРОНА: {maxd} единиц\n👤 Рекордсмен: {maxu_safe}\n📅 Дата рекорда: {maxdt.strftime('%d.%m.%Y %H:%M') if maxdt else '—'}\n🔢 Всего шlёпков: {format_num(total)}\n⏰ Последний шlёпок: {last.strftime('%d.%m.%Y %H:%M') if last else 'нет'}"
    
    if top:
        text += "\n\n🏆 ТОП ШЛЁПАТЕЛЕЙ:\n"
        for i, (u, c) in enumerate(top[:5], 1):
            u_safe = escape_markdown(u or f'Игрок{i}', version=1)
            lvl = calc_level(c)
            medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else ""
            text += f"\n{medal}{i}. {u_safe}"
            text += f"\n   📊 {format_num(c)} | Ур. {lvl['level']}"
            text += f"\n   ⚡ Урон: {lvl['min']}-{lvl['max']}"
    
    await msg.reply_text(text)

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
    
    text = f"🎯 ТВОЙ УРОВЕНЬ\n👤 Игрок: {safe_name}\n📊 Шlёпков: {format_num(cnt)}\n🎯 Уровень: {lvl['level']} ({title})\n{bar} {lvl['progress']}%\n⚡ Диапазон урона: {lvl['min']}-{lvl['max']}\n🎯 До след. уровня: {lvl['next']} шlёпков\n💡 {advice}"
    
    if last:
        text += f"\n⏰ Последний шlёпок: {last.strftime('%d.%m.%Y %H:%M')}"
    
    await msg.reply_text(text)

@command_handler
async def my_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await get_message_from_update(update)
    if not msg:
        return
    
    user = update.effective_user
    
    _, cnt, last = get_user_stats(user.id)
    lvl = calc_level(cnt)
    compare_stats = get_comparison_stats(user.id)
    
    text = f"📈 ТВОЯ ДЕТАЛЬНАЯ СТАТИСТИКА\n👤 Игрок: {user.first_name}\n📊 Всего шlёпков: {format_num(cnt)}\n🎯 Уровень: {lvl['level']}\n⚡ Диапазон урона: {lvl['min']}-{lvl['max']}\n{get_favorite_time(user.id)}\n📊 Сравнение с другими:\n👥 Всего игроков: {compare_stats.get('total_users', 0)}\n📈 Среднее на игрока: {compare_stats.get('avg_shleps', 0)}\n🏆 Твой ранг: {compare_stats.get('rank', 1)}\n📊 Лучше чем: {compare_stats.get('percentile', 0)}% игроков\n📅 Активность за неделю:\n{format_daily_activity_chart(user.id, 7)}"
    
    if last:
        text += f"\n⏰ Последний шlёпок: {last.strftime('%d.%m.%Y %H:%M')}"
    
    await msg.reply_text(text)

@command_handler
async def trends(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await get_message_from_update(update)
    if not msg:
        return
    
    trends_data = get_global_trends_info()
    
    if not trends_data:
        await msg.reply_text("📊 Данные временно недоступны")
        return
    
    text = f"📊 ГЛОБАЛЬНЫЕ ТРЕНДЫ\n👥 Активных за 24 часа: {trends_data.get('active_users_24h', 0)}\n👊 Шlёпков за 24 часа: {trends_data.get('shleps_24h', 0)}\n📈 Среднее на игрока: {trends_data.get('avg_per_user_24h', 0)}\n🔥 Активных сегодня: {trends_data.get('active_today', 0)}\n⏰ Текущий час: {trends_data.get('current_hour', 0):02d}:00\n👊 Шlёпков в этом часу: {trends_data.get('shleps_this_hour', 0)}"
    
    await msg.reply_text(text)

@command_handler
async def detailed_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await get_message_from_update(update)
    if not msg:
        return
    
    user = update.effective_user
    
    _, cnt, _ = get_user_stats(user.id)
    
    text = f"📊 РАСШИРЕННАЯ СТАТИСТИКА\n👤 Игрок: {user.first_name}\n📊 Шlёпков: {format_num(cnt)}\n{get_favorite_time(user.id)}\n📅 Активность за 2 недели:\n{format_daily_activity_chart(user.id, 14)}\n{format_hourly_distribution_chart(user.id)}\n\nКоманды статистики:\n/my_stats — Краткая статистика\n/trends — Глобальные тренды\n/stats — Общая статистика\n/level — Уровень"
    
    await msg.reply_text(text)

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
        text = "📊 СТАТИСТИКА ЧАТА\n\nВ этом чате ещё не было шlёпков!\nИспользуй /shlep чтобы стать первым! 🎯"
    else:
        max_user_safe = escape_markdown(cs.get('max_damage_user', 'Нет'), version=1)
        text = f"📊 СТАТИСТИКА ЧАТА\n👥 Участников: {cs.get('total_users', 0)}\n👊 Всего шlёпков: {format_num(cs.get('total_shleps', 0))}\n🏆 Рекорд урона: {cs.get('max_damage', 0)} единиц\n👑 Рекордсмен: {max_user_safe}"
    
    await msg.reply_text(text)

@command_handler
@chat_only
async def chat_top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await get_message_from_update(update)
    if not msg:
        return
    
    chat = update.effective_chat
    top = get_chat_top_users(chat.id, 10)
    
    if not top:
        await msg.reply_text("🏆 ТОП ЧАТА\n\nВ этом чате пока никто не шlёпал Мишка! Будь первым!")
        return
    
    text = "🏆 ТОП ШЛЁПАТЕЛЕЙ ЧАТА:\n\n"
    for i, (u, c) in enumerate(top, 1):
        u_safe = escape_markdown(u, version=1)
        lvl = calc_level(c)
        medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else ""
        text += f"{medal}{i}. {u_safe}\n"
        text += f"   📊 {format_num(c)} | Ур. {lvl['level']}\n"
        text += f"   ⚡ Урон: {lvl['min']}-{lvl['max']}\n\n"
    
    await msg.reply_text(text)

async def vote_timer(vote_id, chat_id, message_id, context):
    try:
        await asyncio.sleep(300)
        await finish_vote(vote_id, chat_id, message_id, context)
    except Exception as e:
        logger.error(f"Ошибка в таймере голосования: {e}")

async def finish_vote(vote_id, chat_id, message_id, context):
    vote_data = get_vote_data(vote_id)
    if not vote_data or vote_data.get("finished", False):
        return
    vote_data["finished"] = True
    vote_data["finished_at"] = datetime.now().isoformat()
    save_vote_data(vote_data)
    yes_count = len(vote_data.get("votes_yes", []))
    no_count = len(vote_data.get("votes_no", []))
    total_votes = yes_count + no_count
    if total_votes == 0:
        result_text = "🤷 *НИКТО НЕ ПРОГОЛОСОВАЛ!*\nНикто не решил судьбу моей лысины... 😔"
        action_text = ""
    elif yes_count > no_count:
        result_text = "✅ *БОЛЬШИНСТВО ЗА!*\nНарод решил: шлёпать надо!"
        action_text = "\n\n👊 *ДАВАЙТЕ НАШЛЁПАЕМ ЭТОМУ ЛЫСОМУ!*"
        asyncio.create_task(
            context.bot.send_message(
                chat_id=chat_id,
                text="👴 *Мишок:* Ой-ой, народ решил меня отшлёпать! Принимаю свою судьбу! 👊"
            )
        )
    elif no_count > yes_count:
        result_text = "❌ *БОЛЬШИНСТВО ПРОТИВ!*\nНарод пощадил мою лысину!"
        action_text = "\n\n🙏 *СПАСИБО ЗА МИЛОСЕРДИЕ!*"
    else:
        result_text = "⚖️ *НИЧЬЯ!*\nГолоса разделились поровну!"
        action_text = "\n\n🤔 *САМ РЕШАЙ, ШЛЁПАТЬ ИЛИ НЕТ!*"
    try:
        text = (
            f"🗳️ *ГОЛОСОВАНИЕ ЗАВЕРШЕНО*\n\n"
            f"*Вопрос:* {vote_data['question']}\n\n"
            f"📊 *Результаты:*\n"
            f"✅ За: {yes_count} голосов\n"
            f"❌ Против: {no_count} голосов\n"
            f"👥 Всего проголосовало: {total_votes}\n\n"
            f"{result_text}{action_text}"
        )
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=None
        )
        logger.info(f"Голосование завершено: {vote_id}, результат: {result_text}")
    except Exception as e:
        logger.error(f"Ошибка обновления сообщения голосования: {e}")

@command_handler
@chat_only
async def vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await get_message_from_update(update)
    if not msg:
        return
    question = " ".join(context.args) if context.args else "Шлёпнуть Мишка?"
    kb = get_chat_vote_keyboard()
    question_safe = escape_markdown(question, version=1)
    vote_id = f"{msg.chat_id}_{msg.message_id}_{int(datetime.now().timestamp())}"
    vote_data = {
        "id": vote_id,
        "chat_id": msg.chat_id,
        "message_id": msg.message_id,
        "question": question,
        "votes_yes": [],
        "votes_no": [],
        "started_at": datetime.now().isoformat(),
        "ends_at": (datetime.now() + timedelta(minutes=5)).isoformat(),
        "finished": False
    }
    save_vote_data(vote_data)
    asyncio.create_task(vote_timer(vote_id, msg.chat_id, msg.message_id, context))
    text = (
        f"🗳️ *ГОЛОСОВАНИЕ*\n\n"
        f"*Вопрос:* {question_safe}\n\n"
        f"✅ *За:* 0\n"
        f"❌ *Против:* 0\n\n"
        f"⏰ *Голосование длится 5 минут!*\n"
        f"🆔 `{vote_id}`"
    )
    sent_message = await msg.reply_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
    vote_data["message_id"] = sent_message.message_id
    save_vote_data(vote_data)
    logger.info(f"Голосование создано: {question} в чате {msg.chat_id}, ID: {vote_id}")

@command_handler
@chat_only
async def vote_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await get_message_from_update(update)
    if not msg:
        return
    chat_id = msg.chat_id
    try:
        with open(VOTE_DATA_FILE, 'r', encoding='utf-8') as f:
            all_votes = json.load(f)
        active_votes = []
        now = datetime.now()
        for vote_id, vote_data in all_votes.items():
            if (vote_data.get("chat_id") == chat_id and 
                not vote_data.get("finished", False) and
                datetime.fromisoformat(vote_data["ends_at"]) > now):
                active_votes.append(vote_data)
        if not active_votes:
            text = "🗳️ *АКТИВНЫЕ ГОЛОСОВАНИЯ*\n\nВ этом чате нет активных голосований.\n\nСоздать новое: `/vote [вопрос]`"
        else:
            text = "🗳️ *АКТИВНЫЕ ГОЛОСОВАНИЯ В ЧАТЕ:*\n\n"
            for i, vote in enumerate(active_votes[:5], 1):
                ends_at = datetime.fromisoformat(vote["ends_at"])
                remaining = (ends_at - now).seconds
                minutes = remaining // 60
                seconds = remaining % 60
                yes_count = len(vote.get("votes_yes", []))
                no_count = len(vote.get("votes_no", []))
                text += f"{i}. *{vote['question'][:30]}...*\n"
                text += f"   ✅ {yes_count} | ❌ {no_count}\n"
                text += f"   ⏰ Осталось: {minutes:02d}:{seconds:02d}\n"
                text += f"   🆔 `{vote['id']}`\n\n"
        await msg.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Ошибка получения информации о голосованиях: {e}")
        await msg.reply_text("❌ Ошибка при получении информации о голосованиях")

async def handle_vote(update: Update, context: ContextTypes.DEFAULT_TYPE, vote_type: str):
    try:
        query = update.callback_query
        if not query:
            return
        user = update.effective_user
        user_id = str(user.id)
        message_text = query.message.text
        vote_id = None
        match = re.search(r'🆔 `([^`]+)`', message_text)
        if match:
            vote_id = match.group(1)
        if not vote_id:
            lines = message_text.split('\n')
            for line in lines:
                if '🆔' in line or 'ID:' in line:
                    parts = line.split()
                    for part in parts:
                        if len(part) > 10 and '_' in part:
                            vote_id = part.strip('`')
                            break
        if not vote_id:
            await query.answer("❌ Не удалось определить голосование", show_alert=True)
            return
        vote_data = get_vote_data(vote_id)
        if not vote_data:
            await query.answer("❌ Голосование не найдено", show_alert=True)
            return
        if vote_data.get("finished", False):
            await query.answer("❌ Голосование уже завершено", show_alert=True)
            return
        current_vote = get_user_vote(vote_id, user.id)
        if current_vote:
            if current_vote == "yes" and user_id in vote_data["votes_yes"]:
                vote_data["votes_yes"].remove(user_id)
            elif current_vote == "no" and user_id in vote_data["votes_no"]:
                vote_data["votes_no"].remove(user_id)
        if vote_type == "vote_yes":
            vote_data["votes_yes"].append(user_id)
            vote_text = "👍 За"
        else:
            vote_data["votes_no"].append(user_id)
            vote_text = "👎 Против"
        save_vote_data(vote_data)
        yes_count = len(vote_data.get("votes_yes", []))
        no_count = len(vote_data.get("votes_no", []))
        total_votes = yes_count + no_count
        ends_at = datetime.fromisoformat(vote_data["ends_at"])
        now = datetime.now()
        if now < ends_at:
            remaining = (ends_at - now).seconds
            minutes = remaining // 60
            seconds = remaining % 60
            time_left = f"{minutes:02d}:{seconds:02d}"
        else:
            time_left = "00:00"
        question_safe = escape_markdown(vote_data["question"], version=1)
        text = (
            f"🗳️ *ГОЛОСОВАНИЕ*\n\n"
            f"*Вопрос:* {question_safe}\n\n"
            f"✅ *За:* {yes_count}\n"
            f"❌ *Против:* {no_count}\n"
            f"👥 *Всего:* {total_votes}\n\n"
            f"⏰ *Осталось:* {time_left}\n"
            f"🆔 `{vote_id}`"
        )
        await query.message.edit_text(
            text,
            reply_markup=get_chat_vote_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
        await query.answer(f"Ваш голос: {vote_text}", show_alert=False)
        logger.info(f"Голос зарегистрирован: {user.username or user.first_name} → {vote_text} в голосовании {vote_id}")
    except Exception as e:
        logger.error(f"Ошибка обработки голоса: {e}", exc_info=True)
        try:
            await query.answer("❌ Ошибка при регистрации голоса", show_alert=True)
        except:
            pass

async def show_duel_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await get_message_from_update(update)
    user = update.effective_user
    from database import load_data
    data = load_data()
    text = (
        "⚔️ СИСТЕМА ДУЭЛЕЙ\n\n"
        "Как вызвать на дуэль:\n"
        "/duel @username - вызвать игрока\n"
        "/duel accept - принять вызов (если вас зовут так же)\n"
        "/duel accept_id [ID] - принять по ID дуэли\n"
        "/duel list - список вызовов\n"
        "/duel cancel - отменить свой вызов\n\n"
        "Правила:\n"
        "• Дуэль длится 5 минут\n"
        "• Побеждает тот, кто нанесет больше урона\n"
        "• Победитель получает бонус к урону (+15-40)\n"
        "• Можно сдаться, но бонус будет меньше\n\n"
    )
    if "duels" in data and "invites" in data["duels"]:
        user_invites = []
        for duel_id, invite in data["duels"]["invites"].items():
            target_name_lower = invite["target_name"].lower().replace("@", "")
            user_username_lower = (user.username or "").lower().replace("@", "")
            user_first_name_lower = user.first_name.lower()
            if (target_name_lower in user_username_lower or 
                target_name_lower in user_first_name_lower):
                user_invites.append(invite)
        if user_invites:
            text += "🎯 ВАШИ ПРИГЛАШЕНИЯ:\n"
            for invite in user_invites[:3]:
                expires = (datetime.fromisoformat(invite["expires_at"]) - datetime.now()).seconds // 60
                text += f"• От {invite['challenger_name']} (ID: `{invite['id']}`)\n"
                text += f"  ⏱️ Истекает через: {expires} мин\n"
                text += f"  📝 Принять: `/duel accept_id {invite['id']}`\n\n"
    await msg.reply_text(text)

async def create_duel_invitation(update: Update, context: ContextTypes.DEFAULT_TYPE, target_username: str):
    msg = await get_message_from_update(update)
    user = update.effective_user
    chat = update.effective_chat
    duel_id = f"{user.id}_{target_username}_{int(datetime.now().timestamp())}"
    created_id = create_duel_invite(
        challenger_id=user.id,
        challenger_name=user.first_name,
        target_id=0,
        target_name=target_username,
        chat_id=chat.id
    )
    kb = get_duel_invite_keyboard(user.id, 0, created_id)
    text = (
        f"⚔️ ВЫЗОВ НА ДУЭЛЬ!\n\n"
        f"👤 {user.first_name} вызывает @{target_username} на дуэль!\n\n"
        f"📋 Правила:\n"
        f"• 5 минут на принятие вызова\n"
        f"• Дуэль длится 5 минут\n"
        f"• Побеждает тот, кто нанесет больше урона\n"
        f"• Победитель получает бонус +15-40 к урону!\n\n"
        f"🆔 ID дуэли: `{created_id}`\n"
        f"🔗 Чтобы принять: `/duel accept_id {created_id}`\n\n"
        f"⏱️ Вызов действителен 5 минут!"
    )
    sent_message = await msg.reply_text(text, reply_markup=kb)
    update_duel_message_id(created_id, sent_message.message_id)

async def accept_specific_duel(update: Update, context: ContextTypes.DEFAULT_TYPE, duel_id: str):
    msg = await get_message_from_update(update)
    user = update.effective_user
    from database import load_data
    data = load_data()
    if "duels" not in data or duel_id not in data["duels"]["invites"]:
        await msg.reply_text("❌ Приглашение не найдено или просрочено")
        return
    invite = data["duels"]["invites"][duel_id]
    invite["target_id"] = user.id
    from keyboard import get_duel_invite_keyboard
    kb = get_duel_invite_keyboard(invite["challenger_id"], user.id, duel_id)
    text = (
        f"⚔️ ПРИГЛАШЕНИЕ НА ДУЭЛЬ\n\n"
        f"От: {invite['challenger_name']}\n"
        f"ID дуэли: `{duel_id}`\n\n"
        f"Принять вызов?"
    )
    await msg.reply_text(text, reply_markup=kb)

async def accept_duel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await get_message_from_update(update)
    user = update.effective_user
    from database import load_data
    data = load_data()
    if "duels" not in data or "invites" not in data["duels"]:
        await msg.reply_text("❌ У вас нет приглашений на дуэль")
        return
    user_invites = []
    for duel_id, invite in data["duels"]["invites"].items():
        target_name_lower = invite["target_name"].lower().replace("@", "")
        user_username_lower = (user.username or "").lower().replace("@", "")
        user_first_name_lower = user.first_name.lower()
        if (target_name_lower in user_username_lower or 
            target_name_lower in user_first_name_lower or
            user_username_lower in target_name_lower or
            user_first_name_lower in target_name_lower):
            invite["target_id"] = user.id
            user_invites.append(invite)
    if not user_invites:
        await msg.reply_text("❌ У вас нет приглашений на дуэль")
        return
    invite = user_invites[0]
    from keyboard import get_duel_invite_keyboard
    kb = get_duel_invite_keyboard(invite["challenger_id"], user.id, invite["id"])
    text = (
        f"⚔️ У вас есть приглашение от {invite['challenger_name']}\n\n"
        f"Принять вызов?"
    )
    await msg.reply_text(text, reply_markup=kb)

@command_handler
@chat_only
async def duel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await get_message_from_update(update)
    if not msg:
        return
    user = update.effective_user
    chat = update.effective_chat
    active_duel = get_user_active_duel(user.id)
    if active_duel:
        opponent = active_duel["target_name"] if user.id == active_duel["challenger_id"] else active_duel["challenger_name"]
        remaining = (datetime.fromisoformat(active_duel["ends_at"]) - datetime.now()).seconds // 60
        await msg.reply_text(
            f"⚔️ Вы уже участвуете в дуэли с {opponent}!\n"
            f"Осталось времени: {remaining} минут\n"
            f"Закончите текущую дуэль перед началом новой."
        )
        return
    if not context.args:
        await show_duel_info(update, context)
        return
    command = context.args[0].lower()
    if command == "accept":
        await accept_duel_command(update, context)
    elif command == "accept_id" and len(context.args) > 1:
        duel_id = context.args[1]
        await accept_specific_duel(update, context, duel_id)
    elif command == "list":
        await list_duels_command(update, context)
    elif command == "cancel":
        await cancel_duel_command(update, context)
    elif command == "stats":
        await duel_stats_command(update, context)
    elif command.startswith("@"):
        await create_duel_invitation(update, context, command[1:])
    else:
        await msg.reply_text(
            "Используйте:\n"
            "/duel @username - вызвать игрока\n"
            "/duel accept - принять вызов (если вас зовут так же)\n"
            "/duel accept_id [ID] - принять по ID\n"
            "/duel list - список вызовов\n"
            "/duel cancel - отменить свой вызов\n"
            "/duel stats - ваша статистика дуэлей"
        )

async def list_duels_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await get_message_from_update(update)
    from database import load_data
    data = load_data()
    text = "⚔️ ДУЭЛИ\n\n"
    text += "Активные дуэли:\n"
    if "duels" in data and data["duels"]["active"]:
        for duel_id, duel in data["duels"]["active"].items():
            remaining = (datetime.fromisoformat(duel["ends_at"]) - datetime.now()).seconds // 60
            text += f"• {duel['challenger_name']} vs {duel['target_name']} ({remaining} мин)\n"
            text += f"  Счёт: {duel['challenger_damage']}-{duel['target_damage']}\n\n"
    else:
        text += "Нет активных дуэлей\n\n"
    text += "Приглашения:\n"
    if "duels" in data and data["duels"]["invites"]:
        for duel_id, invite in data["duels"]["invites"].items():
            expires = (datetime.fromisoformat(invite["expires_at"]) - datetime.now()).seconds // 60
            text += f"• {invite['challenger_name']} → {invite['target_name']} ({expires} мин)\n"
    else:
        text += "Нет приглашений\n"
    await msg.reply_text(text)

async def cancel_duel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await get_message_from_update(update)
    user = update.effective_user
    from database import load_data, save_data
    data = load_data()
    if "duels" not in data or "invites" not in data["duels"]:
        await msg.reply_text("❌ У вас нет активных вызовов")
        return
    user_invites = []
    for duel_id, invite in data["duels"]["invites"].items():
        if invite["challenger_id"] == user.id:
            user_invites.append(duel_id)
    if not user_invites:
        await msg.reply_text("❌ У вас нет активных вызовов")
        return
    for duel_id in user_invites:
        del data["duels"]["invites"][duel_id]
    save_data(data)
    await msg.reply_text(f"✅ Отменено {len(user_invites)} вызовов")

async def duel_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await get_message_from_update(update)
    user = update.effective_user
    from database import load_data
    data = load_data()
    wins = 0
    losses = 0
    draws = 0
    total_damage = 0
    total_reward = 0
    if "duels" in data and "history" in data["duels"]:
        for duel in data["duels"]["history"]:
            if duel["challenger_id"] == user.id or duel["target_id"] == user.id:
                if duel.get("winner_id") == user.id:
                    wins += 1
                    total_reward += duel.get("reward", 0)
                elif duel.get("winner_id") is None:
                    draws += 1
                else:
                    losses += 1
                if duel["challenger_id"] == user.id:
                    total_damage += duel["challenger_damage"]
                else:
                    total_damage += duel["target_damage"]
    text = (
        f"⚔️ ВАША СТАТИСТИКА ДУЭЛЕЙ\n\n"
        f"📊 Результаты:\n"
        f"🏆 Побед: {wins}\n"
        f"💀 Поражений: {losses}\n"
        f"🤝 Ничьих: {draws}\n\n"
        f"🔥 Урон в дуэлях: {format_num(total_damage)}\n"
        f"🎯 Всего бонусного урона: +{total_reward}\n\n"
    )
    if (wins+losses+draws) > 0:
        text += f"📈 Процент побед: {wins/(wins+losses+draws)*100:.1f}%"
    await msg.reply_text(text)

@command_handler
@chat_only
async def roles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await get_message_from_update(update)
    if not msg:
        return
    text = "👑 РОЛИ В ЧАТЕ\n\nКак получить роли:\n• 👑 Король шlёпков — быть топ-1 в чате\n• 🎯 Самый меткий — нанести максимальный урон\n• ⚡ Спринтер — сделать 10+ шlёпков за 5 минут\n• 💪 Силач — нанести урон 40+ единиц\n\nИспользуй /chat_top чтобы увидеть текущих лидеров!"
    await msg.reply_text(text)

@command_handler
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await get_message_from_update(update)
    if not msg:
        return
    text = "🆘 ПОМОЩЬ\n\nОсновные команды:\n/start — Начало работы\n/shlep — Шlёпнуть Мишка\n/stats — Глобальная статистика\n/level — Твой уровень\n/my_stats — Детальная статистика\n/detailed_stats — Расширенная статистика\n/trends — Глобальные тренды\n/mishok — О Мишке\n\nДля чатов:\n/chat_stats — Статистика чата\n/chat_top — Топ игроков чата\n/vote — Голосование\n/duel — Дуэль\n/roles — Роли в чате\n\nНовое: Шлёпай в одном окне без спама сообщений!"
    await msg.reply_text(text)

@command_handler
async def mishok(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        msg = await get_message_from_update(update)
        if not msg:
            return
        await msg.reply_text(
            MISHOK_INTRO,
            disable_web_page_preview=True
        )
        logger.info(f"Команда 'О Мишке' выполнена для пользователя {update.effective_user.id}")
    except Exception as e:
        logger.error(f"Ошибка в mishok: {e}", exc_info=True)
        try:
            if update.message:
                await update.message.reply_text(
                    "ℹ️ Информация о Мишке:\n\nЯ — Мишок Лысый, бот для шlёпок! Используй /help для команд."
                )
            elif update.callback_query:
                await update.callback_query.message.reply_text(
                    "ℹ️ Информация о Мишке:\n\nЯ — Мишок Лысый, бот для шlёпок!"
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
    await msg.reply_text(text)

@command_handler
async def check_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await get_message_from_update(update)
    if not msg:
        return
    try:
        result = check_data_integrity()
        text = "🔍 ПРОВЕРКА ЦЕЛОСТНОСТИ ДАННЫХ\n\n"
        text += f"📊 Статистика:\n"
        text += f"👥 Пользователей: {result['stats']['users']}\n"
        text += f"💬 Чатов: {result['stats']['chats']}\n"
        text += f"👊 Всего шlёпков: {result['stats']['total_shleps']}\n\n"
        if result['errors']:
            text += "❌ КРИТИЧЕСКИЕ ОШИБКИ:\n"
            for error in result['errors']:
                text += f"• {error}\n"
            text += "\n"
        else:
            text += "✅ Критических ошибок нет\n\n"
        if result['warnings']:
            text += "⚠️ ПРЕДУПРЕЖДЕНИЯ:\n"
            for warning in result['warnings'][:5]:
                text += f"• {warning}\n"
            if len(result['warnings']) > 5:
                text += f"... и ещё {len(result['warnings']) - 5} предупреждений\n"
        else:
            text += "✅ Предупреждений нет\n"
        await msg.reply_text(text)
    except Exception as e:
        await msg.reply_text(f"❌ Ошибка проверки: {str(e)}")

@command_handler
async def repair(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await get_message_from_update(update)
    if not msg:
        return
    from config import ADMIN_ID
    if update.effective_user.id != ADMIN_ID:
        await msg.reply_text("⚠️ Эта команда только для администраторов!")
        return
    try:
        await msg.reply_text("🔄 Восстановление структуры данных...")
        success = repair_data_structure()
        if success:
            from database import load_data
            data = load_data()
            text = (
                "✅ СТРУКТУРА ДАННЫХ ВОССТАНОВЛЕНА\n\n"
                f"👥 Пользователей: {len(data.get('users', {}))}\n"
                f"💬 Чатов: {len(data.get('chats', {}))}\n"
                f"👊 Всего шlёпков: {data.get('global_stats', {}).get('total_shleps', 0)}\n\n"
                "Ошибки больше не должны возникать!"
            )
        else:
            text = "❌ Не удалось восстановить структуру данных"
        await msg.reply_text(text)
    except Exception as e:
        await msg.reply_text(f"❌ Ошибка: {str(e)}")

@command_handler
async def data_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import os
    import json
    from datetime import datetime
    msg = await get_message_from_update(update)
    if not msg:
        return
    DATA_FILE = "/data/mishok_data.json"
    text = "📁 ИНФОРМАЦИЯ О ФАЙЛЕ ДАННЫХ\n\n"
    if os.path.exists(DATA_FILE):
        try:
            size = os.path.getsize(DATA_FILE)
            modified = datetime.fromtimestamp(os.path.getmtime(DATA_FILE))
            text += f"📍 Путь: {DATA_FILE}\n"
            text += f"📏 Размер: {size:,} байт\n".replace(",", " ")
            text += f"📅 Изменен: {modified.strftime('%d.%m.%Y %H:%M:%S')}\n"
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            text += f"\n📊 СОДЕРЖИМОЕ:\n"
            text += f"• Пользователей: {len(data.get('users', {}))}\n"
            text += f"• Чатов: {len(data.get('chats', {}))}\n"
            text += f"• Всего шlёпков: {data.get('global_stats', {}).get('total_shleps', 0)}\n"
            text += f"• Макс. урон: {data.get('global_stats', {}).get('max_damage', 0)}\n"
            text += f"• Записей в истории: {len(data.get('records', []))}\n"
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
        text += "Используйте /repair для восстановления структуры данных"
    await msg.reply_text(text)

async def start_shlep_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    await query.answer()
    user = update.effective_user
    safe_name = escape_markdown(user.first_name, version=1)
    text = f"👤 {safe_name}, начинаем сессию шлёпания!\n\nНажимай '👊 Ещё раз!' для следующего шlёпка\nТекущие результаты будут обновляться здесь"
    await perform_shlep(update, context, edit_message=query.message)

async def handle_shlep_session(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str):
    query = update.callback_query
    if not query:
        return
    await query.answer()
    if action == "shlep_again":
        await perform_shlep(update, context, edit_message=query.message)
    elif action == "shlep_level":
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
        text = f"🎯 ТВОЙ УРОВЕНЬ\n👤 Игрок: {safe_name}\n📊 Шlёпков: {format_num(cnt)}\n🎯 Уровень: {lvl['level']} ({title})\n{bar} {lvl['progress']}%\n⚡ Диапазон урона: {lvl['min']}-{lvl['max']}\n🎯 До след. уровня: {lvl['next']} шlёпков\n💡 {advice}"
        await query.message.edit_text(text, reply_markup=get_shlep_session_keyboard())
    elif action == "shlep_stats":
        cached = await cache.get("global_stats")
        if cached:
            total, last, maxd, maxu, maxdt = cached
        else:
            total, last, maxd, maxu, maxdt = get_stats()
            await cache.set("global_stats", (total, last, maxd, maxu, maxdt))
        maxu_safe = escape_markdown(maxu or 'Нет', version=1)
        text = f"📊 ГЛОБАЛЬНАЯ СТАТИСТИКА\n👑 РЕКОРД УРОНА: {maxd} единиц\n👤 Рекордсмен: {maxu_safe}\n📅 Дата рекорда: {maxdt.strftime('%d.%m.%Y %H:%M') if maxdt else '—'}\n🔢 Всего шlёпков: {format_num(total)}\n⏰ Последний шlёпок: {last.strftime('%d.%m.%Y %H:%M') if last else 'нет'}"
        await query.message.edit_text(text, reply_markup=get_shlep_session_keyboard())
    elif action == "shlep_my_stats":
        user = update.effective_user
        _, cnt, last = get_user_stats(user.id)
        lvl = calc_level(cnt)
        compare_stats = get_comparison_stats(user.id)
        text = f"📈 ТВОЯ ДЕТАЛЬНАЯ СТАТИСТИКА\n👤 Игрок: {user.first_name}\n📊 Всего шlёпков: {format_num(cnt)}\n🎯 Уровень: {lvl['level']}\n⚡ Диапазон урона: {lvl['min']}-{lvl['max']}\n{get_favorite_time(user.id)}\n📊 Сравнение с другими:\n👥 Всего игроков: {compare_stats.get('total_users', 0)}\n📈 Среднее на игрока: {compare_stats.get('avg_shleps', 0)}\n🏆 Твой ранг: {compare_stats.get('rank', 1)}\n📊 Лучше чем: {compare_stats.get('percentile', 0)}% игроков"
        await query.message.edit_text(text, reply_markup=get_shlep_session_keyboard())
    elif action == "shlep_trends":
        trends_data = get_global_trends_info()
        if not trends_data:
            text = "📊 Данные временно недоступны"
        else:
            text = f"📊 ГЛОБАЛЬНЫЕ ТРЕНДЫ\n👥 Активных за 24 часа: {trends_data.get('active_users_24h', 0)}\n👊 Шlёпков за 24 часа: {trends_data.get('shleps_24h', 0)}\n📈 Среднее на игрока: {trends_data.get('avg_per_user_24h', 0)}\n🔥 Активных сегодня: {trends_data.get('active_today', 0)}\n⏰ Текущий час: {trends_data.get('current_hour', 0):02d}:00\n👊 Шlёпков в этом часу: {trends_data.get('shleps_this_hour', 0)}"
        await query.message.edit_text(text, reply_markup=get_shlep_session_keyboard())
    elif action == "shlep_menu":
        safe_name = escape_markdown(update.effective_user.first_name, version=1)
        text = f"👋 Привет, {safe_name}!\nЯ — Мишок Лысый 👴✨\n\nНачни шlёпать прямо сейчас!"
        await query.message.edit_text(text, reply_markup=get_shlep_start_keyboard())

async def handle_duel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    query = update.callback_query
    user = update.effective_user
    parts = data.split("_")
    action = parts[1] if len(parts) > 1 else None
    duel_id = parts[2] if len(parts) > 2 else None
    if not duel_id:
        await query.answer("❌ Ошибка: ID дуэли не найден", show_alert=True)
        return
    if action == "accept":
        from database import accept_duel_invite, update_duel_message_id
        duel = accept_duel_invite(duel_id)
        if duel:
            from database import load_data, save_data
            data = load_data()
            if duel_id in data["duels"]["active"]:
                data["duels"]["active"][duel_id]["target_id"] = user.id
                data["duels"]["active"][duel_id]["target_name"] = user.first_name
                save_data(data)
                duel = data["duels"]["active"][duel_id]
            await update_duel_message(context, duel_id, query.message.chat_id, query.message.message_id)
            await query.answer(f"✅ Вы приняли вызов от {duel['challenger_name']}!", show_alert=True)
        else:
            await query.answer("❌ Приглашение не найдено или просрочено", show_alert=True)
    elif action == "decline":
        from database import decline_duel_invite
        success = decline_duel_invite(duel_id)
        if success:
            await query.message.edit_text(
                f"❌ ВЫЗОВ ОТКЛОНЁН\n\n"
                f"Пользователь {user.first_name} отклонил вызов на дуэль."
            )
            await query.answer("Вызов отклонён", show_alert=False)
        else:
            await query.answer("❌ Приглашение не найдено", show_alert=True)
    elif action == "shlep":
        if len(parts) >= 3:
            duel_id = parts[2]
            from database import get_active_duel, add_shlep_to_duel
            duel = get_active_duel(duel_id)
            if not duel:
                await query.answer("❌ Дуэль не найдена или завершена", show_alert=True)
                return
            if user.id not in [duel["challenger_id"], duel["target_id"]]:
                await query.answer("❌ Вы не участник этой дуэли", show_alert=True)
                return
            from bot import calc_level
            _, user_shleps, _ = get_user_stats(user.id)
            lvl = calc_level(user_shleps)
            damage = random.randint(lvl['min'], lvl['max'])
            from database import load_data
            data = load_data()
            user_data = data["users"].get(str(user.id), {})
            bonus = user_data.get("bonus_damage", 0)
            total_damage = damage + bonus
            result = add_shlep_to_duel(duel_id, user.id, total_damage)
            if result:
                await update_duel_message(context, duel_id, query.message.chat_id, query.message.message_id)
                side = "challenger" if user.id == duel["challenger_id"] else "target"
                opponent = duel["target_name"] if side == "challenger" else duel["challenger_name"]
                await query.answer(
                    f"👊 Вы нанесли {total_damage} урона {opponent}!\n"
                    f"({damage} + {bonus} бонус)",
                    show_alert=False
                )
                if isinstance(result, dict) and result.get("is_finished") is False:
                    pass
                else:
                    await query.answer("🏆 Дуэль завершена! Смотрите результаты выше.", show_alert=True)
            else:
                await query.answer("❌ Ошибка при добавлении шлёпка", show_alert=True)
    elif action == "stats":
        from database import get_active_duel
        duel = get_active_duel(duel_id)
        if duel:
            total_shleps = duel["challenger_shleps"] + duel["target_shleps"]
            avg_challenger = duel["challenger_damage"] // max(duel["challenger_shleps"], 1)
            avg_target = duel["target_damage"] // max(duel["target_shleps"], 1)
            await query.answer(
                f"📊 Статистика дуэли:\n\n"
                f"{duel['challenger_name']}:\n"
                f"• Урон: {duel['challenger_damage']}\n"
                f"• Шлёпков: {duel['challenger_shleps']}\n"
                f"• Средний урон: {avg_challenger}\n\n"
                f"{duel['target_name']}:\n"
                f"• Урон: {duel['target_damage']}\n"
                f"• Шlёпков: {duel['target_shleps']}\n"
                f"• Средний урон: {avg_target}\n\n"
                f"Всего шлёпков: {total_shleps}",
                show_alert=True
            )
        else:
            await query.answer("❌ Дуэль не найдена", show_alert=True)
    elif action == "surrender":
        from database import get_active_duel, surrender_duel
        duel = get_active_duel(duel_id)
        if not duel:
            await query.answer("❌ Дуэль не найдена", show_alert=True)
            return
        if user.id not in [duel["challenger_id"], duel["target_id"]]:
            await query.answer("❌ Вы не участник этой дуэли", show_alert=True)
            return
        result = surrender_duel(duel_id, user.id)
        if result:
            await update_duel_message(context, duel_id, query.message.chat_id, query.message.message_id)
            await query.answer(f"🏳️ Вы сдались! {result['winner_name']} побеждает.", show_alert=True)
        else:
            await query.answer("❌ Ошибка при сдаче", show_alert=True)
    elif action == "refresh":
        await update_duel_message(context, duel_id, query.message.chat_id, query.message.message_id)
        await query.answer("🔄 Сообщение обновлено", show_alert=False)
    elif action == "details":
        from database import load_data
        data = load_data()
        duel = None
        for hist_duel in data.get("duels", {}).get("history", []):
            if hist_duel.get("id") == duel_id:
                duel = hist_duel
                break
        if duel:
            history_text = "Последние 10 действий:\n"
            for action in duel.get("history", [])[-10:]:
                time_str = datetime.fromisoformat(action["timestamp"]).strftime("%H:%M:%S")
                history_text += f"{time_str} - {action['user_name']}: {action['damage']} урона\n"
            await query.answer(history_text, show_alert=True)
        else:
            await query.answer("❌ История дуэли не найдена", show_alert=True)
    elif action == "close":
        await query.message.delete()
        await query.answer("✅ Сообщение закрыто", show_alert=False)
    else:
        await query.answer("⚙️ Функция в разработке", show_alert=False)

async def inline_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    await query.answer()
    data = query.data
    logger.info(f"Callback received: {data}")
    if data == "start_shlep_session":
        await start_shlep_session(update, context)
    elif data in ["shlep_again", "shlep_level", "shlep_stats", "shlep_my_stats", "shlep_trends", "shlep_menu"]:
        await handle_shlep_session(update, context, data)
    elif data == "shlep_mishok":
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
    elif data in ["vote_yes", "vote_no"]:
        await handle_vote(update, context, data)
    elif data.startswith("duel_"):
        await handle_duel_callback(update, context, data)
    else:
        await query.message.reply_text("⚙️ Эта функция в разработке")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    if not update.message:
        return
    text = update.message.text
    logger.info(f"Button pressed: {text}")
    try:
        if text == "👊 Шлёпнуть Мишка":
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
                "Неизвестная команда. Используйте /help для списка команд."
            )
    except Exception as e:
        logger.error(f"Ошибка в button_handler: {e}", exc_info=True)
        await update.message.reply_text(
            "⚠️ Произошла ошибка при обработке команды. Попробуйте ещё раз."
        )

async def group_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.new_chat_members:
        for m in update.message.new_chat_members:
            if m.id == context.bot.id:
                await update.message.reply_text(
                    "👴 Мишок Лысый в чате!\n\n"
                    "Теперь можно шlёпать меня по лысине прямо здесь!\n"
                    "Основные команды:\n"
                    "/shlep — шlёпнуть Мишка\n"
                    "/stats — статистика\n"
                    "/level — уровень\n"
                    "/my_stats — детальная статистика\n"
                    "Для чата:\n"
                    "/chat_stats — статистика чата\n"
                    "/chat_top — топ игроков\n"
                    "/vote — голосование\n"
                    "/duel — дуэль\n"
                    "Прогресс сохраняется! 💾"
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
        ("vote_info", vote_info),
        ("duel", duel),
        ("roles", roles),
        ("backup", backup),
        ("storage", storage),
        ("check_data", check_data),
        ("repair", repair),
        ("data_info", data_info),
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
