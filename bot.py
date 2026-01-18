import logging
import random
from datetime import datetime
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
from telegram.constants import ParseMode

from config import BOT_TOKEN, MISHOK_REACTIONS, MISHOK_INTRO, STICKERS
from database import init_db, add_shlep, get_stats, get_top_users
from keyboard import get_main_keyboard, get_inline_keyboard, get_group_welcome_keyboard

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация БД
init_db()

# ========== КОМАНДЫ ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /start"""
    user = update.effective_user
    chat = update.effective_chat
    
    welcome_text = f"""
👋 Привет, {user.first_name}!

Я бот с *Мишком Лысым* — самым терпеливым лысым персонажем в Telegram!
Ты можешь шлёпать его по лысине и слушать его недовольные комментарии.

В личных сообщениях используй кнопки ниже.
В группах — команду /shlep или кнопку под сообщением.
    """
    
    if chat.type == "private":
        await update.message.reply_text(
            welcome_text,
            reply_markup=get_main_keyboard(),
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
    
    # Добавляем в статистику
    total, user_count = add_shlep(user.id, user.username or user.first_name)
    
    # Выбираем случайную реакцию
    reaction = random.choice(MISHOK_REACTIONS)
    
    # Формируем сообщение
    message_text = f"""
{reaction}

*Шлёпок №{total}*
👤 {user.first_name}: {user_count} шлёпков
👴 Мишок: всё ещё лысый
    """
    
    # Отправляем сообщение
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
    
    # Отправляем стикер (если есть)
    sticker_key = random.choice(list(STICKERS.keys()))
    if STICKERS.get(sticker_key):
        try:
            if is_callback:
                await update.callback_query.message.reply_sticker(STICKERS[sticker_key])
            else:
                await update.message.reply_sticker(STICKERS[sticker_key])
        except:
            pass  # Если стикер не найден

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статистика (/stats)"""
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

🔢 Всего шлёпков: *{total_shleps}*
⏰ Последний шлёпок: *{last_time}*

🏆 *Топ шлёпателей:*
{top_text}

Мишок устал, но держится! 💪
    """
    
    await update.message.reply_text(
        stats_text,
        parse_mode=ParseMode.MARKDOWN
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кнопок в личных сообщениях"""
    text = update.message.text
    chat = update.effective_chat
    
    if chat.type != "private":
        return
    
    if text == "👊 Шлёпнуть Мишка":
        await process_shlep(update, context, is_callback=False)
    elif text == "📊 Статистика":
        await stats_command(update, context)
    elif text == "👴 О Мишке":
        await mishok_info(update, context)

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
/stats - статистика
/mishok - информация

Или нажми кнопку ниже для быстрого шлёпка!
                """
                await update.message.reply_text(
                    welcome_text,
                    reply_markup=get_group_welcome_keyboard(),
                    parse_mode=ParseMode.MARKDOWN
                )

async def help_in_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Помощь в группе (inline кнопка)"""
    query = update.callback_query
    await query.answer()
    
    help_text = """
🎮 *Доступные команды:*

/shlep - шлёпнуть Мишка по лысине
/stats - статистика шлёпков
/mishok - информация о Мишке

Мишок ждёт твоих шлёпков! 👊
    """
    
    await query.edit_message_text(
        help_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_inline_keyboard()
    )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ошибок"""
    logger.error(f"Update {update} caused error {context.error}")

# ========== ЗАПУСК ==========

def main():
    """Запуск бота"""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not found!")
        return
    
    # Создаём приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("shlep", shlep_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("mishok", mishok_info))
    
    # Inline-кнопки
    application.add_handler(CallbackQueryHandler(shlep_callback, pattern="^shlep_mishok$"))
    application.add_handler(CallbackQueryHandler(help_in_group, pattern="^help_in_group$"))
    
    # Сообщения
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, group_welcome))
    
    # Ошибки
    application.add_error_handler(error_handler)
    
    # Запуск
    logger.info("Бот запускается...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
