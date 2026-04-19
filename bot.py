import logging
import random
import urllib.request
import urllib.parse
import urllib.error
import json
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler, CallbackQueryHandler
)

TOKEN = "8702890215:AAEjWQXaM5yID_-IgN9yupXuCwRp-gtYJK8"

logging.basicConfig(level=logging.INFO)

WAITING_CITY = 1
WAITING_CALC = 2
WAITING_NOTE = 3

user_notes = {}

FACTS = [
    "🐙 У осьминога три сердца и голубая кровь.",
    "🍯 Мёд не портится — в египетских пирамидах находили мёд возрастом 3000 лет.",
    "🦷 Зубная эмаль — самое твёрдое вещество в теле человека.",
    "🌙 На Луне нет ветра, поэтому следы астронавтов останутся там миллионы лет.",
    "🐘 Слоны — единственные животные, которые не умеют прыгать.",
    "🧠 Мозг человека потребляет около 20% всей энергии тела.",
    "🦈 У акулы нет костей — только хрящи.",
    "🌍 Земле около 4,5 миллиарда лет.",
    "🐬 Дельфины спят с одним открытым глазом.",
    "🍌 Бананы слегка радиоактивны из-за содержания калия-40.",
]

def main_menu():
    keyboard = [
        [KeyboardButton("🌤 Погода"), KeyboardButton("💡 Случайный факт")],
        [KeyboardButton("🧮 Калькулятор"), KeyboardButton("📝 Заметка")],
        [KeyboardButton("📋 Мои заметки"), KeyboardButton("🗑 Удалить заметки")],
        [KeyboardButton("💱 Курс USDT"), KeyboardButton("ℹ️ О боте")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def cancel_menu():
    keyboard = [[KeyboardButton("❌ Отмена")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_binance_rate():
    try:
        url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
        payload = json.dumps({
            "asset": "USDT",
            "fiat": "UAH",
            "merchantCheck": False,
            "page": 1,
            "payTypes": [],
            "publisherType": None,
            "rows": 10,
            "tradeType": "BUY",
            "transAmount": "5000"
        }).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "*/*",
                "Accept-Language": "uk-UA,uk;q=0.9",
                "Origin": "https://p2p.binance.com",
                "Referer": "https://p2p.binance.com/",
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        ads = data.get("data", [])
        if not ads:
            return None
        real_ad = None
        for ad in ads:
            if not ad["adv"].get("isAdvert", False):
                real_ad = ad
                break
        if not real_ad:
            real_ad = ads[0]
        price = float(real_ad["adv"]["price"])
        nick = real_ad["advertiser"]["nickName"]
        min_amount = real_ad["adv"]["minSingleTransAmount"]
        max_amount = real_ad["adv"]["maxSingleTransAmount"]
        return {
            "price": price,
            "nick": nick,
            "min": min_amount,
            "max": max_amount
        }
    except Exception as e:
        logging.error(f"Binance error: {e}")
        return None

async def show_rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ Загружаю курс...")
    rate = get_binance_rate()
    refresh_btn = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Обновить", callback_data="refresh_rate")]
    ])
    if rate:
        text = (
            f"💱 Курс USDT/UAH (Binance P2P)\n\n"
            f"💵 Покупка от 5000₴\n"
            f"📈 Лучшая цена: {rate['price']} ₴\n"
            f"👤 Продавец: {rate['nick']}\n"
            f"📊 Лимиты: {rate['min']} — {rate['max']} ₴\n\n"
            f"💳 Оплата: Всі методи"
        )
    else:
        text = "❌ Не удалось получить курс. Попробуй позже."
    await msg.edit_text(text, reply_markup=refresh_btn)

async def refresh_rate_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Обновляю...")
    rate = get_binance_rate()
    refresh_btn = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Обновить", callback_data="refresh_rate")]
    ])
    if rate:
        text = (
            f"💱 Курс USDT/UAH (Binance P2P)\n\n"
            f"💵 Покупка от 5000₴\n"
            f"📈 Лучшая цена: {rate['price']} ₴\n"
            f"👤 Продавец: {rate['nick']}\n"
            f"📊 Лимиты: {rate['min']} — {rate['max']} ₴\n\n"
            f"💳 Оплата: Всі методи"
        )
    else:
        text = "❌ Не удалось получить курс. Попробуй позже."
    await query.edit_message_text(text, reply_markup=refresh_btn)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я твой бот-помощник.\nВыбери что тебя интересует:",
        reply_markup=main_menu()
    )
    return ConversationHandler.END

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "🌤 Погода":
        await update.message.reply_text("Введи название города:", reply_markup=cancel_menu())
        return WAITING_CITY
    elif text == "💡 Случайный факт":
        await update.message.reply_text(random.choice(FACTS), reply_markup=main_menu())
    elif text == "🧮 Калькулятор":
        await update.message.reply_text("Введи пример (например: 25 * 4):", reply_markup=cancel_menu())
        return WAITING_CALC
    elif text == "📝 Заметка":
        await update.message.reply_text("Напиши свою заметку:", reply_markup=cancel_menu())
        return WAITING_NOTE
    elif text == "📋 Мои заметки":
        uid = update.message.from_user.id
        notes = user_notes.get(uid, [])
        if notes:
            result = "\n".join([f"{i+1}. {n}" for i, n in enumerate(notes)])
            await update.message.reply_text(f"📋 Твои заметки:\n\n{result}", reply_markup=main_menu())
        else:
            await update.message.reply_text("У тебя пока нет заметок.", reply_markup=main_menu())
    elif text == "🗑 Удалить заметки":
        uid = update.message.from_user.id
        user_notes[uid] = []
        await update.message.reply_text("✅ Все заметки удалены.", reply_markup=main_menu())
    elif text == "💱 Курс USDT":
        await show_rate(update, context)
    elif text == "ℹ️ О боте":
        await update.message.reply_text(
            "🤖 Я простой бот-помощник!\n\n"
            "Умею:\n"
            "• Показывать погоду\n"
            "• Рассказывать факты\n"
            "• Считать примеры\n"
            "• Сохранять заметки\n"
            "• Показывать курс USDT/UAH\n\n"
            "Создан с помощью Claude 🧠",
            reply_markup=main_menu()
        )
    return ConversationHandler.END

async def get_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city = update.message.text.strip()
    if city == "❌ Отмена":
        await update.message.reply_text("Отменено.", reply_markup=main_menu())
        return ConversationHandler.END
    try:
        url = f"https://wttr.in/{urllib.parse.quote(city)}?format=j1"
        req = urllib.request.Request(url, headers={"User-Agent": "curl/7.68.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
        temp = data["current_condition"][0]["temp_C"]
        feels = data["current_condition"][0]["FeelsLikeC"]
        desc = data["current_condition"][0]["weatherDesc"][0]["value"]
        humidity = data["current_condition"][0]["humidity"]
        msg = (
            f"🌤 Погода в {city}:\n\n"
            f"🌡 Температура: {temp}°C\n"
            f"🤔 Ощущается как: {feels}°C\n"
            f"💧 Влажность: {humidity}%\n"
            f"📋 Описание: {desc}"
        )
    except Exception:
        msg = f"❌ Не удалось получить погоду для '{city}'."
    await update.message.reply_text(msg, reply_markup=main_menu())
    return ConversationHandler.END

async def calculate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    expr = update.message.text.strip()
    if expr == "❌ Отмена":
        await update.message.reply_text("Отменено.", reply_markup=main_menu())
        return ConversationHandler.END
    try:
        allowed = set("0123456789+-*/(). ")
        if not all(c in allowed for c in expr):
            raise ValueError()
        result = eval(expr)
        await update.message.reply_text(f"🧮 {expr} = {result}", reply_markup=main_menu())
    except Exception:
        await update.message.reply_text("❌ Не могу посчитать. Попробуй: 25 * 4", reply_markup=main_menu())
    return ConversationHandler.END

async def save_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    note = update.message.text.strip()
    if note == "❌ Отмена":
        await update.message.reply_text("Отменено.", reply_markup=main_menu())
        return ConversationHandler.END
    uid = update.message.from_user.id
    if uid not in user_notes:
        user_notes[uid] = []
    user_notes[uid].append(note)
    await update.message.reply_text("✅ Заметка сохранена!", reply_markup=main_menu())
    return ConversationHandler.END

def main():
    app = Application.builder().token(TOKEN).build()
    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)],
        states={
            WAITING_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_weather)],
            WAITING_CALC: [MessageHandler(filters.TEXT & ~filters.COMMAND, calculate)],
            WAITING_NOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_note)],
        },
        fallbacks=[CommandHandler("start", start)],
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(refresh_rate_callback, pattern="refresh_rate"))
    print("Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()

