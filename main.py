import logging, sqlite3, re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

TOKEN = '8407535870:AAEWI80Tq8Gr_F55V5S9PG6cuxCrnEeG3v8'
ADMIN_ID = 0  # ЗАМЕНИ на ID менеджера (@userinfobot)
CHAT_ID = None  # Автоопределение такси-чата

# База
conn = sqlite3.connect('cars.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS cars (name TEXT, price TEXT)')
conn.commit()

def get_ad_text():
    cursor.execute("SELECT name, price FROM cars")
    cars = cursor.fetchall()
    text = "🚗 <b>АРЕНДА МАШИН СПБ 24/7!</b>\n\n"
    if cars:
        for name, price in cars:
            text += f"✅ {name} - {price}₽/сутки\n"
    else:
        text += "📞 +7 (999) 123-45-67 (ПОДКЛЮЧИ МАШИНЫ!)\n"
    text += "\n📞 +7 (999) 123-45-67 | /arenda\n"
    return text

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    keyboard = [
        [InlineKeyboardButton("➕ Добавить авто", callback_data='add_car')],
        [InlineKeyboardButton("📢 В такси-чат", callback_data='send_chat')],
        [InlineKeyboardButton("📝 Текст рекламы", callback_data='edit_ad')],
        [InlineKeyboardButton("📊 Статистика", callback_data='stats')]
    ]
    await update.message.reply_text('🚗 <b>АДМИН-ПАНЕЛЬ ТАКСИ</b>', 
                                   parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'add_car':
        await query.edit_message_text('📝 Отправь: "Toyota Camry, 2000₽"')
        context.user_data['mode'] = 'add_car'
    elif query.data == 'send_chat':
        if CHAT_ID:
            ad = get_ad_text()
            await context.bot.send_message(CHAT_ID, ad, parse_mode='HTML')
            await query.edit_message_text('✅ Реклама ушла в такси-чат!')
        else:
            await query.edit_message_text('❌ Добавь бота в такси-чат сначала!')

async def handle_admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('mode') == 'add_car' and update.effective_user.id == ADMIN_ID:
        match = re.match(r'(.+?),\s*(\d+)', update.message.text.strip())
        if match:
            name, price = match.groups()
            cursor.execute("INSERT INTO cars (name, price) VALUES (?, ?)", (name, price))
            conn.commit()
            await update.message.reply_text(f'✅ Добавлено: {name} - {price}₽')
        context.user_data.pop('mode', None)

async def taxi_trigger(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CHAT_ID
    if CHAT_ID is None and update.message.chat.type in ['group', 'supergroup']:
        CHAT_ID = update.message.chat.id
        logging.info(f'Такси-чат найден: {CHAT_ID}')
    
    text = update.message.text.lower() if update.message.text else ''
    phrases = ['аренда', 'нужна машина', 'ищу машину', 'арендовать', 'ищу тачку']
    if any(p in text for p in phrases):
        ad = get_ad_text()
        await update.message.reply_text(ad, parse_mode='HTML')

logging.basicConfig(level=logging.INFO)
print("🚀 Такси-бот запущен!")

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler('admin', admin_panel))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.TEXT & filters.User(user_id=ADMIN_ID), handle_admin_input))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, taxi_trigger))
app.run_polling()