import logging
import re
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

TOKEN = '8407535870:AAEWI80Tq8Gr_F55V5S9PG6cuxCrnEeG3v8'
ADMIN_ID = 0
CHAT_ID = None

conn = sqlite3.connect('cars.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS cars (name TEXT, price TEXT)')
conn.commit()

PHRASES = ['аренда', 'нужна машина', 'парк', 'ищу парк', 'прокат', 'бренд', 'сменщик', 'процент парка']


def get_ad_text():
    cursor.execute('SELECT name, price FROM cars')
    cars = cursor.fetchall()
    text = (
        '🚕 Нужна аренда?\n'
        'Отличные условия, много авто, есть со страховкой.\n'
        '🎁 ПИТЕР369 — скидка 369₽ на первую неделю.\n'
        '📩 @ElisavetaZ369\n'
        '━━━━━━━━━━━━\n'
    )
    if cars:
        text += '📋 Актуальные авто:\n'
        for name, price in cars:
            text += f'✅ {name} - {price}₽/сутки\n'
        text += '\n'
    text += (
        '🚖 На своей машине?\n'
        '«ЗОЛОТОЙ ПАРК» — 8+ лет на рынке.\n'
        '✔️ Даже Без СМЗ и ИП\n'
        '📩 @AlexParts2020'
    )
    return text


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    keyboard = [
        [InlineKeyboardButton('➕ Добавить авто', callback_data='add')],
        [InlineKeyboardButton('📢 В чат', callback_data='send')],
        [InlineKeyboardButton('🗑️ Очистить', callback_data='clear')],
    ]
    await update.message.reply_text(
        '🚗 PARK AGENTS АДМИН',
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'add':
        await query.edit_message_text('📝 Отправь: "Lada Vesta, 1500"')
        context.user_data['mode'] = 'add_car'
    elif query.data == 'send':
        if CHAT_ID:
            await context.bot.send_message(chat_id=CHAT_ID, text=get_ad_text())
            await query.edit_message_text('✅ В чат отправлено')
        else:
            await query.edit_message_text('❌ Чат не найден. Сначала напиши что-то в группе')
    elif query.data == 'clear':
        cursor.execute('DELETE FROM cars')
        conn.commit()
        await query.edit_message_text('🗑️ База очищена')


async def handle_admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('mode') == 'add_car' and update.effective_user.id == ADMIN_ID:
        match = re.match(r'(.+?),\s*(\d+)', update.message.text.strip())
        if match:
            name, price = match.groups()
            cursor.execute('INSERT INTO cars (name, price) VALUES (?, ?)', (name, price))
            conn.commit()
            await update.message.reply_text(f'✅ Добавлено: {name} - {price}₽')
        else:
            await update.message.reply_text('❌ Формат: Название, цена')
        context.user_data.pop('mode', None)


async def taxi_trigger(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CHAT_ID
    if update.message.chat.type in ['group', 'supergroup'] and CHAT_ID is None:
        CHAT_ID = update.message.chat.id
        logging.info(f'CHAT_ID saved: {CHAT_ID}')

    text = (update.message.text or '').lower()
    if any(p in text for p in PHRASES):
        await update.message.reply_text(get_ad_text())


logging.basicConfig(level=logging.INFO)

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler('admin', admin_panel))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.TEXT & filters.User(user_id=ADMIN_ID), handle_admin_input))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, taxi_trigger))
app.run_polling()
