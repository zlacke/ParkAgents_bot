import logging
import sqlite3
import re
import os
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# 🔐 Токен из настроек сайта
TOKEN = os.getenv("TG_TOKEN")
if not TOKEN:
    print("❌ ОШИБКА: Переменная TG_TOKEN не найдена в настройках сайта!")
    # Не падаем сразу, чтобы увидеть ошибку в логе
    TOKEN = "" 

ADMIN_ID = 919221270
CHAT_ID = -1001453944871

# Подключение к БД
conn = sqlite3.connect("cars.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS cars (name TEXT, price TEXT)")
conn.commit()

ADS = {
    "taxopark": {
        "keywords": ["аренда", "арендую", "нужна машина", "прокат", "взять машину", "частник"],
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
        "keywords": ["работа в штате", "трудовой договор", "путевые", "трудоустройство"],
        "text": (
            "🚖 Подключайся к Яндекс Такси всего за 5 минут!\n"
            "Разрешение перевозчика подтверждено!\n"
            "✅ Полностью легально: идет стаж, больничные и отпускные.\n"
            "✅ Удаленно: любой город, оформление через Госключ.\n"
            "💰 Условия: Комиссия от 6% (2% парк + 4% налог) или 8%. Моменталки — 1,5%.\n"
            "❗️ Взнос за оформление: 5000 ₽.\n"
            "Для регистрации нужны: ВУ, СТС, Паспорт, СНИЛС, ИНН и фото.\n"
            "📲 Писать: @AlexParts2020\n"
            "━━━━━━━━━━━━\n"
        )
    },
    "park_connection": {
        "keywords": ["подключашка", "подключашку", "низкий процент"],
        "text": (
            "Подключайся к Яндекс Такси всего за 5 минут! 🚕\n"
            "Комиссия парка от 1-2%, моментальный вывод 24/7 и круглосуточная поддержка.\n"
            "Пиши «Хочу подключиться» прямо сейчас: @zp_help. 🚀\n"
            "#ЯндексТакси #подключение #работа #такси #вывод #поддержка\n"
            "━━━━━━━━━━━━\n"
        )
    },
    "waybill": {
        "keywords": ["путевой лист", "путевки", "путевой", "путевка", "эпл"],
        "text": (
            "📑 ЭЛЕКТРОННЫЙ ПУТЕВОЙ ЛИСТ НА РЕЙДЫ!\n"
            "Всего от 1199 рублей в месяц!\n"
            "Мы от Золотого Парка\n"
            "Писать сюда:\n"
            "@AlexParts2020\n"
            "━━━━━━━━━━━━\n"
        )
    }
}

AD_COOLDOWN = {}  # user_id -> timestamp of last ad sent
COOLDOWN_SECONDS = 3600  # 1 hour

def normalize_text(text: str) -> str:
    return " ".join((text or "").lower().split())

def has_keyword(text: str, keyword: str) -> bool:
    text = normalize_text(text)
    keyword = normalize_text(keyword)
    if not keyword: return False
    if " " in keyword: return keyword in text
    pattern = rf"(?<!\w){re.escape(keyword)}(?!\w)"
    return re.search(pattern, text) is not None

def get_ad_for_message(user_text):
    text = normalize_text(user_text)
    for ad_name, ad_data in ADS.items():
        for keyword in ad_data["keywords"]:
            if has_keyword(text, keyword):
                try:
                    cursor.execute("SELECT name, price FROM cars")
                    cars = cursor.fetchall()
                except: cars = []
                
                ad_text = ad_data["text"]
                if cars:
                    ad_text += "📋 Актуальные авто:\n"
                    for name, price in cars:
                        ad_text += f"✅ {name} - {price}₽/сутки\n"
                return ad_text
    return None

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    keyboard = [
        [InlineKeyboardButton("➕ Добавить авто", callback_data="add")],
        [InlineKeyboardButton("📢 В чат", callback_data="send")],
        [InlineKeyboardButton("🗑️ Очистить", callback_data="clear")],
    ]
    await update.message.reply_text("🚗 PARK AGENTS АДМИН", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query: return
    await query.answer()
    
    # 🔐 Проверка прав
    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔️ Доступ запрещен")
        return

    if query.data == "add":
        context.user_data["mode"] = "add_car"
        await query.edit_message_text('📝 Отправь: "Lada Vesta, 1500"')
    elif query.data == "send":
        try:
            cursor.execute("SELECT name, price FROM cars")
            cars = cursor.fetchall()
        except: cars = []
        text = ADS["taxopark"]["text"]
        if cars:
            text += "📋 Актуальные авто:\n"
            for name, price in cars: text += f"✅ {name} - {price}₽/сутки\n"
        await context.bot.send_message(chat_id=CHAT_ID, text=text)
        await query.edit_message_text("✅ В чат отправлено")
    elif query.data == "clear":
        cursor.execute("DELETE FROM cars")
        conn.commit()
        await query.edit_message_text("🗑️ База очищена")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 🔥 Проверка: есть ли сообщение и текст
    if not update.message or not update.message.text: return
    text = update.message.text.strip()

    # Режим добавления авто
    if context.user_data.get("mode") == "add_car" and update.effective_user.id == ADMIN_ID:
        match = re.match(r"(.+?),\s*(\d+)", text)
        if match:
            name, price = match.groups()
            try:
                cursor.execute("INSERT INTO cars (name, price) VALUES (?, ?)", (name.strip(), price.strip()))
                conn.commit()
                await update.message.reply_text(f"✅ Добавлено: {name} - {price}₽")
            except Exception as e:
                await update.message.reply_text(f"❌ Ошибка БД: {e}")
        else:
            await update.message.reply_text("❌ Формат: Название, цена")
        context.user_data.pop("mode", None)
        return

    # Поиск рекламы с таймаутом
    ad = get_ad_for_message(text)
    if ad:
        user_id = update.effective_user.id
        now = time.time()
        last_ad = AD_COOLDOWN.get(user_id, 0)
        if now - last_ad >= COOLDOWN_SECONDS:
            AD_COOLDOWN[user_id] = now
            await update.message.reply_text(ad)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.error(f"Update {update} caused error {context.error}")

# --- ЗАПУСК ---
if __name__ == "__main__":
    logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
    print("🚀 ParkAgents_bot запускается...")

    app = Application.builder().token(TOKEN).build()
    
    app.add_error_handler(error_handler)
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # 🔥 ГЛАВНОЕ: drop_pending_updates=True сбрасывает старые зависшие команды
    app.run_polling(drop_pending_updates=True)
