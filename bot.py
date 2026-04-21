import logging
import random
import sys
import os
import asyncio
from datetime import datetime, timedelta
from functools import wraps
from collections import deque
from typing import Dict, Deque, Optional

from telegram import Update, User
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.constants import ParseMode
from telegram.helpers import escape_markdown

from config import BOT_TOKEN, DATA_FILE, BACKUP_PATH, LOG_FILE
from database import (
    add_shlep, get_stats, get_top_users, get_user_stats, get_chat_stats,
    get_chat_top_users, backup_database, check_data_integrity,
    repair_data_structure, create_safe_backup, get_backup_list,
    get_database_size, create_vote, get_vote, get_active_chat_vote,
    add_user_vote, finish_vote, update_vote_message_id,
    ban_user, unban_user, get_banned_users, add_banned_word, get_banned_words
)

from utils import cache, get_comparison_stats, format_file_size, format_number, create_progress_bar
from keyboard import (
    get_shlep_session_keyboard, get_shlep_start_keyboard, 
    get_chat_vote_keyboard, get_main_reply_keyboard, 
    get_main_inline_keyboard, get_admin_keyboard, 
    get_confirmation_keyboard, get_cleanup_keyboard
)

from texts import (
    MISHOK_REACTIONS, MISHOK_INTRO, COMMAND_TEXTS, VOTE_TEXTS, 
    ADMIN_TEXTS, ERROR_TEXTS, LEVEL_TITLES,
    format_stats_text, format_level_text, format_vote_text, format_vote_results
)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

_user_queues: Dict[int, Deque] = {}
_user_processing: Dict[int, bool] = {}

def escape_text(text: str) -> str:
    return escape_markdown(text or "", version=1)

def get_message(update: Update):
    if update.callback_query and update.callback_query.message:
        return update.callback_query.message
    return update.message

def get_user_info(user: User):
    return {
        'name': escape_text(user.first_name),
        'username': escape_text(user.username or user.first_name),
        'full_name': escape_text(user.full_name)
    }

def handler(admin=False, chat_only=False):
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            msg = get_message(update)
            if not msg:
                logger.warning(f"Нет сообщения для {func.__name__}")
                return
            try:
                if chat_only and update.effective_chat.type == "private":
                    await msg.reply_text(ERROR_TEXTS['chat_only'])
                    return
                from config import ADMIN_ID
                if admin and update.effective_user.id != ADMIN_ID:
                    await msg.reply_text(ERROR_TEXTS['admin_only'])
                    return
                return await func(update, context, msg)
            except Exception as e:
                logger.error(f"Ошибка в {func.__name__}: {e}", exc_info=True)
                try:
                    await msg.reply_text(ERROR_TEXTS['generic'])
                except:
                    pass
        return wrapper
    return decorator

def with_message(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        msg = get_message(update)
        if not msg:
            logger.warning(f"Нет сообщения для {func.__name__}")
            return
        return await func(update, context, msg)
    return wrapper


def calc_level(cnt):
    if cnt is None or cnt < 0:
        cnt = 0
    
    if cnt == 0:
        return {
            'level': 1,
            'progress': 0,
            'min': 10,
            'max': 25,
            'next': 10
        }
    
    level = max(1, (cnt - 1) // 10 + 1)
    
    progress = (cnt % 10) * 10 if cnt % 10 != 0 else 0
    
    if level > 1000:
        min_dmg = 10 + 1000 * 2 + (level - 1000) * 1
        max_dmg = 15 + 1000 * 3 + (level - 1000) * 2
    else:
        min_dmg = int(10 * (1.02 ** min(level - 1, 100)))
        max_dmg = int(20 * (1.08 ** min(level - 1, 100)))
    
    if max_dmg <= min_dmg:
        max_dmg = min_dmg + 10
    
    next_shleps = 10 - (cnt % 10) if cnt % 10 != 0 else 0
    
    return {
        'level': level,
        'progress': progress,
        'min': min_dmg,
        'max': max_dmg,
        'next': next_shleps
    }

def level_title(lvl):
    for threshold, (title, advice) in sorted(LEVEL_TITLES.items(), reverse=True):
        if lvl >= threshold:
            return title, advice
    return "🌱 ПОЛНЫЙ ДОХЛЯК", "Ты только начал... очень слабо!"

def get_reaction(): 
    return random.choice(MISHOK_REACTIONS)

async def send_progress(message, text, progress=0):
    bar = create_progress_bar(progress)
    percentage = int(progress * 100)
    status_text = f"🔄 {text}\n[{bar}] {percentage}%"
    
    try:
        current_text = message.text or ""
        if status_text != current_text:
            await message.edit_text(status_text)
    except:
        try:
            await message.reply_text(status_text)
        except:
            pass
    
    return percentage

async def shlep_task(update: Update, context: ContextTypes.DEFAULT_TYPE, edit_message=None):
    try:
        msg = get_message(update)
        if not msg:
            return
        
        user = update.effective_user
        chat = update.effective_chat
        user_info = get_user_info(user)
        
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
                user_info['username'], 
                total_damage, 
                chat.id if chat.type != "private" else None
            )
        except KeyError as e:
            logger.error(f"Ошибка KeyError при добавлении шлёпка: {e}")
            repair_data_structure()
            total, cnt, max_dmg = add_shlep(
                user.id, 
                user_info['username'], 
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
        
        new_text = f"{get_reaction()}{rec}\n💥 Урон: {total_damage}\n👤 {user_info['name']}: {cnt} шлёпков\n🎯 Уровень {lvl['level']} ({title})"
        
        kb = get_shlep_session_keyboard()
        
        if edit_message:
            try:
                current_text = edit_message.text or ""
                if new_text != current_text:
                    await edit_message.edit_text(new_text, reply_markup=kb)
                elif update.callback_query:
                    await update.callback_query.answer("✅")
            except Exception as e:
                if "Message is not modified" in str(e):
                    if update.callback_query:
                        await update.callback_query.answer("✅")
                elif "Message to edit not found" in str(e):
                    await msg.reply_text(new_text, reply_markup=kb)
                else:
                    logger.warning(f"Не удалось отредактировать сообщение: {e}")
                    await msg.reply_text(new_text, reply_markup=kb)
        else:
            await msg.reply_text(new_text, reply_markup=kb)
        
    except Exception as e:
        logger.error(f"Ошибка в shlep_task: {e}", exc_info=True)

async def process_user_queue(user_id: int):
    if user_id not in _user_queues:
        _user_processing[user_id] = False
        return
    
    _user_processing[user_id] = True
    
    try:
        while _user_queues[user_id]:
            callback = _user_queues[user_id].popleft()
            
            try:
                await callback()
            except Exception as e:
                logger.error(f"Ошибка в обработке клика: {e}")
            
            await asyncio.sleep(0.05)
            
            if not _user_queues[user_id]:
                break
                
    finally:
        _user_processing[user_id] = False
        if user_id in _user_queues and _user_queues[user_id]:
            asyncio.create_task(process_user_queue(user_id))

async def perform_shlep(update: Update, context: ContextTypes.DEFAULT_TYPE, edit_message=None):
    try:
        msg = get_message(update)
        if not msg:
            return
        
        user = update.effective_user
        
        if user.id not in _user_queues:
            _user_queues[user.id] = deque()
            _user_processing[user.id] = False
        
        async def execute_shlep():
            await shlep_task(update, context, edit_message)
        
        _user_queues[user.id].append(execute_shlep)
        
        if not _user_processing[user.id]:
            asyncio.create_task(process_user_queue(user.id))
        
        if update.callback_query:
            try:
                await update.callback_query.answer()
            except:
                pass
        
    except Exception as e:
        logger.error(f"Ошибка в perform_shlep: {e}", exc_info=True)

@handler()
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE, msg):
    user_info = get_user_info(update.effective_user)
    
    if update.effective_chat.type == "private":
        text = COMMAND_TEXTS['start']['private'].format(name=user_info['name'])
        kb = get_main_reply_keyboard()
    else:
        text = COMMAND_TEXTS['start']['group']
        kb = get_main_inline_keyboard()
    
    await msg.reply_text(text, reply_markup=kb)

@handler()
async def shlep(update: Update, context: ContextTypes.DEFAULT_TYPE, msg):
    await perform_shlep(update, context)

@handler()
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE, msg):
    cached = await cache.get("global_stats")
    if cached:
        total, last, maxd, maxu, maxdt = cached
    else:
        total, last, maxd, maxu, maxdt = get_stats()
        await cache.set("global_stats", (total, last, maxd, maxu, maxdt))
    
    top = get_top_users(10)
    
    maxu_safe = escape_text(maxu or 'Нет')
    
    text = format_stats_text(total, last, maxd, maxu_safe, maxdt)
    
    if top:
        text += COMMAND_TEXTS['stats']['top_header']
        for i, (u, c) in enumerate(top[:5], 1):
            u_safe = escape_text(u or f'Игрок{i}')
            lvl = calc_level(c)
            medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else ""
            text += f"\n{medal}{i}. {u_safe}"
            text += f"\n   📊 {format_number(c)} | Ур. {lvl['level']}"
            text += f"\n   ⚡ Урон: {lvl['min']}-{lvl['max']}"
    
    await msg.reply_text(text)

@handler()
async def level(update: Update, context: ContextTypes.DEFAULT_TYPE, msg):
    try:
        user = update.effective_user
        user_info = get_user_info(user)
        
        cached = await cache.get(f"user_stats_{user.id}")
        if cached:
            username, cnt, last_shlep = cached
        else:
            username, cnt, last_shlep = get_user_stats(user.id)
            await cache.set(f"user_stats_{user.id}", (username, cnt, last_shlep))
        
        if cnt is None:
            cnt = 0
        
        lvl = calc_level(cnt)
        title, advice = level_title(lvl['level'])
        bar = create_progress_bar(lvl['progress'])
        
        last_date_str = None
        if last_shlep:
            if isinstance(last_shlep, datetime):
                last_date_str = last_shlep.strftime('%d.%m.%Y %H:%M')
            elif isinstance(last_shlep, str):
                try:
                    dt_obj = datetime.fromisoformat(last_shlep.replace('Z', '+00:00'))
                    last_date_str = dt_obj.strftime('%d.%m.%Y %H:%M')
                except Exception:
                    last_date_str = last_shlep
        
        text = format_level_text(
            user_info['name'], 
            format_number(cnt), 
            lvl['level'], 
            title, 
            bar, 
            lvl['progress'], 
            lvl['min'], 
            lvl['max'], 
            lvl['next'], 
            advice, 
            last_date_str
        )
        
        await msg.reply_text(text)
        
    except Exception as e:
        logger.error(f"Ошибка в команде level: {e}", exc_info=True)
        await msg.reply_text("⚠️ Произошла ошибка при получении уровня. Попробуйте позже.")

@handler()
async def my_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, msg):
    user = update.effective_user
    
    username, cnt, last_shlep = get_user_stats(user.id)
    lvl = calc_level(cnt)
    compare_stats = get_comparison_stats(user.id)
    
    text = f"{COMMAND_TEXTS['my_stats']['header']}\n"
    text += f"{COMMAND_TEXTS['my_stats']['player'].format(name=user.first_name)}\n"
    text += f"{COMMAND_TEXTS['my_stats']['shlep_count'].format(count=format_number(cnt))}\n"
    text += f"{COMMAND_TEXTS['my_stats']['level'].format(level=lvl['level'])}\n"
    text += f"{COMMAND_TEXTS['my_stats']['damage_range'].format(min=lvl['min'], max=lvl['max'])}\n"
    text += f"{COMMAND_TEXTS['my_stats']['comparison_header']}\n"
    text += f"{COMMAND_TEXTS['my_stats']['total_users'].format(count=compare_stats.get('total_users', 0))}\n"
    text += f"{COMMAND_TEXTS['my_stats']['avg_shleps'].format(avg=compare_stats.get('avg_shleps', 0))}\n"
    text += f"{COMMAND_TEXTS['my_stats']['rank'].format(rank=compare_stats.get('rank', 1))}\n"
    text += f"{COMMAND_TEXTS['my_stats']['percentile'].format(percent=compare_stats.get('percentile', 0))}\n"
    
    if last_shlep:
        if isinstance(last_shlep, datetime):
            date_str = last_shlep.strftime('%d.%m.%Y %H:%M')
        else:
            date_str = str(last_shlep)
        text += f"\n{COMMAND_TEXTS['my_stats']['last_shlep'].format(date=date_str)}"
    
    await msg.reply_text(text)

@handler(chat_only=True)
async def chat_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, msg):
    chat = update.effective_chat
    
    cached = await cache.get(f"chat_stats_{chat.id}")
    if cached:
        cs = cached
    else:
        cs = get_chat_stats(chat.id)
        await cache.set(f"chat_stats_{chat.id}", cs)
    
    if not cs:
        text = COMMAND_TEXTS['chat_stats']['empty']
    else:
        max_user_safe = escape_text(cs.get('max_damage_user', 'Нет'))
        text = f"{COMMAND_TEXTS['chat_stats']['header']}\n"
        text += f"{COMMAND_TEXTS['chat_stats']['users'].format(count=cs.get('total_users', 0))}\n"
        text += f"{COMMAND_TEXTS['chat_stats']['shleps'].format(count=format_number(cs.get('total_shleps', 0)))}\n"
        text += f"{COMMAND_TEXTS['chat_stats']['record_damage'].format(damage=cs.get('max_damage', 0))}\n"
        text += f"{COMMAND_TEXTS['chat_stats']['record_user'].format(user=max_user_safe)}"
    
    await msg.reply_text(text)

@handler(chat_only=True)
async def chat_top(update: Update, context: ContextTypes.DEFAULT_TYPE, msg):
    chat = update.effective_chat
    top = get_chat_top_users(chat.id, 10)
    
    if not top:
        await msg.reply_text(COMMAND_TEXTS['chat_top']['empty'])
        return
    
    text = COMMAND_TEXTS['chat_top']['header']
    for i, (u, c) in enumerate(top, 1):
        u_safe = escape_text(u)
        lvl = calc_level(c)
        medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else ""
        text += f"{medal}{i}. {u_safe}\n"
        text += f"   📊 {format_number(c)} | Ур. {lvl['level']}\n"
        text += f"   ⚡ Урон: {lvl['min']}-{lvl['max']}\n\n"
    
    await msg.reply_text(text)

async def vote_timer(vote_id: str, chat_id: int, message_id: int, context: ContextTypes.DEFAULT_TYPE):
    try:
        vote = get_vote(vote_id)
        if not vote:
            return
        
        ends_at = datetime.fromisoformat(vote["ends_at"])
        wait_time = (ends_at - datetime.now()).total_seconds()
        
        if wait_time > 0:
            await asyncio.sleep(wait_time)
        
        vote = get_vote(vote_id)
        if vote and vote.get("active", False):
            await finish_vote_task(vote_id, chat_id, message_id, context)
            
    except asyncio.CancelledError:
        logger.info(f"Таймер голосования {vote_id} отменён")
    except Exception as e:
        logger.error(f"Ошибка в таймере голосования: {e}")

async def finish_vote_task(vote_id: str, chat_id: int, message_id: int, context: ContextTypes.DEFAULT_TYPE):
    try:
        vote = finish_vote(vote_id)
        if not vote:
            return
        
        yes_count = len(vote.get("votes_yes", []))
        no_count = len(vote.get("votes_no", []))
        total_votes = yes_count + no_count
        
        if total_votes == 0:
            result_key = 'none'
            action_key = 'none'
            mishok_text = None
        elif yes_count > no_count:
            result_key = 'yes'
            action_key = 'yes'
            mishok_text = random.choice(VOTE_TEXTS['mishok_reactions']['yes'])
        elif no_count > yes_count:
            result_key = 'no'
            action_key = 'no'
            mishok_text = random.choice(VOTE_TEXTS['mishok_reactions']['no'])
        else:
            result_key = 'tie'
            action_key = 'tie'
            mishok_text = random.choice(VOTE_TEXTS['mishok_reactions']['tie'])
        
        text = format_vote_results(vote['question'], yes_count, no_count, result_key, action_key)
        
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=None
            )
        except Exception as e:
            if "Message to edit not found" not in str(e):
                logger.error(f"Ошибка обновления сообщения голосования: {e}")
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode=ParseMode.MARKDOWN
                )
        
        if mishok_text:
            async def send_mishok_message():
                await asyncio.sleep(1)
                try:
                    await context.bot.send_message(chat_id=chat_id, text=mishok_text)
                except Exception as e:
                    logger.error(f"Ошибка отправки сообщения Мишка: {e}")
            
            asyncio.create_task(send_mishok_message())
        
        logger.info(f"Голосование завершено: {vote_id}, результат: {result_key}")
        
    except Exception as e:
        logger.error(f"Ошибка завершения голосования: {e}")

@handler(chat_only=True)
async def vote(update: Update, context: ContextTypes.DEFAULT_TYPE, msg):
    active_vote = get_active_chat_vote(msg.chat_id)
    if active_vote:
        ends_at = datetime.fromisoformat(active_vote["ends_at"])
        time_left = (ends_at - datetime.now()).seconds
        minutes = time_left // 60
        seconds = time_left % 60
        
        await msg.reply_text(
            VOTE_TEXTS['active_exists'].format(
                question=active_vote['question'],
                yes_count=len(active_vote.get('votes_yes', [])),
                no_count=len(active_vote.get('votes_no', [])),
                minutes=minutes,
                seconds=seconds
            )
        )
        return
    
    question = " ".join(context.args) if context.args else "Шлёпнуть Мишка?"
    question_safe = escape_text(question)
    
    vote_id = create_vote(msg.chat_id, question, duration_minutes=5)
    
    if not vote_id:
        await msg.reply_text(ERROR_TEXTS['vote'])
        return
    
    text = format_vote_text(question_safe, 0, 0)
    
    sent_message = await msg.reply_text(
        text, 
        reply_markup=get_chat_vote_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )
    
    update_vote_message_id(vote_id, sent_message.message_id)
    
    asyncio.create_task(vote_timer(vote_id, msg.chat_id, sent_message.message_id, context))
    
    logger.info(f"Создано голосование: {question} в чате {msg.chat_id}")

@handler(chat_only=True)
async def vote_end(update: Update, context: ContextTypes.DEFAULT_TYPE, msg):
    active_vote = get_active_chat_vote(msg.chat_id)
    
    if not active_vote:
        await msg.reply_text(ERROR_TEXTS['vote_not_found'])
        return
    
    from config import ADMIN_ID
    user = update.effective_user
    
    try:
        creator_id = int(active_vote["id"].split("_")[0])
    except:
        creator_id = None
    
    if user.id != ADMIN_ID and (creator_id and user.id != creator_id):
        await msg.reply_text(ERROR_TEXTS['vote_permission'])
        return
    
    await finish_vote_task(active_vote["id"], msg.chat_id, active_vote.get("message_id"), context)

def get_vote_message_text(vote_data):
    ends_at = datetime.fromisoformat(vote_data["ends_at"])
    time_left = (ends_at - datetime.now()).seconds
    minutes = time_left // 60
    seconds = time_left % 60
    
    return format_vote_text(
        vote_data['question'],
        len(vote_data.get('votes_yes', [])),
        len(vote_data.get('votes_no', [])),
        action=f"Осталось: {minutes:02d}:{seconds:02d}"
    )

async def handle_vote(update: Update, context: ContextTypes.DEFAULT_TYPE, vote_type: str):
    try:
        query = update.callback_query
        if not query:
            return
            
        await query.answer()
        user = update.effective_user
        
        active_vote = get_active_chat_vote(query.message.chat.id)
        if not active_vote:
            await query.answer(ERROR_TEXTS['vote_active'], show_alert=True)
            return
        
        if vote_type not in ["yes", "no"]:
            await query.answer(ERROR_TEXTS['vote_type'], show_alert=True)
            return
        
        success = add_user_vote(active_vote["id"], user.id, vote_type)
        
        if not success:
            await query.answer(ERROR_TEXTS['vote_error'], show_alert=True)
            return
        
        active_vote = get_vote(active_vote["id"])
        if not active_vote:
            await query.answer(ERROR_TEXTS['vote_not_found_alert'], show_alert=True)
            return
        
        vote_text = get_vote_message_text(active_vote)
        
        try:
            await query.message.edit_text(
                vote_text,
                reply_markup=get_chat_vote_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Ошибка обновления сообщения: {e}")
        
        if vote_type == "yes":
            await query.answer(ERROR_TEXTS['vote_counted_yes'])
        else:
            await query.answer(ERROR_TEXTS['vote_counted_no'])
        
    except Exception as e:
        logger.error(f"Ошибка обработки голоса: {e}", exc_info=True)
        try:
            await query.answer(ERROR_TEXTS['vote_processing_alert'], show_alert=True)
        except:
            pass

@handler()
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE, msg):
    await msg.reply_text(COMMAND_TEXTS['help'])

@handler()
async def mishok(update: Update, context: ContextTypes.DEFAULT_TYPE, msg):
    try:
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

@handler(admin=True)
async def backup_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE, msg):
    status_msg = await msg.reply_text(ADMIN_TEXTS['backup'])
    
    await send_progress(status_msg, "Создание безопасного бэкапа", 0.3)
    success, backup_path = create_safe_backup("manual")
    
    if success:
        await send_progress(status_msg, "Бэкап создан", 0.7)
        
        size = os.path.getsize(backup_path)
        backups = get_backup_list(5)
        
        text = ADMIN_TEXTS['backup_result']['success']
        text += ADMIN_TEXTS['backup_result']['file'].format(name=os.path.basename(backup_path))
        text += ADMIN_TEXTS['backup_result']['size'].format(size=format_file_size(size))
        text += ADMIN_TEXTS['backup_result']['list_header']
        
        for i, backup in enumerate(backups, 1):
            age = backup['age_days']
            text += f"{i}. {backup['name']} ({format_file_size(backup['size'])}), {age} дн. назад\n"
        
        await status_msg.edit_text(text)
    else:
        await status_msg.edit_text(ADMIN_TEXTS['backup_result']['error'].format(error=backup_path))

@handler()
async def check_data(update: Update, context: ContextTypes.DEFAULT_TYPE, msg):
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
        await msg.reply_text(ERROR_TEXTS['data_check'].format(error=str(e)))

@handler(admin=True)
async def repair_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE, msg):
    status_msg = await msg.reply_text("🔄 Восстановление структуры данных...")
    
    await send_progress(status_msg, "Создание бэкапа перед восстановлением", 0.2)
    create_safe_backup("before_repair")
    
    await send_progress(status_msg, "Восстановление структуры", 0.5)
    success = repair_data_structure()
    
    if success:
        await send_progress(status_msg, "Загрузка данных для проверки", 0.8)
        from database import load_data
        data = load_data()
        
        text = ADMIN_TEXTS['repair_result']['success'].format(
            users=len(data.get('users', {})),
            chats=len(data.get('chats', {})),
            shleps=data.get('global_stats', {}).get('total_shleps', 0)
        )
    else:
        text = ADMIN_TEXTS['repair_result']['error']
    
    await status_msg.edit_text(text)

async def start_shlep_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    
    await query.answer()
    
    user = update.effective_user
    user_info = get_user_info(user)
    text = f"👤 {user_info['name']}, начинаем сессию шлёпания!\n\nНажимай '👊 Ещё раз!' для следующего шлёпка\nТекущие результаты будут обновляться здесь"
    
    await perform_shlep(update, context, edit_message=query.message)

async def handle_shlep_session(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str):
    query = update.callback_query
    if not query:
        return
    
    try:
        await query.answer()
    except:
        pass
    
    if action == "shlep_again":
        await perform_shlep(update, context, edit_message=query.message)
    elif action == "shlep_level":
        user = update.effective_user
        user_info = get_user_info(user)
        
        cached = await cache.get(f"user_stats_{user.id}")
        if cached:
            u, cnt, last = cached
        else:
            u, cnt, last = get_user_stats(user.id)
            await cache.set(f"user_stats_{user.id}", (u, cnt, last))
        
        lvl = calc_level(cnt)
        title, advice = level_title(lvl['level'])
        bar = create_progress_bar(lvl['progress'])
        
        last_date = last.strftime('%d.%m.%Y %H:%M') if last else None
        text = format_level_text(
            user_info['name'], format_number(cnt), lvl['level'], title, 
            bar, lvl['progress'], lvl['min'], lvl['max'], 
            lvl['next'], advice, last_date
        )
        
        await query.message.edit_text(text, reply_markup=get_shlep_session_keyboard())
    elif action == "shlep_stats":
        cached = await cache.get("global_stats")
        if cached:
            total, last, maxd, maxu, maxdt = cached
        else:
            total, last, maxd, maxu, maxdt = get_stats()
            await cache.set("global_stats", (total, last, maxd, maxu, maxdt))
        
        maxu_safe = escape_text(maxu or 'Нет')
        text = format_stats_text(total, last, maxd, maxu_safe, maxdt)
        
        await query.message.edit_text(text, reply_markup=get_shlep_session_keyboard())
    elif action == "shlep_my_stats":
        user = update.effective_user
        _, cnt, last = get_user_stats(user.id)
        lvl = calc_level(cnt)
        compare_stats = get_comparison_stats(user.id)
        
        text = f"{COMMAND_TEXTS['my_stats']['header']}\n"
        text += f"{COMMAND_TEXTS['my_stats']['player'].format(name=user.first_name)}\n"
        text += f"{COMMAND_TEXTS['my_stats']['shlep_count'].format(count=format_number(cnt))}\n"
        text += f"{COMMAND_TEXTS['my_stats']['level'].format(level=lvl['level'])}\n"
        text += f"{COMMAND_TEXTS['my_stats']['damage_range'].format(min=lvl['min'], max=lvl['max'])}\n"
        text += f"{COMMAND_TEXTS['my_stats']['comparison_header']}\n"
        text += f"{COMMAND_TEXTS['my_stats']['total_users'].format(count=compare_stats.get('total_users', 0))}\n"
        text += f"{COMMAND_TEXTS['my_stats']['avg_shleps'].format(avg=compare_stats.get('avg_shleps', 0))}\n"
        text += f"{COMMAND_TEXTS['my_stats']['rank'].format(rank=compare_stats.get('rank', 1))}\n"
        text += f"{COMMAND_TEXTS['my_stats']['percentile'].format(percent=compare_stats.get('percentile', 0))}\n"
        
        if last:
            text += f"\n{COMMAND_TEXTS['my_stats']['last_shlep'].format(date=last.strftime('%d.%m.%Y %H:%M'))}"
        
        await query.message.edit_text(text, reply_markup=get_shlep_session_keyboard())
    elif action == "shlep_menu":
        user_info = get_user_info(update.effective_user)
        text = f"👋 Привет, {user_info['name']}!\nЯ — Мишок Лысый 👴✨\n\nНачни шlёпать прямо сейчас!"
        await query.message.edit_text(text, reply_markup=get_shlep_start_keyboard())

@handler(admin=True)
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE, msg):
    await msg.reply_text(
        ADMIN_TEXTS['panel'],
        reply_markup=get_admin_keyboard()
    )

@handler(admin=True)
async def admin_health(update: Update, context: ContextTypes.DEFAULT_TYPE, msg):
    await msg.edit_text(ADMIN_TEXTS['health_check'])
    
    try:
        import platform
        
        status_msg = msg
        
        from database import get_database_size, check_data_integrity
        
        db_stats = get_database_size()
        integrity = check_data_integrity()
        
        try:
            import shutil
            total, used, free = shutil.disk_usage(".")
            disk_info = f"Диск: {used/(1024**3):.1f} GB из {total/(1024**3):.1f} использовано ({used/total*100:.1f}%)"
        except:
            disk_info = "Информация о диске: доступно"
        
        report = ADMIN_TEXTS['health_report']['header']
        
        report += ADMIN_TEXTS['health_report']['python'].format(version=platform.python_version()) + "\n"
        report += ADMIN_TEXTS['health_report']['system'].format(system=platform.system(), machine=platform.machine()) + "\n"
        report += ADMIN_TEXTS['health_report']['disk'].format(info=disk_info) + "\n"
        
        if db_stats.get("exists"):
            report += ADMIN_TEXTS['health_report']['db_exists'].format(size=db_stats.get('size', 0)/1024) + "\n"
            report += ADMIN_TEXTS['health_report']['users'].format(count=db_stats.get('users', 0)) + "\n"
            report += ADMIN_TEXTS['health_report']['shleps'].format(count=db_stats.get('total_shleps', 0)) + "\n"
        else:
            report += ADMIN_TEXTS['health_report']['db_not_exists'] + "\n"
        
        report += ADMIN_TEXTS['health_report']['integrity'].format(
            errors=len(integrity['errors']), 
            warnings=len(integrity['warnings'])
        ) + "\n"
        
        all_good = (not integrity['errors'] and db_stats.get("exists", False))
        
        if all_good:
            report += ADMIN_TEXTS['health_report']['all_good']
        else:
            report += ADMIN_TEXTS['health_report']['attention']
        
        await status_msg.edit_text(report, reply_markup=get_admin_keyboard())
        
    except Exception as e:
        await msg.edit_text(
            ERROR_TEXTS['health_check'].format(error=str(e)[:200]),
            reply_markup=get_admin_keyboard()
        )

@handler(admin=True)
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, msg):
    await msg.edit_text(ADMIN_TEXTS['user_stats'])
    
    from database import load_data
    
    data = load_data()
    users = data.get('users', {})
    
    if not users:
        await msg.edit_text("📭 Нет данных о пользователях", reply_markup=get_admin_keyboard())
        return
    
    now = datetime.now()
    
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
                last_date = datetime.fromisoformat(last_shlep)
                days_diff = (now - last_date).days
                
                if days_diff == 0:
                    active_today += 1
                if days_diff <= 7:
                    active_week += 1
            except:
                pass
    
    avg_shleps = total_shleps / len(users) if users else 0
    
    report = ADMIN_TEXTS['user_stats_report']['header']
    
    report += ADMIN_TEXTS['user_stats_report']['total_users'].format(count=len(users)) + "\n"
    report += ADMIN_TEXTS['user_stats_report']['active_today'].format(count=active_today) + "\n"
    report += ADMIN_TEXTS['user_stats_report']['active_week'].format(count=active_week) + "\n"
    report += ADMIN_TEXTS['user_stats_report']['total_shleps'].format(count=total_shleps) + "\n"
    report += ADMIN_TEXTS['user_stats_report']['avg_shleps'].format(avg=avg_shleps) + "\n"
    report += ADMIN_TEXTS['user_stats_report']['record_user'].format(user=max_user, count=max_shleps) + "\n\n"
    
    level_distribution = {}
    for user_data in users.values():
        shleps = user_data.get("total_shleps", 0)
        level = (shleps // 10) + 1
        level_key = f"{min(level, 100)}+" if level > 100 else str(level)
        level_distribution[level_key] = level_distribution.get(level_key, 0) + 1
    
    report += ADMIN_TEXTS['user_stats_report']['levels_header'] + "\n"
    for level, count in sorted(level_distribution.items(), key=lambda x: int(x[0].replace('+', ''))):
        percentage = (count / len(users)) * 100
        bar = create_progress_bar(percentage)
        report += ADMIN_TEXTS['user_stats_report']['level_item'].format(
            level=level, bar=bar, percent=percentage, count=count
        ) + "\n"
    
    await msg.edit_text(report, reply_markup=get_admin_keyboard())

@handler(admin=True)
async def admin_cleanup(update: Update, context: ContextTypes.DEFAULT_TYPE, msg):
    await msg.edit_text(
        ADMIN_TEXTS['cleanup'],
        reply_markup=get_cleanup_keyboard()
    )

async def perform_cleanup(message, cleanup_type):
    await message.edit_text(ADMIN_TEXTS['cleanup_progress'].format(type=cleanup_type))
    
    import glob
    
    total_cleaned = 0
    total_freed = 0
    
    if cleanup_type == "logs":
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
    
    result_text = ADMIN_TEXTS['cleanup_result'].format(count=total_cleaned, mb=freed_mb)
    
    await message.edit_text(result_text, reply_markup=get_admin_keyboard())

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
            ADMIN_TEXTS['panel'],
            reply_markup=get_admin_keyboard()
        )

async def admin_backup_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    
    await query.answer()
    
    await backup_cmd_internal(query.message)

async def backup_cmd_internal(message):
    await message.edit_text(ADMIN_TEXTS['backup'])
    
    success, backup_path = create_safe_backup("admin_panel")
    
    if success:
        size = os.path.getsize(backup_path)
        backups = get_backup_list(3)
        
        text = ADMIN_TEXTS['backup_result']['success']
        text += ADMIN_TEXTS['backup_result']['file'].format(name=os.path.basename(backup_path))
        text += ADMIN_TEXTS['backup_result']['size'].format(size=format_file_size(size))
        text += ADMIN_TEXTS['backup_result']['list_header']
        
        for i, backup in enumerate(backups, 1):
            age = backup['age_days']
            text += f"{i}. {backup['name']} ({format_file_size(backup['size'])}), {age} дн. назад\n"
    else:
        text = ADMIN_TEXTS['backup_result']['error'].format(error=backup_path)
    
    await message.edit_text(text, reply_markup=get_admin_keyboard())

@handler(admin=True)
async def admin_repair_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE, msg):
    await msg.edit_text(
        ADMIN_TEXTS['repair_confirm'],
        reply_markup=get_confirmation_keyboard("восстановить")
    )

async def admin_storage_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    
    await query.answer()
    
    from database import get_database_size
    
    db_stats = get_database_size()
    
    if "error" in db_stats:
        text = ADMIN_TEXTS['storage_stats']['error'].format(error=db_stats['error'])
    else:
        text = ADMIN_TEXTS['storage_stats']['header']
        
        if db_stats.get('exists'):
            text += ADMIN_TEXTS['storage_stats']['db_exists'].format(
                size=db_stats['size']/1024,
                users=db_stats['users'],
                shleps=db_stats['total_shleps'],
                chats=db_stats['chats']
            )
            if db_stats.get('last_modified'):
                text += f"\n{ADMIN_TEXTS['storage_stats']['db_modified'].format(date=db_stats['last_modified'].strftime('%d.%m.%Y %H:%M'))}"
        else:
            text += ADMIN_TEXTS['storage_stats']['db_not_exists']
        
        try:
            statvfs = os.statvfs('.')
            free_gb = (statvfs.f_bavail * statvfs.f_frsize) / (1024**3)
            text += ADMIN_TEXTS['storage_stats']['disk'].format(gb=free_gb)
        except:
            text += ADMIN_TEXTS['storage_stats']['disk_error']
    
    await query.message.edit_text(text, reply_markup=get_admin_keyboard())

async def admin_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    
    await query.answer()
    await query.message.delete()

async def perform_repair(message):
    try:
        await message.edit_text(ADMIN_TEXTS['repair'])
    except:
        pass
    
    from database import repair_data_structure, create_safe_backup
    
    success_backup, backup_path = create_safe_backup("before_repair")
    
    if not success_backup:
        try:
            await message.edit_text("⚠️ Не удалось создать бэкап перед восстановлением")
        except:
            pass
        return
    
    success = repair_data_structure()
    
    if success:
        from database import load_data
        data = load_data()
        
        text = ADMIN_TEXTS['repair_result']['success'].format(
            users=len(data.get('users', {})),
            chats=len(data.get('chats', {})),
            shleps=data.get('global_stats', {}).get('total_shleps', 0)
        )
    else:
        text = ADMIN_TEXTS['repair_result']['error']
    
    try:
        await message.edit_text(text, reply_markup=get_admin_keyboard())
    except:
        pass

@handler(admin=True)
async def admin_bans(update: Update, context: ContextTypes.DEFAULT_TYPE, msg):
    # Показать список забаненных в текущем чате
    chat_id = update.effective_chat.id
    banned = get_banned_users(chat_id)

    if not banned:
        text = "🚫 В этом чате нет забаненных пользователей."
    else:
        text = f"🚫 Забаненные пользователи в этом чате ({len(banned)}):\n\n"
        for uid in banned:
            text += f"• {uid}\n"

    await msg.reply_text(text, reply_markup=get_admin_keyboard())

@handler(admin=True)
async def debug_user(update: Update, context: ContextTypes.DEFAULT_TYPE, msg):
    from database import load_data
    user = update.effective_user

    data = load_data()
    user_data = data["users"].get(str(user.id), {})

    text = f"🔍 ДЕБАГ ДАННЫХ ДЛЯ user_id={user.id}\n\n"
    text += f"📊 Сырые данные:\n"

    for key, value in user_data.items():
        text += f"  {key}: {value} (тип: {type(value).__name__})\n"

    text += f"\n🧪 Результат get_user_stats:\n"
    username, cnt, last_shlep = get_user_stats(user.id)
    text += f"  username: {username}\n"
    text += f"  cnt: {cnt} (тип: {type(cnt).__name__})\n"
    text += f"  last_shlep: {last_shlep} (тип: {type(last_shlep).__name__})\n"

    text += f"\n🎯 Результат calc_level({cnt}):\n"
    lvl = calc_level(cnt)
    for key, value in lvl.items():
        text += f"  {key}: {value}\n"

    await msg.reply_text(f"<pre>{text}</pre>", parse_mode=ParseMode.HTML)

async def get_mentioned_user_id(msg, context, chat_id) -> Optional[int]:
    """Получить user_id из упоминания @username в сообщении или reply"""
    # Сначала проверить reply
    if msg.reply_to_message:
        return msg.reply_to_message.from_user.id

    if not msg.entities:
        return None
    for entity in msg.entities:
        if entity.type == "mention":
            username = msg.text[entity.offset + 1:entity.offset + entity.length]  # без @
            if hasattr(entity, 'user') and entity.user:
                return entity.user.id
            else:
                # Попробовать получить по username
                try:
                    member = await context.bot.get_chat_member(chat_id, username)
                    return member.user.id
                except:
                    return None
    return None

@handler(admin=True, chat_only=True)
async def mishok_ban(update: Update, context: ContextTypes.DEFAULT_TYPE, msg):
    chat_id = update.effective_chat.id
    mentioned_user_id = await get_mentioned_user_id(msg, context, chat_id)

    if not mentioned_user_id:
        await msg.reply_text("❌ Укажите пользователя для бана с помощью @username или ответьте на его сообщение")
        return

    if ban_user(chat_id, mentioned_user_id):
        await msg.reply_text(f"✅ Пользователь забанен. Все его сообщения будут автоматически удаляться.")
    else:
        await msg.reply_text("❌ Не удалось забанить пользователя или он уже забанен.")

@handler(admin=True, chat_only=True)
async def mishok_unban(update: Update, context: ContextTypes.DEFAULT_TYPE, msg):
    chat_id = update.effective_chat.id
    mentioned_user_id = await get_mentioned_user_id(msg, context, chat_id)

    if not mentioned_user_id:
        await msg.reply_text("❌ Укажите пользователя для разбана с помощью @username или ответьте на его сообщение")
        return

    if unban_user(chat_id, mentioned_user_id):
        await msg.reply_text(f"✅ Пользователь разбанен.")
    else:
        await msg.reply_text("❌ Не удалось разбанить пользователя или он не был забанен.")

@handler(admin=True, chat_only=True)
async def mishok_banword(update: Update, context: ContextTypes.DEFAULT_TYPE, msg):
    chat_id = update.effective_chat.id
    text = msg.text.strip()

    # Ожидаем /MishokBanWord слово
    parts = text.split()
    if len(parts) < 2:
        await msg.reply_text("❌ Укажите слово для бана: /MishokBanWord <слово>")
        return

    word = " ".join(parts[1:]).strip()
    if not word:
        await msg.reply_text("❌ Слово не может быть пустым.")
        return

    if add_banned_word(chat_id, word):
        await msg.reply_text(f"✅ Слово '{word}' добавлено в банворды.")
    else:
        await msg.reply_text(f"❌ Слово '{word}' уже в банвордах.")

async def inline_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    
    await query.answer()
    data = query.data
    
    if data == "start_shlep_session":
        await start_shlep_session(update, context)
    elif data in ["shlep_again", "shlep_level", "shlep_stats", "shlep_my_stats", "shlep_menu"]:
        await handle_shlep_session(update, context, data)
    
    elif data == "shlep_mishok":
        await perform_shlep(update, context)
    elif data == "stats_inline":
        await stats(update, context, query.message)
    elif data == "level_inline":
        await level(update, context, query.message)
    elif data == "chat_top":
        await chat_top(update, context, query.message)
    elif data == "my_stats":
        await my_stats(update, context, query.message)
    elif data == "help_inline":
        await help_cmd(update, context, query.message)
    elif data == "mishok_info":
        await mishok(update, context, query.message)
    
    elif data in ["vote_yes", "vote_no"]:
        vote_type = data.replace("vote_", "")
        await handle_vote(update, context, vote_type)
    
    elif data.startswith("duel_"):
        await query.answer(ERROR_TEXTS['duel_disabled'], show_alert=True)
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
    elif data == "admin_bans":
        await admin_bans(update, context)
    elif data == "admin_close":
        await admin_close(update, context)
    elif data == "admin_back":
        await admin_panel(update, context, query.message)
    elif data == "debug_user":
        await debug_user(update, context, query.message)
    
    elif data.startswith("cleanup_"):
        action = data.replace("cleanup_", "")
        await cleanup_action(update, context, action)
    
    elif data.startswith("confirm_"):
        action = data.replace("confirm_", "")
        if action == "восстановить":
            await perform_repair(query.message)
    
    elif data == "cancel_action":
        await query.message.edit_text(
            ADMIN_TEXTS['cancel'],
            reply_markup=get_admin_keyboard()
        )
    
    else:
        await query.message.reply_text(ERROR_TEXTS['function'])

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    
    text = update.message.text
    
    try:
        if text == "👊 Шлёпнуть Мишка":
            await shlep(update, context, update.message)
        elif text == "🎯 Уровень":
            await level(update, context, update.message)
        elif text == "📊 Статистика":
            await stats(update, context, update.message)
        elif text == "📈 Моя статистика":
            await my_stats(update, context, update.message)
        elif text == "❓ Помощь":
            await help_cmd(update, context, update.message)
        elif text in ["👴 О Мишке", "О Мишке"]:
            await mishok(update, context, update.message)
        else:
            logger.warning(f"Неизвестная кнопка: {text}")
            if update.effective_chat.type == "private":
                await update.message.reply_text(ERROR_TEXTS['unknown_button'])
    except Exception as e:
        logger.error(f"Ошибка в button_handler: {e}", exc_info=True)
        if update.effective_chat.type == "private":
            await update.message.reply_text(ERROR_TEXTS['command'])

async def check_banned_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка и удаление сообщений забаненных пользователей"""
    logger.info(f"check_banned_messages вызвана для {update.effective_user.id} в {update.effective_chat.id}, тип чата: {update.effective_chat.type}")
    if not update.message or update.effective_chat.type == "private":
        logger.info("Пропуск: нет сообщения или приватный чат")
        return

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    banned_users = get_banned_users(chat_id)
    banned_words = get_banned_words(chat_id)
    logger.info(f"Проверка пользователя {user_id} в чате {chat_id}, забаненные: {banned_users}, банворды: {banned_words}")

    message_text = update.message.text.lower() if update.message.text else ""

    # Проверка на банворды
    if any(word in message_text for word in banned_words):
        if ban_user(chat_id, user_id):
            logger.info(f"Пользователь {user_id} забанен за использование банворда в чате {chat_id}")
            try:
                await update.message.delete()
                logger.info(f"Удалено сообщение с банвордом от {user_id} в чате {chat_id}")
            except Exception as e:
                logger.error(f"Не удалось удалить сообщение от {user_id}: {e}")
        return

    if user_id in banned_users:
        try:
            await update.message.delete()
            logger.info(f"Удалено сообщение от забаненного пользователя {user_id} в чате {chat_id}")
        except Exception as e:
            logger.error(f"Не удалось удалить сообщение от {user_id}: {e}")

async def group_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.new_chat_members:
        for m in update.message.new_chat_members:
            if m.id == context.bot.id:
                await update.message.reply_text(COMMAND_TEXTS['welcome_group'])

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Ошибка: {context.error}", exc_info=True)

def main():
    if not BOT_TOKEN:
        logger.error(ERROR_TEXTS['no_token'])
        sys.exit(1)

    logger.info("Запуск бота с токеном: {}...".format(BOT_TOKEN[:10]))
    logger.info("Используется polling для получения обновлений")

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
        ("vote_end", vote_end),
        ("backup", backup_cmd),
        ("check_data", check_data),
        ("repair", repair_cmd),
        ("admin", admin_panel),
        ("debug_user", debug_user),
        ("MishokBan", mishok_ban),
        ("MishokUnban", mishok_unban),
        ("MishokBanWord", mishok_banword),
    ]
    
    for name, handler in commands:
        app.add_handler(CommandHandler(name, handler))
    
    app.add_handler(CallbackQueryHandler(inline_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, group_welcome))
    app.add_handler(MessageHandler(filters.ChatType.GROUPS & ~filters.COMMAND, check_banned_messages))
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
        logger.error(ERROR_TEXTS['bot'].format(error=e))
        sys.exit(1)

if __name__ == "__main__":
    main()
