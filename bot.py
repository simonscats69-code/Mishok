import logging
import random
import sys
import os
import json
import asyncio
import re
from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, Any, Tuple

from telegram import Update, User
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.constants import ParseMode
from telegram.helpers import escape_markdown

from config import BOT_TOKEN, MISHOK_REACTIONS, MISHOK_INTRO, DATA_FILE, VOTES_FILE, BACKUP_PATH, LOG_FILE, CHAT_VOTE_DURATION
from database import add_shlep, get_stats, get_top_users, get_user_stats, get_chat_stats, get_chat_top_users, backup_database, check_data_integrity, repair_data_structure, save_vote_data, get_vote_data, delete_vote_data, get_user_vote, get_all_votes, cleanup_expired_votes, create_safe_backup, get_backup_list, get_database_size
from keyboard import get_shlep_session_keyboard, get_shlep_start_keyboard, get_chat_vote_keyboard, get_main_reply_keyboard, get_main_inline_keyboard, get_admin_keyboard, get_confirmation_keyboard, get_cleanup_keyboard
from cache import cache
from statistics import get_favorite_time, get_comparison_stats
from utils import format_file_size

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

def admin_only(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        from config import ADMIN_ID
        if update.effective_user.id != ADMIN_ID:
            msg = get_message_from_update(update)
            if msg:
                await msg.reply_text("⚠️ Эта команда только для администраторов!")
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

def get_message_from_update(update: Update):
    if update.callback_query and update.callback_query.message:
        return update.callback_query.message
    return update.message

async def send_progress(message, text, progress=0):
    bar_length = 10
    filled = int(progress * bar_length)
    bar = "█" * filled + "░" * (bar_length - filled)
    percentage = int(progress * 100)
    
    status_text = f"🔄 {text}\n[{bar}] {percentage}%"
    
    try:
        await message.edit_text(status_text)
    except:
        await message.reply_text(status_text)
    
    return percentage

async def perform_shlep(update: Update, context: ContextTypes.DEFAULT_TYPE, edit_message=None):
    try:
        msg = get_message_from_update(update)
        if not msg:
            logger.error("Не удалось получить сообщение из update")
            return
        
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
        
        try:
            total, cnt, max_dmg = add_shlep(
                user.id, 
                username, 
                total_damage, 
                chat.id if chat.type != "private" else None
            )
        except KeyError as e:
            logger.error(f"Ошибка KeyError при добавлении шлёпка: {e}")
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
        
        text = f"{get_reaction()}{rec}\n💥 Урон: {total_damage}\n👤 {user.first_name}: {cnt} шлёпков\n🎯 Уровень {lvl['level']} ({title})"
        
        kb = get_shlep_session_keyboard()
        
        if edit_message:
            try:
                await edit_message.edit_text(text, reply_markup=kb)
                return edit_message
            except Exception as e:
                logger.warning(f"Не удалось отредактировать сообщение: {e}")
                return await msg.reply_text(text, reply_markup=kb)
        else:
            return await msg.reply_text(text, reply_markup=kb)
        
    except Exception as e:
        logger.error(f"Ошибка в perform_shlep: {e}", exc_info=True)
        try:
            msg = get_message_from_update(update)
            if msg:
                await msg.reply_text("⚠️ Произошла ошибка при обработке шлёпка. Попробуйте еще раз.")
        except Exception as e2:
            logger.error(f"Не удалось отправить сообщение об ошибке: {e2}")

@command_handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = get_message_from_update(update)
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
❓ /help — Помощь по командам
👴 /mishok — О Мишке

Новая фича: Теперь шлёпай в одном окне без спама сообщений!"""
        
        kb = get_main_reply_keyboard()
        await msg.reply_text(text, reply_markup=kb)
    else:
        text += """Я бот для шлёпков!

Команды для чата:
👊 /shlep — Шлёпнуть Мишка
📊 /chat_stats — Статистика чата
🏆 /chat_top — Топ игроков
🗳️ /vote [вопрос] — Голосование

Личные команды (в лс с ботом):
📊 /stats — Глобальная статистика
🎯 /level — Твой уровень
📈 /my_stats — Детальная статистика

Нажми кнопку ниже или введи команду!"""
        
        kb = get_main_inline_keyboard()
        await msg.reply_text(text, reply_markup=kb)

@command_handler
async def shlep(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await perform_shlep(update, context)

@command_handler 
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = get_message_from_update(update)
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
    
    text = f"📊 ГЛОБАЛЬНАЯ СТАТИСТИКА\n👑 РЕКОРД УРОНА: {maxd} единиц\n👤 Рекордсмен: {maxu_safe}\n📅 Дата рекорда: {maxdt.strftime('%d.%m.%Y %H:%M') if maxdt else '—'}\n🔢 Всего шлёпков: {format_num(total)}\n⏰ Последний шлёпок: {last.strftime('%d.%m.%Y %H:%M') if last else 'нет'}"
    
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
    msg = get_message_from_update(update)
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
    
    text = f"🎯 ТВОЙ УРОВЕНЬ\n👤 Игрок: {safe_name}\n📊 Шлёпков: {format_num(cnt)}\n🎯 Уровень: {lvl['level']} ({title})\n{bar} {lvl['progress']}%\n⚡ Диапазон урона: {lvl['min']}-{lvl['max']}\n🎯 До след. уровня: {lvl['next']} шлёпков\n💡 {advice}"
    
    if last:
        text += f"\n⏰ Последний шлёпок: {last.strftime('%d.%m.%Y %H:%M')}"
    
    await msg.reply_text(text)

@command_handler
async def my_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = get_message_from_update(update)
    if not msg:
        return
    
    user = update.effective_user
    
    _, cnt, last = get_user_stats(user.id)
    lvl = calc_level(cnt)
    compare_stats = get_comparison_stats(user.id)
    
    text = f"📈 ТВОЯ ДЕТАЛЬНАЯ СТАТИСТИКА\n👤 Игрок: {user.first_name}\n📊 Всего шлёпков: {format_num(cnt)}\n🎯 Уровень: {lvl['level']}\n⚡ Диапазон урона: {lvl['min']}-{lvl['max']}\n{get_favorite_time(user.id)}\n📊 Сравнение с другими:\n👥 Всего игроков: {compare_stats.get('total_users', 0)}\n📈 Среднее на игрока: {compare_stats.get('avg_shleps', 0)}\n🏆 Твой ранг: {compare_stats.get('rank', 1)}\n📊 Лучше чем: {compare_stats.get('percentile', 0)}% игроков"
    
    if last:
        text += f"\n⏰ Последний шлёпок: {last.strftime('%d.%m.%Y %H:%M')}"
    
    await msg.reply_text(text)

@command_handler
@chat_only
async def chat_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = get_message_from_update(update)
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
        text = f"📊 СТАТИСТИКА ЧАТА\n👥 Участников: {cs.get('total_users', 0)}\n👊 Всего шлёпков: {format_num(cs.get('total_shleps', 0))}\n🏆 Рекорд урона: {cs.get('max_damage', 0)} единиц\n👑 Рекордсмен: {max_user_safe}"
    
    await msg.reply_text(text)

@command_handler
@chat_only
async def chat_top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = get_message_from_update(update)
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
    
    await msg.reply_text(text)

async def vote_timer(vote_id, chat_id, message_id, context):
    try:
        await asyncio.sleep(CHAT_VOTE_DURATION)
        
        vote_data = get_vote_data(vote_id)
        if not vote_data or vote_data.get("finished", False):
            return
            
        await finish_vote(vote_id, chat_id, message_id, context)
        
    except asyncio.CancelledError:
        logger.info(f"Таймер голосования {vote_id} отменён")
    except Exception as e:
        logger.error(f"Ошибка в таймере голосования {vote_id}: {e}")

async def finish_vote(vote_id, chat_id, message_id, context):
    try:
        vote_data = get_vote_data(vote_id)
        if not vote_data or vote_data.get("finished", False):
            return
            
        vote_data["finished"] = True
        vote_data["finished_at"] = datetime.now().isoformat()
        
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
            if "Message to edit not found" in str(e) or "message not found" in str(e):
                logger.warning(f"Сообщение голосования {vote_id} было удалено")
            else:
                logger.error(f"Ошибка обновления сообщения голосования: {e}")
        
        save_vote_data(vote_data)
                
    except Exception as e:
        logger.error(f"Ошибка завершения голосования {vote_id}: {e}")

@command_handler
@chat_only
async def vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = get_message_from_update(update)
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
        "ends_at": (datetime.now() + timedelta(seconds=CHAT_VOTE_DURATION)).isoformat(),
        "finished": False
    }
    
    save_vote_data(vote_data)
    
    asyncio.create_task(vote_timer(vote_id, msg.chat_id, msg.message_id, context))
    
    text = (
        f"🗳️ *ГОЛОСОВАНИЕ*\n\n"
        f"*Вопрос:* {question_safe}\n\n"
        f"✅ *За:* 0\n"
        f"❌ *Против:* 0\n\n"
        f"⏰ *Голосование длится {CHAT_VOTE_DURATION//60} минут!*"
    )
    
    sent_message = await msg.reply_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
    
    vote_data["message_id"] = sent_message.message_id
    save_vote_data(vote_data)
    
    logger.info(f"Голосование создано: {question} в чате {msg.chat_id}, ID: {vote_id}")

@command_handler
@chat_only
async def vote_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = get_message_from_update(update)
    if not msg:
        return
        
    chat_id = msg.chat_id
    
    try:
        cleanup_expired_votes()
        
        all_votes = get_all_votes()
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
                text += f"   ⏰ Осталось: {minutes:02d}:{seconds:02d}\n\n"
        
        await msg.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Ошибка получения информации о голосованиях: {e}")
        await msg.reply_text("❌ Ошибка при получении информации о голосованиях")

async def handle_vote(update: Update, context: ContextTypes.DEFAULT_TYPE, vote_type: str):
    try:
        query = update.callback_query
        if not query:
            return
            
        await query.answer()
        user = update.effective_user
        user_id = str(user.id)
        
        vote_id = None
        all_votes = get_all_votes()
        
        for vid, vdata in all_votes.items():
            if (str(vdata.get("message_id")) == str(query.message.message_id) and 
                str(vdata.get("chat_id")) == str(query.message.chat.id)):
                vote_id = vid
                break
        
        if not vote_id:
            await query.answer("❌ Голосование не найдено или устарело", show_alert=True)
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
            f"⏰ *Осталось:* {time_left}"
        )
        
        await query.message.edit_text(
            text,
            reply_markup=get_chat_vote_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
        
        logger.info(f"Голос зарегистрирован: {user.username or user.first_name} → {vote_text} в голосовании {vote_id}")
        
    except Exception as e:
        logger.error(f"Ошибка обработки голоса: {e}", exc_info=True)
        try:
            await query.answer("❌ Ошибка при регистрации голоса", show_alert=True)
        except:
            pass

@command_handler
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = get_message_from_update(update)
    if not msg:
        return
    
    text = """🆘 ПОМОЩЬ

Основные команды:
/start — Начало работы
/shlep — Шлёпнуть Мишка
/stats — Глобальная статистика
/level — Твой уровень
/my_stats — Детальная статистика
/mishok — О Мишке

Для чатов:
/chat_stats — Статистика чата
/chat_top — Топ игроков чата
/vote — Голосование

Новое: Шлёпай в одном окне без спама сообщений!"""
    
    await msg.reply_text(text)

@command_handler
async def mishok(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        msg = get_message_from_update(update)
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
                    "ℹ️ Информация о Мишке:\n\nЯ — Мишок Лысый, бот для шлёпок! Используй /help для команд."
                )
            elif update.callback_query:
                await update.callback_query.message.reply_text(
                    "ℹ️ Информация о Мишке:\n\nЯ — Мишок Лысый, бот для шлёпок!"
                )
        except Exception as e2:
            logger.error(f"Не удалось отправить сообщение об ошибке: {e2}")

@command_handler
@admin_only
async def backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = get_message_from_update(update)
    if not msg:
        return
    
    status_msg = await msg.reply_text("💾 Создание бэкапа...")
    
    await send_progress(status_msg, "Создание безопасного бэкапа", 0.3)
    success, backup_path = create_safe_backup("manual")
    
    if success:
        await send_progress(status_msg, "Бэкап создан", 0.7)
        
        size = os.path.getsize(backup_path)
        backups = get_backup_list(5)
        
        text = "✅ БЭКАП СОЗДАН!\n\n"
        text += f"📁 Файл: {os.path.basename(backup_path)}\n"
        text += f"📏 Размер: {format_file_size(size)}\n\n"
        text += "📦 ПОСЛЕДНИЕ БЭКАПЫ:\n"
        
        for i, backup in enumerate(backups, 1):
            age = backup['age_days']
            text += f"{i}. {backup['name']} ({format_file_size(backup['size'])}), {age} дн. назад\n"
        
        await status_msg.edit_text(text)
    else:
        await status_msg.edit_text(f"❌ Ошибка создания бэкапа: {backup_path}")

@command_handler
async def storage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = get_message_from_update(update)
    if not msg:
        return
    
    import os
    text = "📂 Информация о хранилище:\n"
    paths = [
        ("/root", "Основная папка"),
        ("/bothost", "Корень Bothost"),
        (DATA_FILE, "Файл данных"),
        (VOTES_FILE, "Файл голосований"),
        (BACKUP_PATH, "Директория бэкапов"),
        (LOG_FILE, "Файл логов")
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
    msg = get_message_from_update(update)
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
@admin_only
async def repair(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = get_message_from_update(update)
    if not msg:
        return
    
    status_msg = await msg.reply_text("🔄 Восстановление структуры данных...")
    
    await send_progress(status_msg, "Создание бэкапа перед восстановлением", 0.2)
    create_safe_backup("before_repair")
    
    await send_progress(status_msg, "Восстановление структуры", 0.5)
    success = repair_data_structure()
    
    if success:
        await send_progress(status_msg, "Загрузка данных для проверки", 0.8)
        from database import load_data
        data = load_data()
        
        text = (
            "✅ СТРУКТУРА ДАННЫХ ВОССТАНОВЛЕНА\n\n"
            f"👥 Пользователей: {len(data.get('users', {}))}\n"
            f"💬 Чатов: {len(data.get('chats', {}))}\n"
            f"👊 Всего шлёпков: {data.get('global_stats', {}).get('total_shleps', 0)}\n\n"
            "Ошибки больше не должны возникать!"
        )
    else:
        text = "❌ Не удалось восстановить структуру данных"
    
    await status_msg.edit_text(text)

@command_handler
async def data_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import os
    import json
    from datetime import datetime
    
    msg = get_message_from_update(update)
    if not msg:
        return
    
    from config import DATA_FILE
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
            text += f"• Всего шлёпков: {data.get('global_stats', {}).get('total_shleps', 0)}\n"
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
    text = f"👤 {safe_name}, начинаем сессию шлёпания!\n\nНажимай '👊 Ещё раз!' для следующего шлёпка\nТекущие результаты будут обновляться здесь"
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
        
        text = f"🎯 ТВОЙ УРОВЕНЬ\n👤 Игрок: {safe_name}\n📊 Шлёпков: {format_num(cnt)}\n🎯 Уровень: {lvl['level']} ({title})\n{bar} {lvl['progress']}%\n⚡ Диапазон урона: {lvl['min']}-{lvl['max']}\n🎯 До след. уровня: {lvl['next']} шлёпков\n💡 {advice}"
        
        await query.message.edit_text(text, reply_markup=get_shlep_session_keyboard())
    elif action == "shlep_stats":
        cached = await cache.get("global_stats")
        if cached:
            total, last, maxd, maxu, maxdt = cached
        else:
            total, last, maxd, maxu, maxdt = get_stats()
            await cache.set("global_stats", (total, last, maxd, maxu, maxdt))
        
        maxu_safe = escape_markdown(maxu or 'Нет', version=1)
        text = f"📊 ГЛОБАЛЬНАЯ СТАТИСТИКА\n👑 РЕКОРД УРОНА: {maxd} единиц\n👤 Рекордсмен: {maxu_safe}\n📅 Дата рекорда: {maxdt.strftime('%d.%m.%Y %H:%M') if maxdt else '—'}\n🔢 Всего шлёпков: {format_num(total)}\n⏰ Последний шлёпок: {last.strftime('%d.%m.%Y %H:%M') if last else 'нет'}"
        
        await query.message.edit_text(text, reply_markup=get_shlep_session_keyboard())
    elif action == "shlep_my_stats":
        user = update.effective_user
        _, cnt, last = get_user_stats(user.id)
        lvl = calc_level(cnt)
        compare_stats = get_comparison_stats(user.id)
        
        text = f"📈 ТВОЯ ДЕТАЛЬНАЯ СТАТИСТИКА\n👤 Игрок: {user.first_name}\n📊 Всего шлёпков: {format_num(cnt)}\n🎯 Уровень: {lvl['level']}\n⚡ Диапазон урона: {lvl['min']}-{lvl['max']}\n{get_favorite_time(user.id)}\n📊 Сравнение с другими:\n👥 Всего игроков: {compare_stats.get('total_users', 0)}\n📈 Среднее на игрока: {compare_stats.get('avg_shleps', 0)}\n🏆 Твой ранг: {compare_stats.get('rank', 1)}\n📊 Лучше чем: {compare_stats.get('percentile', 0)}% игроков"
        
        await query.message.edit_text(text, reply_markup=get_shlep_session_keyboard())
    elif action == "shlep_menu":
        safe_name = escape_markdown(update.effective_user.first_name, version=1)
        text = f"👋 Привет, {safe_name}!\nЯ — Мишок Лысый 👴✨\n\nНачни шлёпать прямо сейчас!"
        await query.message.edit_text(text, reply_markup=get_shlep_start_keyboard())

@command_handler
@admin_only
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = get_message_from_update(update)
    if not msg:
        return
    
    await msg.reply_text(
        "⚙️ АДМИН-ПАНЕЛЬ\n\n"
        "Выберите действие:",
        reply_markup=get_admin_keyboard()
    )

@command_handler
@admin_only
async def admin_health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    
    await query.answer()
    await query.message.edit_text("🩺 Проверяю здоровье системы...")
    
    try:
        import os
        import platform
        
        status_msg = query.message
        
        # Проверка базы данных
        from database import get_database_size, check_data_integrity
        
        db_stats = get_database_size()
        integrity = check_data_integrity()
        
        # Простая проверка диска
        try:
            import shutil
            total, used, free = shutil.disk_usage(".")
            disk_info = f"Диск: {used/(1024**3):.1f} GB из {total/(1024**3):.1f} GB использовано ({used/total*100:.1f}%)"
        except:
            disk_info = "Информация о диске: доступно"
        
        report = "🏥 ОТЧЕТ О ЗДОРОВЬЕ СИСТЕМЫ\n\n"
        
        report += f"🐍 Python: {platform.python_version()}\n"
        report += f"🖥️ Система: {platform.system()} {platform.machine()}\n"
        report += f"💾 {disk_info}\n"
        
        if db_stats.get("exists"):
            report += f"🗃️ База данных: {db_stats.get('size', 0)/1024:.1f} KB\n"
            report += f"👥 Пользователей: {db_stats.get('users', 0)}\n"
            report += f"👊 Шлёпков: {db_stats.get('total_shleps', 0)}\n"
        else:
            report += "🗃️ База данных: ❌ Не найдена\n"
        
        report += f"🔍 Целостность: {len(integrity['errors'])} ошибок, {len(integrity['warnings'])} предупреждений\n"
        
        all_good = (not integrity['errors'] and db_stats.get("exists", False))
        
        if all_good:
            report += "\n🎉 ВСЕ СИСТЕМЫ РАБОТАЮТ НОРМАЛЬНО"
        else:
            report += "\n⚠️ ТРЕБУЕТСЯ ВНИМАНИЕ АДМИНИСТРАТОРА"
        
        await status_msg.edit_text(report, reply_markup=get_admin_keyboard())
        
    except Exception as e:
        await query.message.edit_text(
            f"❌ Ошибка проверки здоровья: {str(e)[:200]}",
            reply_markup=get_admin_keyboard()
        )

@command_handler
@admin_only
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    
    await query.answer()
    status_msg = query.message
    
    await status_msg.edit_text("📊 Собираю статистику пользователей...")
    
    from database import load_data
    
    data = load_data()
    users = data.get('users', {})
    
    if not users:
        await status_msg.edit_text("📭 Нет данных о пользователях", reply_markup=get_admin_keyboard())
        return
    
    import datetime
    now = datetime.datetime.now()
    
    active_today = 0
    active_week = 0
    total_shleps = 0
    max_shleps = 0
    max_user = None
    
    for user_id, user_data in users.items():
        shleps = user_data.get('total_shleps', 0)
        total_shleps += shleps
        
        if shleps > max_shleps:
            max_shleps = shleps
            max_user = user_data.get('username', f'ID: {user_id}')[:20]
        
        last_shlep = user_data.get('last_shlep')
        if last_shlep:
            try:
                last_date = datetime.datetime.fromisoformat(last_shlep)
                days_diff = (now - last_date).days
                
                if days_diff == 0:
                    active_today += 1
                if days_diff <= 7:
                    active_week += 1
            except:
                pass
    
    avg_shleps = total_shleps / len(users) if users else 0
    
    report = f"👥 СТАТИСТИКА ПОЛЬЗОВАТЕЛЕЙ\n\n"
    report += f"📈 Всего пользователей: {len(users)}\n"
    report += f"🎯 Активных сегодня: {active_today}\n"
    report += f"📅 Активных за неделю: {active_week}\n"
    report += f"👊 Всего шлёпков: {total_shleps}\n"
    report += f"📊 Среднее на пользователя: {avg_shleps:.1f}\n"
    report += f"🏆 Рекордсмен: {max_user} ({max_shleps} шлёпков)\n\n"
    
    level_distribution = {}
    for user_data in users.values():
        shleps = user_data.get('total_shleps', 0)
        level = (shleps // 10) + 1
        level_key = f"{min(level, 100)}+" if level > 100 else str(level)
        level_distribution[level_key] = level_distribution.get(level_key, 0) + 1
    
    report += "🎯 РАСПРЕДЕЛЕНИЕ ПО УРОВНЯМ:\n"
    for level, count in sorted(level_distribution.items(), key=lambda x: int(x[0].replace('+', ''))):
        percentage = (count / len(users)) * 100
        bar_length = 10
        filled = int(percentage / 10)
        bar = "█" * filled + "░" * (bar_length - filled)
        report += f"Уровень {level}: {bar} {percentage:.1f}% ({count} чел.)\n"
    
    await status_msg.edit_text(report, reply_markup=get_admin_keyboard())

@command_handler
@admin_only
async def admin_cleanup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    
    await query.answer()
    
    await query.message.edit_text(
        "🧹 ОЧИСТКА СИСТЕМЫ\n\n"
        "Выберите тип очистки:",
        reply_markup=get_cleanup_keyboard()
    )

async def perform_cleanup(message, cleanup_type):
    await message.edit_text(f"🧹 Очистка {cleanup_type}...")
    
    import glob
    import os
    from datetime import datetime, timedelta
    
    total_cleaned = 0
    total_freed = 0
    
    if cleanup_type == "logs":
        # Удаляем старые log файлы
        log_files = glob.glob("*.log")
        for log_file in log_files:
            try:
                size = os.path.getsize(log_file)
                os.remove(log_file)
                total_cleaned += 1
                total_freed += size
            except:
                pass
    
    elif cleanup_type == "temp":
        # Удаляем временные файлы
        temp_files = glob.glob("*.tmp") + glob.glob("*_backup_*.json")
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    size = os.path.getsize(temp_file)
                    os.remove(temp_file)
                    total_cleaned += 1
                    total_freed += size
            except:
                pass
    
    elif cleanup_type == "backups":
        # Удаляем старые бэкапы (оставляем последние 10)
        from database import get_backup_list
        backups = get_backup_list()
        
        if len(backups) > 10:
            backups_to_delete = backups[10:]
            for backup in backups_to_delete:
                try:
                    if os.path.exists(backup["path"]):
                        size = os.path.getsize(backup["path"])
                        os.remove(backup["path"])
                        total_cleaned += 1
                        total_freed += size
                except:
                    pass
    
    freed_mb = total_freed / (1024 * 1024)
    
    result_text = (
        f"✅ ОЧИСТКА ЗАВЕРШЕНА\n\n"
        f"🗑️ Удалено файлов: {total_cleaned}\n"
        f"💾 Освобождено: {freed_mb:.2f} MB\n\n"
        f"Система готова к работе!"
    )
    
    await message.edit_text(result_text, reply_markup=get_admin_keyboard())

@command_handler
@admin_only
async def cleanup_action(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str):
    query = update.callback_query
    if not query:
        return
    
    await query.answer()
    
    if action == "logs":
        await perform_cleanup(query.message, "logs")
    elif action == "temp":
        await perform_cleanup(query.message, "temp")
    elif action == "backups":
        await perform_cleanup(query.message, "backups")
    elif action == "back":
        await query.message.edit_text(
            "⚙️ АДМИН-ПАНЕЛЬ\n\nВыберите действие:",
            reply_markup=get_admin_keyboard()
        )

@command_handler
@admin_only
async def admin_backup_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    
    await query.answer()
    
    await backup_cmd_internal(query.message)

async def backup_cmd_internal(message):
    await message.edit_text("💾 Создание бэкапа...")
    
    success, backup_path = create_safe_backup("admin_panel")
    
    if success:
        size = os.path.getsize(backup_path)
        backups = get_backup_list(3)
        
        text = "✅ БЭКАП СОЗДАН!\n\n"
        text += f"📁 Файл: {os.path.basename(backup_path)}\n"
        text += f"📏 Размер: {format_file_size(size)}\n\n"
        text += "📦 ПОСЛЕДНИЕ БЭКАПЫ:\n"
        
        for i, backup in enumerate(backups, 1):
            age = backup['age_days']
            text += f"{i}. {backup['name']} ({format_file_size(backup['size'])}), {age} дн. назад\n"
    else:
        text = f"❌ Ошибка создания бэкапа: {backup_path}"
    
    await message.edit_text(text, reply_markup=get_admin_keyboard())

@command_handler
@admin_only
async def admin_repair_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    
    await query.answer()
    
    message = query.message
    await message.edit_text(
        "⚠️ ПОДТВЕРЖДЕНИЕ ВОССТАНОВЛЕНИЯ\n\n"
        "Вы уверены, что хотите восстановить структуру данных?\n"
        "Перед восстановлением будет создан бэкап.",
        reply_markup=get_confirmation_keyboard("восстановить")
    )

@command_handler
@admin_only
async def admin_storage_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    
    await query.answer()
    
    from database import get_database_size
    
    db_stats = get_database_size()
    
    if "error" in db_stats:
        text = f"❌ Ошибка получения статистики: {db_stats['error']}"
    else:
        text = "📊 СТАТИСТИКА ХРАНИЛИЩА\n\n"
        
        if db_stats.get('exists'):
            text += f"🗃️ База данных: {db_stats['size']/1024:.1f} KB\n"
            text += f"👥 Пользователей: {db_stats['users']}\n"
            text += f"👊 Шлёпков: {db_stats['total_shleps']}\n"
            text += f"💬 Чатов: {db_stats['chats']}\n"
            if db_stats.get('last_modified'):
                text += f"📅 Изменена: {db_stats['last_modified'].strftime('%d.%m.%Y %H:%M')}\n"
        else:
            text += "🗃️ База данных: ❌ Не найдена\n"
        
        # Простая проверка доступного места
        import os
        try:
            statvfs = os.statvfs('.')
            free_gb = (statvfs.f_bavail * statvfs.f_frsize) / (1024**3)
            text += f"\n💾 Свободное место на диске: {free_gb:.1f} GB"
        except:
            text += "\n💾 Информация о диске: доступно"
    
    await query.message.edit_text(text, reply_markup=get_admin_keyboard())

@command_handler
@admin_only
async def admin_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    
    await query.answer()
    await query.message.delete()

async def perform_repair(message):
    await message.edit_text("🔧 Восстановление структуры...")
    
    from database import repair_data_structure, create_safe_backup
    
    # Создаем бэкап перед восстановлением
    success_backup, backup_path = create_safe_backup("before_repair")
    
    if not success_backup:
        await message.edit_text("⚠️ Не удалось создать бэкап перед восстановлением")
        return
    
    # Выполняем восстановление
    success = repair_data_structure()
    
    if success:
        from database import load_data
        data = load_data()
        
        text = (
            "✅ СТРУКТУРА ДАННЫХ ВОССТАНОВЛЕНА\n\n"
            f"👥 Пользователей: {len(data.get('users', {}))}\n"
            f"💬 Чатов: {len(data.get('chats', {}))}\n"
            f"👊 Всего шлёпков: {data.get('global_stats', {}).get('total_shleps', 0)}\n\n"
            "Ошибки должны быть исправлены!"
        )
    else:
        text = "❌ Не удалось восстановить структуру данных"
    
    await message.edit_text(text, reply_markup=get_admin_keyboard())

@command_handler
async def check_paths(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from config import DATA_FILE, VOTES_FILE, BACKUP_PATH
    
    text = (
        "🔍 ПРОВЕРКА ПУТЕЙ ДЛЯ ДАННЫХ:\n\n"
        f"📁 DATA_FILE: {DATA_FILE}\n"
        f"   Существует: {'✅ Да' if os.path.exists(DATA_FILE) else '❌ Нет'}\n\n"
        f"🗳️ VOTES_FILE: {VOTES_FILE}\n"
        f"   Существует: {'✅ Да' if os.path.exists(VOTES_FILE) else '❌ Нет'}\n\n"
        f"💾 BACKUP_PATH: {BACKUP_PATH}\n"
        f"   Существует: {'✅ Да' if os.path.exists(BACKUP_PATH) else '❌ Нет'}\n"
    )
    
    if os.path.exists(DATA_FILE):
        size = os.path.getsize(DATA_FILE)
        text += f"\n📏 Размер файла данных: {size:,} байт".replace(",", " ")
    
    await update.message.reply_text(text)

async def inline_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    
    await query.answer()
    data = query.data
    logger.info(f"Callback received: {data}")
    
    if data == "start_shlep_session":
        await start_shlep_session(update, context)
    elif data in ["shlep_again", "shlep_level", "shlep_stats", "shlep_my_stats", "shlep_menu"]:
        await handle_shlep_session(update, context, data)
    elif data == "shlep_mishok":
        await perform_shlep(update, context)
    elif data == "stats_inline":
        await stats(update, context)
    elif data == "level_inline":
        await level(update, context)
    elif data == "chat_top":
        await chat_top(update, context)
    elif data == "my_stats":
        await my_stats(update, context)
    elif data == "help_inline":
        await help_cmd(update, context)
    elif data == "mishok_info":
        await mishok(update, context)
    elif data in ["vote_yes", "vote_no"]:
        await handle_vote(update, context, data)
    elif data.startswith("duel_"):
        await query.answer("❌ Система дуэлей временно отключена", show_alert=True)
        try:
            await query.message.edit_reply_markup(reply_markup=None)
        except:
            pass
    
    elif data == "admin_cleanup":
        await admin_cleanup(update, context)
    elif data == "admin_health":
        await admin_health(update, context)
    elif data == "admin_stats":
        await admin_stats(update, context)
    elif data == "admin_backup":
        await admin_backup_cmd(update, context)
    elif data == "admin_repair":
        await admin_repair_cmd(update, context)
    elif data == "admin_storage":
        await admin_storage_cmd(update, context)
    elif data == "admin_close":
        await admin_close(update, context)
    elif data == "admin_back":
        await admin_panel(update, context)
    
    elif data.startswith("cleanup_"):
        action = data.replace("cleanup_", "")
        await cleanup_action(update, context, action)
    
    elif data.startswith("confirm_"):
        action = data.replace("confirm_", "")
        if action == "восстановить":
            await perform_repair(query.message)
    
    elif data == "cancel_action":
        await query.message.edit_text(
            "❌ Действие отменено",
            reply_markup=get_admin_keyboard()
        )
    
    else:
        await query.message.reply_text("⚙️ Эта функция в разработке")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        elif text == "❓ Помощь":
            await help_cmd(update, context)
        elif text in ["👴 О Мишке", "О Мишке"]:
            await mishok(update, context)
        else:
            logger.warning(f"Неизвестная кнопка: {text}")
            if update.effective_chat.type == "private":
                await update.message.reply_text(
                    "Неизвестная команда. Используйте /help для списка команд."
                )
    except Exception as e:
        logger.error(f"Ошибка в button_handler: {e}", exc_info=True)
        if update.effective_chat.type == "private":
            await update.message.reply_text(
                "⚠️ Произошла ошибка при обработке команды. Попробуйте ещё раз."
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
        ("help", help_cmd),
        ("mishok", mishok),
        ("chat_stats", chat_stats),
        ("chat_top", chat_top),
        ("vote", vote),
        ("vote_info", vote_info),
        ("backup", backup),
        ("storage", storage),
        ("check_data", check_data),
        ("repair", repair),
        ("data_info", data_info),
        ("check_paths", check_paths),
        ("admin", admin_panel),
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
    print(f"• Админ-панель: /admin")
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
