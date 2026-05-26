import logging
import sqlite3
import re
import os
import atexit
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

# 🔐 Токен берётся из переменных окружения Bothost
TOKEN = os.getenv("TOKEN")  # Bothost сам подставит значение из панели
if not TOKEN:
    raise RuntimeError("❌ TOKEN не найден! Добавь переменную 'TOKEN' в панели Bothost")

ADMIN_ID = 919221270
CHAT_ID = -1001453944871

# Подключение к БД
conn = sqlite3.connect("cars.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS cars (name TEXT, price TEXT)")
conn.commit()

def close_db():
    if conn:
        conn.close()
atexit.register(close_db)

ADS = {
    "taxopark": {
        "keywords": [
            "аренда", "аренду", "нужна машина", "прокат",
            "бренд", "раскат", "сменщик", "взять машину", "частник"
        ],
        "text": (
            "🚖 Таксопарк 369: Авто + Поддержка 24/7\n"
            "✅ Машины готовы к выезду — начинай зарабатывать сразу!\n"
            "✅ Доступ в закрытый Клуб Водителей (2000+ участников)\n"
            "✅ Юр. консультации, розыгрыши и помощь в любых ситуациях\n"
            "🎁 Есть гостевой доступ — протестируй перед стартом!\n"
            "👉 Подключиться: @ElisavetaZ369\n"
            "━━━━━━━━━━━━\n"
        )
    },
    "work_official": {
        "keywords": [
            "работа в штате", "трудовой договор", "путевые", "трудоустройство"
        ],
        "text": (
            "🚖 Подключайся к Яндекс Такси всего за 5 минут!\n"
            "Разрешение перевозчика подтверждено!\n"
            "✅ Полностью легально: идет стаж, больничные и отпускные.\n"
            "✅ Удаленно: любой город, оформление через Госключ.\n"
            "💰 Условия: Комиссия от 6% (2% парк + 4% налог) или 8%. Моменталки — 1,5%.\n"
            "❗️ Взнос за оформление: 5000 ₽.\n"
            "Для регистрации нужны: ВУ, СТС, Паспорт, СНИЛС, ИНН и фото.\n"
            "📲 Писать: @AlexParts2020 \n"
            "━━━━━━━━━━━━\n"
        )
    },
    "park_connection": {
        "keywords": [
            "парк", "подключашка", "подключашку", "низкий процент"
        ],
        "text": (
            "Подключайся к Яндекс Такси всего за 5 минут! 🚕\n"
            "Комиссия парка от 1-2%, моментальный вывод 24/7 и круглосуточная поддержка.\n"
            "Пиши «Хочу подключиться» прямо сейчас: @zp_help. 🚀\n"
            "#ЯндексТакси #подключение #работа #такси #вывод #поддержка\n"
            "━━━━━━━━━━━━\n"
        )
    }
}

def get_ad_for_message(user_text):
    for ad_name, ad_data in ADS.items():
        for keyword in ad_data["keywords"]:
            pattern = r'(?i)\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, user_text):
                try:
                    cursor.execute("SELECT name, price FROM cars")
                    cars = cursor.fetchall()
                except sqlite3.Error as e:
                    logging.error(f"DB Error: {e}")
                    cars = []
                
                text = ad_data["text"]
                if cars:
                    text += "📋 Актуальные авто:\n"
                    for name, price in cars:
                        text += f"✅ {name} - {price}₽/сутки\n"
                return text
    return None

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    keyboard = [
        [InlineKeyboardButton("➕ Добавить авто", callback_data="add")],
        [InlineKeyboardButton("📢 В чат", callback_data="send")],
        [InlineKeyboardButton("🗑️ Очистить", callback_data="clear_confirm")],
    ]
    await update.message.reply_text(
        "🚗 PARK AGENTS АДМИН",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    
    if query.from_user.id != ADMIN_ID:
        await query.answer("⛔️ Доступ запрещен", show_alert=True)
        return

    await query.answer()
    action = query.data

    if action == "add":
        context.user_data["mode"] = "add_car"
        await query.edit_message_text('📝 Отправь: "Lada Vesta, 1500"')

    elif action == "send":
        try:
            cursor.execute("SELECT name, price FROM cars")
            cars = cursor.fetchall()
        except sqlite3.Error:
            cars = []
            
        text = ADS["taxopark"]["text"]
        if cars:
            text += "📋 Актуальные авто:\n"
            for name, price in cars:
                text += f"✅ {name} - {price}₽/сутки\n"
        await context.bot.send_message(chat_id=CHAT_ID, text=text)
        await query.edit_message_text("✅ В чат отправлено")

    elif action == "clear_confirm":
        keyboard = [
            [InlineKeyboardButton("⚠️ Да, удалить всё", callback_data="clear_execute")],
            [InlineKeyboardButton("❌ Отмена", callback_data="clear_cancel")]
        ]
        await query.edit_message_text(
            "❗️ Вы уверены? Это действие нельзя отменить.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif action == "clear_execute":
        cursor.execute("DELETE FROM cars")
        conn.commit()
        await query.edit_message_text("🗑️ База данных полностью очищена.")
    
    elif action == "clear_cancel":
        await query.edit_message_text("🆗 Операция отменена.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None:
        return
    
    text = getattr(update.message, "text", "") or ""
    text = text.strip()
    
    if not text:
        return

    if context.user_data.get("mode") == "add_car" and update.effective_user.id == ADMIN_ID:
        match = re.match(r"(.+?),\s*([\d\s]+)", text)
        if match:
            name, price = match.groups()
            try:
                cursor.execute("INSERT INTO cars (name, price) VALUES (?, ?)", (name.strip(), price.strip()))
                conn.commit()
                await update.message.reply_text(f"✅ Добавлено: {name} - {price}₽")
            except sqlite3.Error as e:
                await update.message.reply_text(f"❌ Ошибка БД: {e}")
        else:
            await update.message.reply_text("❌ Формат: Название, цена (например: Kia Rio, 1800)")
        context.user_data.pop("mode", None)
        return

    ad = get_ad_for_message(text)
    if ad:
        await update.message.reply_text(ad)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.error(msg="Exception while handling an update:", exc_info=context.error)

if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO
    )
    print("🚀 ParkAgents_bot готов к запуску на Bothost!")

    app = Application.builder().token(TOKEN).build()
    
    app.add_error_handler(error_handler)
    
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    app.run_polling()
