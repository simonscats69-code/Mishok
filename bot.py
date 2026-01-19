import logging, random, sys, os
from datetime import datetime
from functools import wraps
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.constants import ParseMode

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

_CONFIG, _DB, _KEYBOARD, _CACHE, _STATS = None, None, None, None, None

def get_config():
    global _CONFIG
    if _CONFIG is None:
        try: from config import BOT_TOKEN, MISHOK_REACTIONS, MISHOK_INTRO
        except ImportError: BOT_TOKEN, MISHOK_REACTIONS, MISHOK_INTRO = "", ["Ой!"], "Мишок Лысый"
        _CONFIG = {'BOT_TOKEN': BOT_TOKEN, 'MISHOK_REACTIONS': MISHOK_REACTIONS, 'MISHOK_INTRO': MISHOK_INTRO}
    return _CONFIG

def get_db():
    global _DB
    if _DB is None:
        try:
            from database import init_db, add_shlep, get_stats, get_top_users, get_user_stats, get_chat_stats, get_chat_top_users, backup_database
            _DB = {'init': init_db, 'add': add_shlep, 'stats': get_stats, 'top': get_top_users, 'user': get_user_stats, 'chat': get_chat_stats, 'chat_top': get_chat_top_users, 'backup': backup_database}
            _DB['init']()
        except ImportError:
            _DB = {'add': lambda *_: (0,0,0), 'stats': lambda: (0,None,0,None,None), 'top': lambda _=10: [], 'user': lambda uid: (f"Игрок_{uid}",0,None), 'chat': lambda _: None, 'chat_top': lambda *_: [], 'backup': lambda: False}
    return _DB

def get_keyboard():
    global _KEYBOARD
    if _KEYBOARD is None:
        try: from keyboard import get_chat_quick_actions as quick, get_inline_keyboard as inline
        except ImportError: quick = inline = lambda: None
        _KEYBOARD = {'quick': quick, 'inline': inline}
    return _KEYBOARD

def get_cache():
    global _CACHE
    if _CACHE is None:
        try: from cache import cache
        except ImportError:
            class StubCache: get, set, delete, get_stats = lambda *_: None, lambda *_: None, lambda *_: False, lambda: {}
            cache = StubCache()
        _CACHE = cache
    return _CACHE

def get_stats_module():
    global _STATS
    if _STATS is None:
        try:
            from statistics import get_favorite_time, get_comparison_stats, get_global_trends_info, format_daily_activity_chart, format_hourly_distribution_chart
            _STATS = {'time': get_favorite_time, 'compare': get_comparison_stats, 'trends': get_global_trends_info, 'daily': format_daily_activity_chart, 'hourly': format_hourly_distribution_chart}
        except ImportError:
            _STATS = {'time': lambda _: "📊 Нет данных", 'compare': lambda _: {'total':0,'avg':0,'rank':1}, 'trends': lambda: {}, 'daily': lambda *_: "📊 Нет", 'hourly': lambda _: "⏰ Нет"}
    return _STATS

def command_handler(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        try:
            message = update.message or (update.callback_query and update.callback_query.message)
            if not message:
                return
            return await func(update, context, message, *args, **kwargs)
        except Exception as e:
            logger.error(f"Ошибка в {func.__name__}: {e}")
            try:
                if update.message:
                    await update.message.reply_text("⚠️ Ошибка выполнения команды")
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

def format_num(num): return f"{num:,}".replace(",", " ")
def calc_level(cnt):
    if cnt <= 0: return {'level':1,'progress':0,'min':10,'max':15,'next':10}
    lvl = (cnt//10)+1; prog = (cnt%10)*10; dmg = int(10+(lvl-1)*0.5)
    return {'level':min(lvl,100),'progress':prog,'min':dmg,'max':dmg+5,'next':10-(cnt%10) if (cnt%10)<10 else 0}
def level_title(lvl):
    if lvl>=50: return ("👑 ЛЕГЕНДА","Мастер!")
    if lvl>=30: return ("💎 МАСТЕР","Отлично!")
    if lvl>=20: return ("⭐ ПРОФЕССИОНАЛ","Хорошо!")
    if lvl>=10: return ("🔥 АКТИВНЫЙ","Продолжай!")
    return ("👊 НОВИЧОК","Шлёпай больше!")
def get_reaction(): return random.choice(get_config()['MISHOK_REACTIONS'])

@command_handler
async def start(update, context, msg):
    text = f"""👋 *Привет, {update.effective_user.first_name}!*
Я — *Мишок Лысый* 👴✨
*Команды:*
/shlep — Шлёпнуть
/stats — Статистика  
/level — Уровень
/my_stats — Детально
/trends — Тренды
*Для чатов:* /chat_stats, /chat_top, /vote, /duel
*Начни:* /shlep"""
    kb = get_keyboard()['inline']() if update.effective_chat.type!="private" else None
    await msg.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)

@command_handler
async def shlep(update, context, msg):
    db, cache, user, chat = get_db(), get_cache(), update.effective_user, update.effective_chat
    _, cnt, _ = db['user'](user.id); lvl = calc_level(cnt)
    dmg = random.randint(lvl['min'], lvl['max'])
    total, cnt, max_dmg = db['add'](user.id, user.username or user.first_name, dmg, chat.id if chat.type!="private" else None)
    await cache.delete("global_stats"); await cache.delete(f"user_stats_{user.id}")
    if chat.type!="private": await cache.delete(f"chat_stats_{chat.id}")
    rec = f"\n🏆 *НОВЫЙ РЕКОРД!*\n" if dmg>max_dmg else ""
    lvl = calc_level(cnt); title, _ = level_title(lvl['level'])
    text = f"""{get_reaction()}{rec}💥 *Урон:* {dmg}
👤 *{user.first_name}*: {cnt} шлёпков
🎯 *Уровень {lvl['level']}* ({title})
📊 *До уровня:* {lvl['next']}
⚡ *Урон:* {lvl['min']}-{lvl['max']}
📈 *Всего:* {format_num(total)}"""
    kb = get_keyboard()['quick']() if chat.type!="private" else None
    await msg.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)

@command_handler 
async def stats(update, context, msg):
    db, cache = get_db(), get_cache()
    cached = await cache.get("global_stats")
    if cached: total, last, maxd, maxu, maxdt = cached
    else: total, last, maxd, maxu, maxdt = db['stats'](); await cache.set("global_stats", (total, last, maxd, maxu, maxdt))
    top = db['top'](10)
    text = f"""📊 *ГЛОБАЛЬНАЯ СТАТИСТИКА*
👑 *Рекорд:* {maxd} ({maxu or 'Нет'})
🔢 *Всего:* {format_num(total)}
⏰ *Последний:* {last.strftime('%d.%m.%Y %H:%M') if last else 'нет'}"""
    if top:
        text += "\n\n🏆 *ТОП:*\n"
        for i,(u,c) in enumerate(top[:5],1):
            lvl = calc_level(c); medal = ["🥇","🥈","🥉"][i-1] if i<=3 else ""
            text += f"\n{medal}{i}. {u or f'Игрок{i}'}\n   📊 {format_num(c)} | Ур. {lvl['level']}"
    await msg.reply_text(text, parse_mode=ParseMode.MARKDOWN)

@command_handler 
async def level(update, context, msg):
    db, cache, user = get_db(), get_cache(), update.effective_user
    cached = await cache.get(f"user_stats_{user.id}")
    if cached: u, cnt, last = cached
    else: u, cnt, last = db['user'](user.id); await cache.set(f"user_stats_{user.id}", (u, cnt, last))
    lvl = calc_level(cnt); title, advice = level_title(lvl['level'])
    bar = "█"*min(lvl['progress']//10,10) + "░"*(10-min(lvl['progress']//10,10))
    text = f"""🎯 *ТВОЙ УРОВЕНЬ*
👤 *{user.first_name}*
📊 *Шлёпков:* {format_num(cnt)}
🎯 *Уровень {lvl['level']}* ({title})
{bar} {lvl['progress']}%
⚡ *Урон:* {lvl['min']}-{lvl['max']}
🎯 *До уровня:* {lvl['next']}
💡 *{advice}*"""
    if last: text += f"\n⏰ *Последний:* {last.strftime('%d.%m.%Y %H:%M')}"
    await msg.reply_text(text, parse_mode=ParseMode.MARKDOWN)

@command_handler
async def my_stats(update, context, msg):
    user, stats = update.effective_user, get_stats_module()
    db = get_db(); _, cnt, last = db['user'](user.id); lvl = calc_level(cnt)
    text = f"""📈 *ТВОЯ СТАТИСТИКА*
👤 *{user.first_name}*
📊 *Шлёпков:* {format_num(cnt)}
🎯 *Уровень:* {lvl['level']}
⚡ *Урон:* {lvl['min']}-{lvl['max']}
{stats['time'](user.id)}
📊 *Сравнение:*
{stats['compare'](user.id).get('total',0)} игроков | Ранг {stats['compare'](user.id).get('rank',1)}
📅 *Активность:*
{stats['daily'](user.id, 7)}"""
    if last: text += f"\n⏰ *Последний:* {last.strftime('%d.%m.%Y %H:%M')}"
    await msg.reply_text(text, parse_mode=ParseMode.MARKDOWN)

@command_handler
async def trends(update, context, msg):
    trends = get_stats_module()['trends']()
    if not trends: await msg.reply_text("📊 Данные временно недоступны"); return
    text = f"""📊 *ГЛОБАЛЬНЫЕ ТРЕНДЫ*
👥 *Активных/24ч:* {trends.get('active_users_24h',0)}
👊 *Шлёпков/24ч:* {trends.get('shleps_24h',0)}
📈 *Среднее:* {trends.get('avg_per_user_24h',0)}
🔥 *Активных сегодня:* {trends.get('active_today',0)}
⏰ *Сейчас:* {trends.get('current_hour',0):02d}:00
👊 *Этот час:* {trends.get('shleps_this_hour',0)}"""
    await msg.reply_text(text, parse_mode=ParseMode.MARKDOWN)

@command_handler
async def detailed_stats(update, context, msg):
    user, stats = update.effective_user, get_stats_module()
    db = get_db(); _, cnt, _ = db['user'](user.id)
    text = f"""📊 *РАСШИРЕННАЯ СТАТИСТИКА*
👤 *{user.first_name}*
📊 *Шлёпков:* {format_num(cnt)}
{stats['time'](user.id)}
📅 *2 недели:*
{stats['daily'](user.id, 14)}
{stats['hourly'](user.id)}"""
    await msg.reply_text(text, parse_mode=ParseMode.MARKDOWN)

@command_handler
@chat_only
async def chat_stats(update, context, msg):
    db, cache, chat = get_db(), get_cache(), update.effective_chat
    cached = await cache.get(f"chat_stats_{chat.id}")
    if cached: cs = cached
    else: cs = db['chat'](chat.id); await cache.set(f"chat_stats_{chat.id}", cs)
    if not cs: text = "📊 *ЧАТ*\n\nЕщё не было шлёпков!\n/shlep чтобы начать!"
    else: text = f"""📊 *ЧАТ*
👥 *Участников:* {cs.get('total_users',0)}
👊 *Всего:* {format_num(cs.get('total_shleps',0))}
🏆 *Рекорд:* {cs.get('max_damage',0)} ({cs.get('max_damage_user','Нет')})"""
    await msg.reply_text(text, parse_mode=ParseMode.MARKDOWN)

@command_handler
@chat_only
async def chat_top(update, context, msg):
    db, chat = get_db(), update.effective_chat
    top = db['chat_top'](chat.id, 10)
    if not top: await msg.reply_text("🏆 *ЧАТ*\n\nПока пусто!"); return
    text = "🏆 *ТОП ЧАТА:*\n\n"
    for i,(u,c) in enumerate(top,1):
        lvl = calc_level(c); medal = ["🥇","🥈","🥉"][i-1] if i<=3 else ""
        text += f"{medal}{i}. {u}\n   📊 {format_num(c)} | Ур. {lvl['level']}\n\n"
    await msg.reply_text(text, parse_mode=ParseMode.MARKDOWN)

@command_handler
@chat_only
async def vote(update, context, msg):
    q = " ".join(context.args) if context.args else "Шлёпнуть Мишка?"
    await msg.reply_text(f"🗳️ *ГОЛОСОВАНИЕ*\n\n{q}\n\n5 минут!", parse_mode=ParseMode.MARKDOWN)

@command_handler
@chat_only
async def duel(update, context, msg):
    if context.args: text = f"⚔️ *ДУЭЛЬ!*\n\n{update.effective_user.first_name} вызывает {' '.join(context.args)}!\n\n5 минут, больше шлёпков - победа!"
    else: text = "⚔️ *ДУЭЛЬ*\n\n`/duel @имя` чтобы вызвать\n\n5 минут, больше шлёпков - победа!"
    await msg.reply_text(text, parse_mode=ParseMode.MARKDOWN)

@command_handler
@chat_only
async def roles(update, context, msg):
    text = """👑 *РОЛИ В ЧАТЕ*
• 👑 Король — топ-1 в чате
• 🎯 Меткий — макс. урон  
• ⚡ Спринтер — 10+ за 5 мин
• 💪 Силач — урон 40+
/chat_top — текущие лидеры"""
    await msg.reply_text(text, parse_mode=ParseMode.MARKDOWN)

@command_handler
async def help_cmd(update, context, msg):
    text = """🆘 *ПОМОЩЬ*
*Основные:*
/start /shlep /stats /level /my_stats /trends /mishok
*Для чатов:*
/chat_stats /chat_top /vote /duel /roles
*Сохранение прогресса!* 💾"""
    await msg.reply_text(text, parse_mode=ParseMode.MARKDOWN)

@command_handler
async def mishok(update, context, msg):
    await msg.reply_text(get_config()['MISHOK_INTRO'], parse_mode=ParseMode.MARKDOWN)

@command_handler
async def backup(update, context, msg):
    from config import ADMIN_ID
    if update.effective_user.id != ADMIN_ID: await msg.reply_text("⚠️ Только админ!"); return
    ok = get_db()['backup']()
    await msg.reply_text("✅ Бэкап создан!" if ok else "❌ Ошибка")

@command_handler
async def storage(update, context, msg):
    import os
    text = "📂 **Хранилище:**\n"
    for p,d in [("/root","Основная"),("/bothost","Корень"),("/bothost/storage","Постоянное"),("/bothost/storage/mishok_data.json","Файл данных")]:
        ex = os.path.exists(p); sz = os.path.getsize(p) if ex and os.path.isfile(p) else 0
        text += f"{'✅' if ex else '❌'} {d}: `{p}` ({sz/1024:.1f} KB)\n" if sz else f"{'✅' if ex else '❌'} {d}: `{p}`\n"
    await msg.reply_text(text, parse_mode="Markdown")

async def inline_handler(update, context, msg):
    query = update.callback_query
    if not query: return
    await query.answer()
    handlers = {"shlep_mishok":shlep,"stats_inline":stats,"level_inline":level,"mishok_info":mishok,"chat_stats":chat_stats,"chat_top":chat_top,"my_stats":my_stats,"trends":trends}
    if query.data in handlers: await handlers[query.data](update, context)
    elif query.data.startswith("quick_"): await quick_handler(update, context, query.data)
    else: await msg.reply_text("⚙️ В разработке")

async def quick_handler(update, context, data):
    query = update.callback_query
    if not query: return
    await query.answer()
    handlers = {"quick_shlep":shlep,"quick_stats":chat_stats,"quick_level":level,"quick_my_stats":my_stats,"quick_trends":trends}
    if data in handlers: await handlers[data](update, context)
    elif data=="quick_daily_top": await query.message.reply_text("📊 *ТОП ДНЯ*\n\nСобираем...")
    elif data in ["quick_vote","quick_duel"]: await query.message.reply_text(f"Используй /{data[6:]}")

@command_handler
async def button_handler(update, context, msg):
    if update.effective_chat.type!="private": return
    acts = {"👊 Шлёпнуть":shlep,"🎯 Уровень":level,"📊 Статистика":stats,"📈 Моя статистика":my_stats,"👴 О Мишке":mishok}
    if update.message.text in acts: await acts[update.message.text](update, context)

@command_handler
async def group_welcome(update, context, msg):
    if update.message.new_chat_members:
        for m in update.message.new_chat_members:
            if m.id==context.bot.id:
                await msg.reply_text("👴 *Мишок в чате!*\n\n/shlep — шлёпнуть\n/stats — статистика\n/level — уровень\n\n*Прогресс сохраняется!* 💾", parse_mode=ParseMode.MARKDOWN)

async def error_handler(update, context):
    logger.error(f"Ошибка: {context.error}", exc_info=True)

def main():
    cfg = get_config()
    if not cfg['BOT_TOKEN']: logger.error("❌ Нет токена!"); sys.exit(1)
    app = Application.builder().token(cfg['BOT_TOKEN']).build()
    cmds = [("start",start),("shlep",shlep),("stats",stats),("level",level),("my_stats",my_stats),("trends",trends),("detailed_stats",detailed_stats),("help",help_cmd),("mishok",mishok),("chat_stats",chat_stats),("chat_top",chat_top),("vote",vote),("duel",duel),("roles",roles),("backup",backup),("storage",storage)]
    for n,h in cmds: app.add_handler(CommandHandler(n,h))
    app.add_handler(CallbackQueryHandler(inline_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, group_welcome))
    app.add_error_handler(error_handler)
    logger.info("✅ Бот запущен (Bothost Storage)")
    print("\n"+"="*50+"\nМИШОК ЛЫСЫЙ ЗАПУЩЕН!\n"+"="*50)
    print(f"• Хранилище: /bothost/storage/mishok_data.json")
    print(f"• Проверка: /storage")
    print("="*50)
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__": main()
