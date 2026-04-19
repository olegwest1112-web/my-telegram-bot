import logging
import json
import urllib.request
import urllib.parse
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)

TOKEN = "8702890215:AAEjWQXaM5yID_-IgN9yupXuCwRp-gtYJK8"
NP_API_KEY = "008df90224049cd5fd7f24fb82b891b9"
NP_API_URL = "https://api.novaposhta.ua/v2.0/json/"

logging.basicConfig(level=logging.INFO)

WAITING_WEIGHT = 1
WAITING_CITY = 2
WAITING_TRACK = 3
WAITING_BRANCH_CITY = 4

user_history = {}

def np_request(model, method, props):
    try:
        payload = json.dumps({
            "apiKey": NP_API_KEY,
            "modelName": model,
            "calledMethod": method,
            "methodProperties": props
        }).encode("utf-8")
        req = urllib.request.Request(
            NP_API_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        logging.error(f"NP API error: {e}")
        return None

def calculate_delivery(weight: float, city: str) -> dict:
    if weight <= 1:
        base = 55
    elif weight <= 2:
        base = 65
    elif weight <= 5:
        base = 75
    elif weight <= 10:
        base = 90
    elif weight <= 20:
        base = 110
    elif weight <= 30:
        base = 135
    else:
        base = 135 + (weight - 30) * 3

    big_cities = ["київ", "харків", "одеса", "дніпро", "львів", "запоріжжя"]
    city_lower = city.lower()
    if any(c in city_lower for c in big_cities):
        surcharge = 0
        city_type = "велике місто"
    else:
        surcharge = 10
        city_type = "мале місто/село"

    total = base + surcharge
    return {
        "weight": weight,
        "city": city,
        "city_type": city_type,
        "base": base,
        "surcharge": surcharge,
        "total": total
    }

def calculate_delivery_time(city: str) -> str:
    city_lower = city.lower()

    if "львів" in city_lower:
        return "🟢 В межах міста — сьогодні або завтра (1 день)"

    west = ["луцьк", "рівне", "тернопіль", "івано-франківськ", "ужгород", "мукачево", "хмельницький", "вінниця"]
    if any(c in city_lower for c in west):
        return "🟢 1-2 дні"

    center = ["київ", "житомир", "черкаси", "кропивницький", "полтава"]
    if any(c in city_lower for c in center):
        return "🟡 2-3 дні"

    east = ["харків", "дніпро", "запоріжжя", "одеса", "миколаїв", "херсон", "суми", "чернігів"]
    if any(c in city_lower for c in east):
        return "🟠 2-4 дні"

    return "🟡 2-3 дні (орієнтовно)"

def main_menu():
    keyboard = [
        [KeyboardButton("📦 Розрахувати доставку")],
        [KeyboardButton("🔍 Відстежити посилку")],
        [KeyboardButton("📍 Найближче відділення")],
        [KeyboardButton("📋 Історія розрахунків")],
        [KeyboardButton("ℹ️ Тарифи НП"), KeyboardButton("🗑 Очистити історію")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def cancel_menu():
    keyboard = [[KeyboardButton("❌ Скасувати")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привіт! Я допоможу з доставкою Новою Поштою.\n\nОбери дію:",
        reply_markup=main_menu()
    )
    return ConversationHandler.END

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "📦 Розрахувати доставку":
        await update.message.reply_text(
            "Введи вагу посилки в кг (наприклад: 2.5):",
            reply_markup=cancel_menu()
        )
        return WAITING_WEIGHT

    elif text == "🔍 Відстежити посилку":
        await update.message.reply_text(
            "Введи номер посилки (ТТН):",
            reply_markup=cancel_menu()
        )
        return WAITING_TRACK

    elif text == "📍 Найближче відділення":
        await update.message.reply_text(
            "Введи назву міста (наприклад: Київ):",
            reply_markup=cancel_menu()
        )
        return WAITING_BRANCH_CITY

    elif text == "📋 Історія розрахунків":
        uid = update.message.from_user.id
        history = user_history.get(uid, [])
        if history:
            lines = []
            for i, h in enumerate(history[-5:], 1):
                lines.append(f"{i}. {h['city']} | {h['weight']} кг → {h['total']} грн")
            await update.message.reply_text(
                "📋 Останні розрахунки:\n\n" + "\n".join(lines),
                reply_markup=main_menu()
            )
        else:
            await update.message.reply_text("Історія порожня.", reply_markup=main_menu())

    elif text == "ℹ️ Тарифи НП":
        await update.message.reply_text(
            "📦 Тарифи Нової Пошти (орієнтовні):\n\n"
            "до 1 кг — 55 грн\n"
            "до 2 кг — 65 грн\n"
            "до 5 кг — 75 грн\n"
            "до 10 кг — 90 грн\n"
            "до 20 кг — 110 грн\n"
            "до 30 кг — 135 грн\n"
            "понад 30 кг — 135 + 3 грн/кг\n\n"
            "➕ Надбавка для малих міст: +10 грн\n\n"
            "⚠️ Тарифи орієнтовні.",
            reply_markup=main_menu()
        )

    elif text == "🗑 Очистити історію":
        uid = update.message.from_user.id
        user_history[uid] = []
        await update.message.reply_text("✅ Історію очищено.", reply_markup=main_menu())

    return ConversationHandler.END

async def get_weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "❌ Скасувати":
        await update.message.reply_text("Скасовано.", reply_markup=main_menu())
        return ConversationHandler.END
    try:
        weight = float(text.replace(",", "."))
        if weight <= 0 or weight > 1000:
            raise ValueError()
        context.user_data["weight"] = weight
        await update.message.reply_text(
            f"✅ Вага: {weight} кг\n\nТепер введи місто доставки:",
            reply_markup=cancel_menu()
        )
        return WAITING_CITY
    except ValueError:
        await update.message.reply_text(
            "❌ Введи правильну вагу, наприклад: 2.5",
            reply_markup=cancel_menu()
        )
        return WAITING_WEIGHT

async def get_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "❌ Скасувати":
        await update.message.reply_text("Скасовано.", reply_markup=main_menu())
        return ConversationHandler.END

    city = text
    weight = context.user_data.get("weight", 1)
    result = calculate_delivery(weight, city)
    delivery_time = calculate_delivery_time(city)

    uid = update.message.from_user.id
    if uid not in user_history:
        user_history[uid] = []
    user_history[uid].append(result)

    await update.message.reply_text(
        f"📦 Розрахунок доставки:\n\n"
        f"🏙 Місто: {result['city']}\n"
        f"⚖️ Вага: {result['weight']} кг\n"
        f"📍 Тип: {result['city_type']}\n"
        f"💰 Базова вартість: {result['base']} грн\n"
        f"➕ Надбавка: {result['surcharge']} грн\n"
        f"✅ Разом: {result['total']} грн\n"
        f"🕐 Термін зі Львова: {delivery_time}\n\n"
        f"⚠️ Орієнтовні дані.",
        reply_markup=main_menu()
    )
    return ConversationHandler.END

async def track_package(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "❌ Скасувати":
        await update.message.reply_text("Скасовано.", reply_markup=main_menu())
        return ConversationHandler.END

    await update.message.reply_text("⏳ Шукаю інформацію про посилку...")

    data = np_request("TrackingDocument", "getStatusDocuments", {
        "Documents": [{"DocumentNumber": text, "Phone": ""}]
    })

    if data and data.get("success") and data.get("data"):
        doc = data["data"][0]
        status = doc.get("Status", "Невідомо")
        city_from = doc.get("CitySender", "—")
        city_to = doc.get("CityRecipient", "—")
        weight = doc.get("DocumentWeight", "—")
        scheduled = doc.get("ScheduledDeliveryDate", "—")

        await update.message.reply_text(
            f"🔍 Посилка: {text}\n\n"
            f"📊 Статус: {status}\n"
            f"📤 Відправник: {city_from}\n"
            f"📥 Отримувач: {city_to}\n"
            f"⚖️ Вага: {weight} кг\n"
            f"📅 Очікувана дата: {scheduled}",
            reply_markup=main_menu()
        )
    else:
        await update.message.reply_text(
            "❌ Посилку не знайдено. Перевір номер ТТН.",
            reply_markup=main_menu()
        )
    return ConversationHandler.END

async def find_branch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "❌ Скасувати":
        await update.message.reply_text("Скасовано.", reply_markup=main_menu())
        return ConversationHandler.END

    await update.message.reply_text("⏳ Шукаю відділення...")

    data = np_request("Address", "getWarehouses", {
        "CityName": text,
        "Limit": 5,
        "Page": 1
    })

    if data and data.get("success") and data.get("data"):
        branches = data["data"][:5]
        lines = []
        for b in branches:
            number = b.get("Number", "—")
            address = b.get("ShortAddress", "—")
            schedule = b.get("Schedule", {})
            mon = schedule.get("Monday", "—")
            lines.append(f"📍 Відділення №{number}\n🏠 {address}\n🕐 Пн: {mon}\n")

        await update.message.reply_text(
            f"📍 Відділення НП у місті {text}:\n\n" + "\n".join(lines),
            reply_markup=main_menu()
        )
    else:
        await update.message.reply_text(
            "❌ Відділення не знайдено. Перевір назву міста.",
            reply_markup=main_menu()
        )
    return ConversationHandler.END

def main():
    app = Application.builder().token(TOKEN).build()
    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)],
        states={
            WAITING_WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_weight)],
            WAITING_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_city)],
            WAITING_TRACK: [MessageHandler(filters.TEXT & ~filters.COMMAND, track_package)],
            WAITING_BRANCH_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, find_branch)],
        },
        fallbacks=[CommandHandler("start", start)],
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)
    print("Бот запущено!")
    app.run_polling()

if __name__ == "__main__":
    main()
