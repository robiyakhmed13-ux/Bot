"""
HAMYON - Telegram Bot (Python)
Smart Finance Tracker - ALL FEATURES FREE
=========================================
Features:
- Text parsing (natural language)
- Voice message transcription (OpenAI Whisper)
- Receipt/image OCR (GPT-4 Vision)
- Category selection flow
- Budget limits & alerts
- Daily/weekly/monthly reports
- Mini App deep integration
- Multi-language support (uz/ru/en)
- Export to CSV/Excel
"""

import os
import re
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple, List
from dataclasses import dataclass
from enum import Enum
import io

# Telegram
from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    WebAppInfo,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InputFile
)
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# Supabase
from supabase import create_client, Client

# OpenAI (for voice & vision)
import openai

# For CSV export
import csv

# Load environment
from dotenv import load_dotenv
load_dotenv()

# ============================================
# CONFIGURATION
# ============================================
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://your-app.vercel.app")

if not BOT_TOKEN:
    raise ValueError("Missing TELEGRAM_BOT_TOKEN")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_ANON_KEY")

# Initialize clients
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============================================
# TYPES & ENUMS
# ============================================
class TxType(Enum):
    EXPENSE = "expense"
    INCOME = "income"
    DEBT = "debt"

class TxSource(Enum):
    TEXT = "text"
    VOICE = "voice"
    RECEIPT = "receipt"
    MANUAL = "manual"
    BOT = "bot"

@dataclass
class Category:
    id: str
    name_uz: str
    name_ru: str
    name_en: str
    emoji: str
    keywords: List[str]
    tx_type: TxType

@dataclass
class PendingTransaction:
    category_id: str
    tx_type: TxType
    awaiting: str  # "amount" or "description"

# ============================================
# CATEGORIES (45+ categories)
# ============================================
CATEGORIES: Dict[str, Category] = {
    # === EXPENSE CATEGORIES ===
    "food": Category("food", "Oziq-ovqat", "Продукты", "Food", "🍕", 
                     ["food", "oziq", "ovqat", "grocery", "magazin", "продукты", "еда"], TxType.EXPENSE),
    "restaurants": Category("restaurants", "Restoranlar", "Рестораны", "Restaurants", "🍽️",
                           ["restaurant", "restoran", "cafe", "kafe", "ресторан", "кафе"], TxType.EXPENSE),
    "coffee": Category("coffee", "Kofe", "Кофе", "Coffee", "☕",
                      ["coffee", "kofe", "кофе", "starbucks", "espresso"], TxType.EXPENSE),
    "taxi": Category("taxi", "Taksi", "Такси", "Taxi", "🚕",
                    ["taxi", "taksi", "yandex", "uber", "такси", "bolt"], TxType.EXPENSE),
    "fuel": Category("fuel", "Benzin", "Бензин", "Fuel", "⛽",
                    ["fuel", "benzin", "gas", "petrol", "бензин", "топливо", "yoqilgi"], TxType.EXPENSE),
    "transport": Category("transport", "Transport", "Транспорт", "Transport", "🚌",
                         ["transport", "bus", "avtobus", "metro", "транспорт", "автобус"], TxType.EXPENSE),
    "bills": Category("bills", "Kommunal", "Коммунальные", "Bills", "💡",
                     ["bills", "kommunal", "utility", "electric", "gas", "water", "коммунальные", "свет", "газ"], TxType.EXPENSE),
    "rent": Category("rent", "Ijara", "Аренда", "Rent", "🏠",
                    ["rent", "ijara", "kvartira", "аренда", "квартира"], TxType.EXPENSE),
    "shopping": Category("shopping", "Xaridlar", "Покупки", "Shopping", "🛍️",
                        ["shopping", "xarid", "buy", "purchase", "покупки", "шоппинг"], TxType.EXPENSE),
    "clothing": Category("clothing", "Kiyim", "Одежда", "Clothing", "👕",
                        ["clothing", "kiyim", "clothes", "shirt", "pants", "одежда", "футболка"], TxType.EXPENSE),
    "health": Category("health", "Salomatlik", "Здоровье", "Health", "💊",
                      ["health", "salomatlik", "medicine", "doctor", "hospital", "pharmacy", "здоровье", "аптека", "врач"], TxType.EXPENSE),
    "beauty": Category("beauty", "Go'zallik", "Красота", "Beauty", "💄",
                      ["beauty", "salon", "haircut", "sartarosh", "красота", "салон"], TxType.EXPENSE),
    "education": Category("education", "Ta'lim", "Образование", "Education", "📚",
                         ["education", "talim", "course", "kurs", "book", "kitob", "образование", "курс", "книга"], TxType.EXPENSE),
    "entertainment": Category("entertainment", "Ko'ngilochar", "Развлечения", "Entertainment", "🎬",
                             ["entertainment", "movie", "kino", "cinema", "game", "развлечения", "кино"], TxType.EXPENSE),
    "sports": Category("sports", "Sport", "Спорт", "Sports", "🏃",
                      ["sports", "sport", "gym", "fitness", "спорт", "фитнес", "зал"], TxType.EXPENSE),
    "travel": Category("travel", "Sayohat", "Путешествия", "Travel", "✈️",
                      ["travel", "sayohat", "trip", "vacation", "путешествие", "отпуск"], TxType.EXPENSE),
    "electronics": Category("electronics", "Elektronika", "Электроника", "Electronics", "📱",
                           ["electronics", "phone", "telefon", "laptop", "computer", "электроника", "телефон"], TxType.EXPENSE),
    "gifts": Category("gifts", "Sovg'alar", "Подарки", "Gifts", "🎁",
                     ["gift", "sovga", "present", "подарок"], TxType.EXPENSE),
    "pets": Category("pets", "Uy hayvonlari", "Питомцы", "Pets", "🐕",
                    ["pet", "dog", "cat", "mushuk", "it", "питомец", "собака", "кошка"], TxType.EXPENSE),
    "kids": Category("kids", "Bolalar", "Дети", "Kids", "👶",
                    ["kids", "children", "bolalar", "дети", "ребенок"], TxType.EXPENSE),
    "home": Category("home", "Uy jihozlari", "Для дома", "Home", "🏡",
                    ["home", "furniture", "mebel", "uy", "дом", "мебель"], TxType.EXPENSE),
    "internet": Category("internet", "Internet", "Интернет", "Internet", "🌐",
                        ["internet", "wifi", "data", "интернет"], TxType.EXPENSE),
    "phone_bill": Category("phone_bill", "Telefon", "Телефон", "Phone", "📞",
                          ["phone", "mobile", "telefon", "beeline", "ucell", "телефон", "связь"], TxType.EXPENSE),
    "insurance": Category("insurance", "Sug'urta", "Страховка", "Insurance", "🛡️",
                         ["insurance", "sugurta", "страховка"], TxType.EXPENSE),
    "taxes": Category("taxes", "Soliqlar", "Налоги", "Taxes", "📋",
                     ["tax", "soliq", "налог"], TxType.EXPENSE),
    "charity": Category("charity", "Xayriya", "Благотворительность", "Charity", "❤️",
                       ["charity", "xayriya", "sadaqa", "donation", "благотворительность"], TxType.EXPENSE),
    "subscriptions": Category("subscriptions", "Obunalar", "Подписки", "Subscriptions", "📺",
                             ["subscription", "netflix", "spotify", "youtube", "подписка", "obuna"], TxType.EXPENSE),
    "other_expense": Category("other_expense", "Boshqa", "Другое", "Other", "📦",
                             ["other", "boshqa", "другое"], TxType.EXPENSE),
    
    # === INCOME CATEGORIES ===
    "salary": Category("salary", "Oylik maosh", "Зарплата", "Salary", "💰",
                      ["salary", "oylik", "maosh", "ish haqi", "зарплата"], TxType.INCOME),
    "freelance": Category("freelance", "Frilanser", "Фриланс", "Freelance", "💻",
                         ["freelance", "frilanser", "фриланс", "project", "loyiha"], TxType.INCOME),
    "business": Category("business", "Biznes", "Бизнес", "Business", "🏢",
                        ["business", "biznes", "бизнес", "savdo"], TxType.INCOME),
    "investments": Category("investments", "Investitsiya", "Инвестиции", "Investments", "📈",
                           ["investment", "investitsiya", "dividend", "инвестиции", "дивиденды"], TxType.INCOME),
    "bonus": Category("bonus", "Bonus", "Бонус", "Bonus", "🎉",
                     ["bonus", "award", "mukofot", "бонус", "премия"], TxType.INCOME),
    "gift_income": Category("gift_income", "Sovg'a", "Подарок", "Gift", "🎁",
                           ["gift", "sovga", "present", "подарок"], TxType.INCOME),
    "rental_income": Category("rental_income", "Ijara daromadi", "Доход от аренды", "Rental", "🏠",
                             ["rental", "ijara", "rent income", "аренда"], TxType.INCOME),
    "refund": Category("refund", "Qaytarish", "Возврат", "Refund", "↩️",
                      ["refund", "qaytarish", "return", "возврат"], TxType.INCOME),
    "other_income": Category("other_income", "Boshqa daromad", "Другой доход", "Other", "💵",
                            ["income", "daromad", "доход"], TxType.INCOME),
    
    # === DEBT CATEGORIES ===
    "borrowed": Category("borrowed", "Qarz oldim", "Взял в долг", "Borrowed", "🤝",
                        ["borrowed", "qarz oldim", "занял", "взял в долг"], TxType.DEBT),
    "lent": Category("lent", "Qarz berdim", "Дал в долг", "Lent", "💸",
                    ["lent", "qarz berdim", "дал в долг", "одолжил"], TxType.DEBT),
    "debt_payment": Category("debt_payment", "Qarz to'lovi", "Платёж по долгу", "Debt Payment", "🏦",
                            ["debt payment", "qarz tolovi", "платёж", "погашение"], TxType.DEBT),
}

# User states
user_pending: Dict[int, PendingTransaction] = {}
user_language: Dict[int, str] = {}  # Default: "uz"

# ============================================
# TRANSLATIONS
# ============================================
TRANSLATIONS = {
    "uz": {
        "welcome": "👋 Salom! Hamyon botga xush kelibsiz!\n\n✅ Quyidagi usullardan foydalaning:\n1️⃣ Kategoriya tanlang → Summa yuboring\n2️⃣ Matn yozing: \"Taksi 30000\"\n3️⃣ Ovozli xabar yuboring\n4️⃣ Chek rasmini yuboring",
        "balance": "💰 Balans",
        "today": "📅 Bugun",
        "expenses": "↘️ Xarajatlar",
        "income": "↗️ Daromad",
        "transactions": "🧾 Tranzaksiyalar",
        "select_expense": "🧾 Xarajat kategoriyasini tanlang:",
        "select_income": "💰 Daromad kategoriyasini tanlang:",
        "select_debt": "💳 Qarz turini tanlang:",
        "enter_amount": "✅ {emoji} {name}\n\nEndi summani yuboring.\nMasalan: 500000 yoki 500k",
        "saved": "✅ Saqlandi!\n\n{emoji} {name}\n{type_emoji} {amount}\n💰 Balans: {balance}",
        "cant_parse": "❌ Summani aniqlab bo'lmadi.\nMasalan: 'Taksi 30000' yoki avval kategoriya tanlang.",
        "voice_processing": "🎤 Ovozli xabar qayta ishlanmoqda...",
        "receipt_processing": "🧾 Chek tahlil qilinmoqda...",
        "no_openai": "⚠️ OpenAI API sozlanmagan. Matn yozing yoki kategoriya tanlang.",
        "weekly_report": "📊 Haftalik hisobot",
        "monthly_report": "📊 Oylik hisobot",
        "limit_warning": "⚠️ Ogohlantirish!\n\n{emoji} {name} limiti:\n💰 Limit: {limit}\n💸 Sarflangan: {spent}\n📊 {percent}% ishlatilgan",
        "limit_exceeded": "🚨 LIMIT OSHDI!\n\n{emoji} {name}:\n💰 Limit: {limit}\n💸 Sarflangan: {spent}\n📊 {percent}% - limit oshdi!",
        "export_ready": "📥 Eksport tayyor!",
        "settings": "⚙️ Sozlamalar",
        "language": "🌐 Til",
        "open_app": "📱 Ilovani ochish",
        "add_expense": "➖ Xarajat",
        "add_income": "➕ Daromad",
        "add_debt": "💳 Qarz",
        "reports": "📊 Hisobotlar",
        "export": "📥 Eksport",
        "help": "❓ Yordam",
    },
    "ru": {
        "welcome": "👋 Привет! Добро пожаловать в Hamyon!\n\n✅ Используйте:\n1️⃣ Выберите категорию → Отправьте сумму\n2️⃣ Напишите: \"Такси 30000\"\n3️⃣ Отправьте голосовое сообщение\n4️⃣ Отправьте фото чека",
        "balance": "💰 Баланс",
        "today": "📅 Сегодня",
        "expenses": "↘️ Расходы",
        "income": "↗️ Доходы",
        "transactions": "🧾 Транзакции",
        "select_expense": "🧾 Выберите категорию расхода:",
        "select_income": "💰 Выберите категорию дохода:",
        "select_debt": "💳 Выберите тип долга:",
        "enter_amount": "✅ {emoji} {name}\n\nТеперь отправьте сумму.\nНапример: 500000 или 500k",
        "saved": "✅ Сохранено!\n\n{emoji} {name}\n{type_emoji} {amount}\n💰 Баланс: {balance}",
        "cant_parse": "❌ Не удалось определить сумму.\nНапример: 'Такси 30000' или сначала выберите категорию.",
        "voice_processing": "🎤 Обработка голосового сообщения...",
        "receipt_processing": "🧾 Анализ чека...",
        "no_openai": "⚠️ OpenAI API не настроен. Напишите текст или выберите категорию.",
        "weekly_report": "📊 Недельный отчёт",
        "monthly_report": "📊 Месячный отчёт",
        "limit_warning": "⚠️ Предупреждение!\n\n{emoji} {name} лимит:\n💰 Лимит: {limit}\n💸 Потрачено: {spent}\n📊 {percent}% использовано",
        "limit_exceeded": "🚨 ЛИМИТ ПРЕВЫШЕН!\n\n{emoji} {name}:\n💰 Лимит: {limit}\n💸 Потрачено: {spent}\n📊 {percent}% - лимит превышен!",
        "export_ready": "📥 Экспорт готов!",
        "settings": "⚙️ Настройки",
        "language": "🌐 Язык",
        "open_app": "📱 Открыть приложение",
        "add_expense": "➖ Расход",
        "add_income": "➕ Доход",
        "add_debt": "💳 Долг",
        "reports": "📊 Отчёты",
        "export": "📥 Экспорт",
        "help": "❓ Помощь",
    },
    "en": {
        "welcome": "👋 Hello! Welcome to Hamyon!\n\n✅ Use these methods:\n1️⃣ Select category → Send amount\n2️⃣ Write: \"Taxi 30000\"\n3️⃣ Send voice message\n4️⃣ Send receipt photo",
        "balance": "💰 Balance",
        "today": "📅 Today",
        "expenses": "↘️ Expenses",
        "income": "↗️ Income",
        "transactions": "🧾 Transactions",
        "select_expense": "🧾 Select expense category:",
        "select_income": "💰 Select income category:",
        "select_debt": "💳 Select debt type:",
        "enter_amount": "✅ {emoji} {name}\n\nNow send the amount.\nExample: 500000 or 500k",
        "saved": "✅ Saved!\n\n{emoji} {name}\n{type_emoji} {amount}\n💰 Balance: {balance}",
        "cant_parse": "❌ Couldn't parse amount.\nExample: 'Taxi 30000' or select a category first.",
        "voice_processing": "🎤 Processing voice message...",
        "receipt_processing": "🧾 Analyzing receipt...",
        "no_openai": "⚠️ OpenAI API not configured. Send text or select a category.",
        "weekly_report": "📊 Weekly Report",
        "monthly_report": "📊 Monthly Report",
        "limit_warning": "⚠️ Warning!\n\n{emoji} {name} limit:\n💰 Limit: {limit}\n💸 Spent: {spent}\n📊 {percent}% used",
        "limit_exceeded": "🚨 LIMIT EXCEEDED!\n\n{emoji} {name}:\n💰 Limit: {limit}\n💸 Spent: {spent}\n📊 {percent}% - exceeded!",
        "export_ready": "📥 Export ready!",
        "settings": "⚙️ Settings",
        "language": "🌐 Language",
        "open_app": "📱 Open App",
        "add_expense": "➖ Expense",
        "add_income": "➕ Income",
        "add_debt": "💳 Debt",
        "reports": "📊 Reports",
        "export": "📥 Export",
        "help": "❓ Help",
    }
}

def t(user_id: int, key: str) -> str:
    """Get translation for user"""
    lang = user_language.get(user_id, "uz")
    return TRANSLATIONS.get(lang, TRANSLATIONS["uz"]).get(key, key)

def get_cat_name(cat: Category, user_id: int) -> str:
    """Get category name in user's language"""
    lang = user_language.get(user_id, "uz")
    if lang == "ru":
        return cat.name_ru
    elif lang == "en":
        return cat.name_en
    return cat.name_uz

# ============================================
# DATABASE HELPERS
# ============================================
async def get_or_create_user(telegram_id: int, first_name: str, last_name: str = "") -> Dict:
    """Get or create user in database"""
    try:
        result = supabase.table("users").select("*").eq("telegram_id", telegram_id).maybe_single().execute()
        if result.data:
            return result.data
        
        name = f"{first_name} {last_name}".strip()
        new_user = supabase.table("users").insert({
            "telegram_id": telegram_id,
            "name": name,
            "balance": 0
        }).execute()
        return new_user.data[0] if new_user.data else {"telegram_id": telegram_id, "name": name, "balance": 0}
    except Exception as e:
        logger.error(f"get_or_create_user error: {e}")
        return {"telegram_id": telegram_id, "name": first_name, "balance": 0}

async def get_balance(telegram_id: int) -> int:
    """Get user balance"""
    try:
        result = supabase.table("users").select("balance").eq("telegram_id", telegram_id).single().execute()
        return int(result.data.get("balance", 0)) if result.data else 0
    except Exception as e:
        logger.error(f"get_balance error: {e}")
        return 0

async def save_transaction(telegram_id: int, description: str, amount: int, category_id: str, source: str) -> bool:
    """Save transaction to database"""
    try:
        supabase.table("transactions").insert({
            "user_telegram_id": telegram_id,
            "description": description,
            "amount": amount,
            "category_id": category_id,
            "source": source
        }).execute()
        
        # Update balance via RPC or direct update
        try:
            supabase.rpc("update_balance", {"p_telegram_id": telegram_id, "p_amount": amount}).execute()
        except:
            # Fallback: direct update
            current = await get_balance(telegram_id)
            supabase.table("users").update({"balance": current + amount}).eq("telegram_id", telegram_id).execute()
        
        return True
    except Exception as e:
        logger.error(f"save_transaction error: {e}")
        return False

async def get_today_stats(telegram_id: int) -> Dict:
    """Get today's statistics"""
    try:
        result = supabase.rpc("get_today_stats", {"p_telegram_id": telegram_id}).execute()
        if result.data and len(result.data) > 0:
            row = result.data[0]
            return {
                "expenses": abs(int(row.get("total_expenses", 0))),
                "income": int(row.get("total_income", 0)),
                "count": int(row.get("transaction_count", 0))
            }
    except Exception as e:
        logger.error(f"get_today_stats error: {e}")
    return {"expenses": 0, "income": 0, "count": 0}

async def get_period_stats(telegram_id: int, days: int) -> Dict:
    """Get statistics for period"""
    try:
        start_date = (datetime.now() - timedelta(days=days)).isoformat()
        result = supabase.table("transactions")\
            .select("amount, category_id")\
            .eq("user_telegram_id", telegram_id)\
            .gte("created_at", start_date)\
            .execute()
        
        expenses = 0
        income = 0
        by_category: Dict[str, int] = {}
        
        for tx in (result.data or []):
            amt = int(tx.get("amount", 0))
            cat_id = tx.get("category_id", "other")
            
            if amt < 0:
                expenses += abs(amt)
                by_category[cat_id] = by_category.get(cat_id, 0) + abs(amt)
            else:
                income += amt
        
        return {
            "expenses": expenses,
            "income": income,
            "count": len(result.data or []),
            "by_category": by_category
        }
    except Exception as e:
        logger.error(f"get_period_stats error: {e}")
        return {"expenses": 0, "income": 0, "count": 0, "by_category": {}}

async def get_category_limit(telegram_id: int, category_id: str) -> Optional[int]:
    """Get limit for category"""
    try:
        result = supabase.table("limits")\
            .select("limit_amount")\
            .eq("user_telegram_id", telegram_id)\
            .eq("category_id", category_id)\
            .maybe_single()\
            .execute()
        return int(result.data["limit_amount"]) if result.data else None
    except:
        return None

async def get_month_spent(telegram_id: int, category_id: str) -> int:
    """Get amount spent this month for category"""
    try:
        start_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0).isoformat()
        result = supabase.table("transactions")\
            .select("amount")\
            .eq("user_telegram_id", telegram_id)\
            .eq("category_id", category_id)\
            .lt("amount", 0)\
            .gte("created_at", start_of_month)\
            .execute()
        
        return sum(abs(int(tx["amount"])) for tx in (result.data or []))
    except:
        return 0

async def export_transactions(telegram_id: int, days: int = 30) -> str:
    """Export transactions to CSV"""
    try:
        start_date = (datetime.now() - timedelta(days=days)).isoformat()
        result = supabase.table("transactions")\
            .select("*")\
            .eq("user_telegram_id", telegram_id)\
            .gte("created_at", start_date)\
            .order("created_at", desc=True)\
            .execute()
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Date", "Description", "Amount", "Category", "Source"])
        
        for tx in (result.data or []):
            cat = CATEGORIES.get(tx.get("category_id", ""), None)
            cat_name = cat.name_uz if cat else tx.get("category_id", "")
            writer.writerow([
                tx.get("created_at", "")[:10],
                tx.get("description", ""),
                tx.get("amount", 0),
                cat_name,
                tx.get("source", "")
            ])
        
        return output.getvalue()
    except Exception as e:
        logger.error(f"export_transactions error: {e}")
        return ""

# ============================================
# PARSING HELPERS
# ============================================
def parse_amount(text: str) -> Optional[int]:
    """Parse amount from text (supports k, m, ming, million)"""
    text = text.lower().strip()
    
    # Million patterns
    million_match = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:mln|million|миллион|млн|m(?!ing))\b', text, re.IGNORECASE)
    if million_match:
        return int(float(million_match.group(1).replace(",", ".")) * 1_000_000)
    
    # Thousand patterns (k, ming, тысяч)
    k_match = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:k|к|тысяч|ming|минг)\b', text, re.IGNORECASE)
    if k_match:
        return int(float(k_match.group(1).replace(",", ".")) * 1_000)
    
    # Formatted numbers (1,000,000 or 1 000 000)
    formatted_match = re.search(r'(\d{1,3}(?:[,\s]\d{3})+)', text)
    if formatted_match:
        return int(re.sub(r'[,\s]', '', formatted_match.group(1)))
    
    # Simple number
    simple_match = re.search(r'(\d+)', text)
    if simple_match:
        num = int(simple_match.group(1))
        if num >= 100:  # Minimum reasonable amount
            return num
    
    return None

def format_money(amount: int) -> str:
    """Format money amount"""
    abs_amt = abs(amount)
    if abs_amt >= 1_000_000:
        return f"{amount / 1_000_000:.1f}".replace(".0", "") + "M UZS"
    return f"{amount:,}".replace(",", " ") + " UZS"

def detect_category(text: str) -> Tuple[str, TxType]:
    """Detect category from text using keywords"""
    text_lower = text.lower()
    
    # Check income first
    for cat_id, cat in CATEGORIES.items():
        if cat.tx_type == TxType.INCOME:
            if any(kw in text_lower for kw in cat.keywords):
                return cat_id, TxType.INCOME
    
    # Check expense
    for cat_id, cat in CATEGORIES.items():
        if cat.tx_type == TxType.EXPENSE:
            if any(kw in text_lower for kw in cat.keywords):
                return cat_id, TxType.EXPENSE
    
    return "other_expense", TxType.EXPENSE

# ============================================
# OPENAI HELPERS (Voice & Vision)
# ============================================
async def transcribe_voice(file_path: str) -> Optional[str]:
    """Transcribe voice message using Whisper"""
    if not OPENAI_API_KEY:
        return None
    try:
        with open(file_path, "rb") as audio_file:
            response = openai.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="uz"
            )
        return response.text
    except Exception as e:
        logger.error(f"transcribe_voice error: {e}")
        return None

async def analyze_receipt(image_url: str) -> Optional[Dict]:
    """Analyze receipt image using GPT-4 Vision"""
    if not OPENAI_API_KEY:
        return None
    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": """Analyze this receipt and extract:
1. Total amount (number only)
2. Store/vendor name
3. Category (one of: food, restaurants, shopping, health, transport, other)

Respond in JSON format:
{"amount": 50000, "vendor": "Store Name", "category": "shopping"}

If you can't read the receipt, respond: {"error": "Cannot read receipt"}"""
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": image_url}
                    }
                ]
            }],
            max_tokens=200
        )
        
        text = response.choices[0].message.content
        # Parse JSON from response
        json_match = re.search(r'\{[^}]+\}', text)
        if json_match:
            return json.loads(json_match.group())
        return None
    except Exception as e:
        logger.error(f"analyze_receipt error: {e}")
        return None

# ============================================
# KEYBOARDS
# ============================================
def get_main_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Get main menu keyboard"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t(user_id, "open_app"), web_app=WebAppInfo(url=WEBAPP_URL))],
        [
            InlineKeyboardButton(t(user_id, "add_expense"), callback_data="menu_expense"),
            InlineKeyboardButton(t(user_id, "add_income"), callback_data="menu_income")
        ],
        [
            InlineKeyboardButton(t(user_id, "add_debt"), callback_data="menu_debt"),
            InlineKeyboardButton(t(user_id, "reports"), callback_data="menu_reports")
        ],
        [
            InlineKeyboardButton(t(user_id, "export"), callback_data="menu_export"),
            InlineKeyboardButton(t(user_id, "settings"), callback_data="menu_settings")
        ]
    ])

def get_category_keyboard(tx_type: TxType, user_id: int) -> InlineKeyboardMarkup:
    """Get category selection keyboard"""
    buttons = []
    row = []
    
    for cat_id, cat in CATEGORIES.items():
        if cat.tx_type == tx_type:
            btn = InlineKeyboardButton(
                f"{cat.emoji} {get_cat_name(cat, user_id)[:12]}",
                callback_data=f"cat:{tx_type.value}:{cat_id}"
            )
            row.append(btn)
            if len(row) == 2:
                buttons.append(row)
                row = []
    
    if row:
        buttons.append(row)
    
    buttons.append([InlineKeyboardButton("❌ Bekor", callback_data="cancel")])
    return InlineKeyboardMarkup(buttons)

def get_settings_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Get settings keyboard"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇺🇿 O'zbek", callback_data="lang:uz")],
        [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang:ru")],
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang:en")],
        [InlineKeyboardButton("◀️ Orqaga", callback_data="back_main")]
    ])

def get_reports_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Get reports keyboard"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 Bugun", callback_data="report:today")],
        [InlineKeyboardButton("📆 Bu hafta", callback_data="report:week")],
        [InlineKeyboardButton("🗓 Bu oy", callback_data="report:month")],
        [InlineKeyboardButton("◀️ Orqaga", callback_data="back_main")]
    ])

# ============================================
# HANDLERS
# ============================================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    if not user:
        return
    
    await get_or_create_user(user.id, user.first_name, user.last_name or "")
    
    await update.message.reply_text(
        t(user.id, "welcome"),
        reply_markup=get_main_keyboard(user.id)
    )

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /balance command"""
    user = update.effective_user
    if not user:
        return
    
    balance = await get_balance(user.id)
    today = await get_today_stats(user.id)
    
    text = f"""
{t(user.id, "balance")}: *{format_money(balance)}*

{t(user.id, "today")}:
{t(user.id, "expenses")}: {format_money(today['expenses'])}
{t(user.id, "income")}: {format_money(today['income'])}
{t(user.id, "transactions")}: {today['count']}
"""
    
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=get_main_keyboard(user.id))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    user = update.effective_user
    if not user:
        return
    
    help_text = """
📖 *Hamyon Bot - Yordam*

*Tranzaksiya qo'shish:*
1️⃣ Kategoriya tanlang → Summa yuboring
2️⃣ Matn yozing: "Taksi 30000"
3️⃣ Ovozli xabar yuboring
4️⃣ Chek rasmini yuboring

*Summa formatlari:*
• 50000 - oddiy raqam
• 50k - ming (50,000)
• 1.5m - million (1,500,000)
• 150 ming - 150,000

*Buyruqlar:*
/start - Bosh menyu
/balance - Balans
/help - Yordam
/export - Eksport (CSV)

*Mini App:*
Toʻliq funksiyalar uchun "Ilovani ochish" tugmasini bosing.
"""
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /export command"""
    user = update.effective_user
    if not user:
        return
    
    await update.message.reply_text("📥 Eksport tayyorlanmoqda...")
    
    csv_content = await export_transactions(user.id, 30)
    if csv_content:
        file = io.BytesIO(csv_content.encode('utf-8'))
        file.name = f"hamyon_export_{datetime.now().strftime('%Y%m%d')}.csv"
        await update.message.reply_document(
            document=InputFile(file),
            caption=t(user.id, "export_ready")
        )
    else:
        await update.message.reply_text("❌ Eksport qilishda xatolik")

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries"""
    query = update.callback_query
    if not query or not query.data:
        return
    
    await query.answer()
    user = query.from_user
    data = query.data
    
    # Menu navigation
    if data == "menu_expense":
        await query.edit_message_text(
            t(user.id, "select_expense"),
            reply_markup=get_category_keyboard(TxType.EXPENSE, user.id)
        )
    
    elif data == "menu_income":
        await query.edit_message_text(
            t(user.id, "select_income"),
            reply_markup=get_category_keyboard(TxType.INCOME, user.id)
        )
    
    elif data == "menu_debt":
        await query.edit_message_text(
            t(user.id, "select_debt"),
            reply_markup=get_category_keyboard(TxType.DEBT, user.id)
        )
    
    elif data == "menu_reports":
        await query.edit_message_text(
            "📊 Hisobot turini tanlang:",
            reply_markup=get_reports_keyboard(user.id)
        )
    
    elif data == "menu_settings":
        await query.edit_message_text(
            t(user.id, "language"),
            reply_markup=get_settings_keyboard(user.id)
        )
    
    elif data == "menu_export":
        await query.edit_message_text("📥 Eksport tayyorlanmoqda...")
        csv_content = await export_transactions(user.id, 30)
        if csv_content:
            file = io.BytesIO(csv_content.encode('utf-8'))
            file.name = f"hamyon_export_{datetime.now().strftime('%Y%m%d')}.csv"
            await context.bot.send_document(
                chat_id=user.id,
                document=InputFile(file),
                caption=t(user.id, "export_ready")
            )
    
    elif data == "back_main":
        balance = await get_balance(user.id)
        await query.edit_message_text(
            f"{t(user.id, 'balance')}: *{format_money(balance)}*",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard(user.id)
        )
    
    elif data == "cancel":
        user_pending.pop(user.id, None)
        await query.edit_message_text(
            "❌ Bekor qilindi",
            reply_markup=get_main_keyboard(user.id)
        )
    
    # Category selection
    elif data.startswith("cat:"):
        parts = data.split(":")
        tx_type = TxType(parts[1])
        category_id = parts[2]
        
        user_pending[user.id] = PendingTransaction(
            category_id=category_id,
            tx_type=tx_type,
            awaiting="amount"
        )
        
        cat = CATEGORIES.get(category_id)
        if cat:
            await query.edit_message_text(
                t(user.id, "enter_amount").format(
                    emoji=cat.emoji,
                    name=get_cat_name(cat, user.id)
                )
            )
    
    # Language selection
    elif data.startswith("lang:"):
        lang = data.split(":")[1]
        user_language[user.id] = lang
        await query.edit_message_text(
            f"✅ Til o'zgartirildi: {'🇺🇿 O\'zbek' if lang == 'uz' else '🇷🇺 Русский' if lang == 'ru' else '🇬🇧 English'}",
            reply_markup=get_main_keyboard(user.id)
        )
    
    # Reports
    elif data.startswith("report:"):
        period = data.split(":")[1]
        days = {"today": 1, "week": 7, "month": 30}.get(period, 7)
        
        stats = await get_period_stats(user.id, days)
        
        # Build category breakdown
        cat_text = ""
        sorted_cats = sorted(stats["by_category"].items(), key=lambda x: x[1], reverse=True)[:5]
        for cat_id, amount in sorted_cats:
            cat = CATEGORIES.get(cat_id)
            if cat:
                cat_text += f"\n{cat.emoji} {get_cat_name(cat, user.id)}: {format_money(amount)}"
        
        period_name = {"today": "Bugun", "week": "Bu hafta", "month": "Bu oy"}.get(period, "")
        
        text = f"""
📊 *{period_name} hisoboti*

{t(user.id, "expenses")}: *{format_money(stats['expenses'])}*
{t(user.id, "income")}: *{format_money(stats['income'])}*
{t(user.id, "transactions")}: {stats['count']}

*Top kategoriyalar:*{cat_text if cat_text else "\nMa'lumot yo'q"}
"""
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=get_reports_keyboard(user.id))

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    user = update.effective_user
    message = update.message
    if not user or not message or not message.text:
        return
    
    text = message.text.strip()
    if text.startswith("/"):
        return
    
    # Check if user has pending category selection
    pending = user_pending.get(user.id)
    if pending:
        amount = parse_amount(text)
        if not amount:
            await message.reply_text(t(user.id, "cant_parse"))
            return
        
        # Determine sign based on transaction type
        if pending.tx_type == TxType.EXPENSE:
            final_amount = -abs(amount)
        elif pending.tx_type == TxType.INCOME:
            final_amount = abs(amount)
        else:  # DEBT
            cat = CATEGORIES.get(pending.category_id)
            if cat and "lent" in cat.id:
                final_amount = -abs(amount)
            else:
                final_amount = abs(amount)
        
        cat = CATEGORIES.get(pending.category_id)
        if not cat:
            return
        
        # Save transaction
        await save_transaction(
            user.id,
            get_cat_name(cat, user.id),
            final_amount,
            pending.category_id,
            "manual"
        )
        
        user_pending.pop(user.id, None)
        
        # Check limits
        await check_and_notify_limit(user.id, pending.category_id, context)
        
        balance = await get_balance(user.id)
        await message.reply_text(
            t(user.id, "saved").format(
                emoji=cat.emoji,
                name=get_cat_name(cat, user.id),
                type_emoji="💸" if final_amount < 0 else "💰",
                amount=format_money(abs(final_amount)),
                balance=format_money(balance)
            ),
            reply_markup=get_main_keyboard(user.id)
        )
        return
    
    # Parse natural text: "Taxi 30000"
    amount = parse_amount(text)
    if not amount:
        await message.reply_text(t(user.id, "cant_parse"), reply_markup=get_main_keyboard(user.id))
        return
    
    category_id, tx_type = detect_category(text)
    final_amount = -abs(amount) if tx_type == TxType.EXPENSE else abs(amount)
    
    cat = CATEGORIES.get(category_id)
    if not cat:
        return
    
    await save_transaction(user.id, text, final_amount, category_id, "text")
    
    # Check limits
    await check_and_notify_limit(user.id, category_id, context)
    
    balance = await get_balance(user.id)
    await message.reply_text(
        t(user.id, "saved").format(
            emoji=cat.emoji,
            name=get_cat_name(cat, user.id),
            type_emoji="💸" if final_amount < 0 else "💰",
            amount=format_money(abs(final_amount)),
            balance=format_money(balance)
        ),
        reply_markup=get_main_keyboard(user.id)
    )

async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice messages"""
    user = update.effective_user
    message = update.message
    if not user or not message or not message.voice:
        return
    
    if not OPENAI_API_KEY:
        await message.reply_text(t(user.id, "no_openai"))
        return
    
    await message.reply_text(t(user.id, "voice_processing"))
    
    try:
        # Download voice file
        voice_file = await message.voice.get_file()
        file_path = f"/tmp/voice_{user.id}_{datetime.now().timestamp()}.ogg"
        await voice_file.download_to_drive(file_path)
        
        # Transcribe
        text = await transcribe_voice(file_path)
        
        # Clean up
        import os
        os.remove(file_path)
        
        if not text:
            await message.reply_text(t(user.id, "cant_parse"))
            return
        
        # Process transcribed text
        amount = parse_amount(text)
        if not amount:
            await message.reply_text(f"🎤 Matn: {text}\n\n" + t(user.id, "cant_parse"))
            return
        
        category_id, tx_type = detect_category(text)
        final_amount = -abs(amount) if tx_type == TxType.EXPENSE else abs(amount)
        
        cat = CATEGORIES.get(category_id)
        if not cat:
            return
        
        await save_transaction(user.id, text, final_amount, category_id, "voice")
        
        balance = await get_balance(user.id)
        await message.reply_text(
            f"🎤 _{text}_\n\n" + t(user.id, "saved").format(
                emoji=cat.emoji,
                name=get_cat_name(cat, user.id),
                type_emoji="💸" if final_amount < 0 else "💰",
                amount=format_money(abs(final_amount)),
                balance=format_money(balance)
            ),
            parse_mode="Markdown",
            reply_markup=get_main_keyboard(user.id)
        )
        
    except Exception as e:
        logger.error(f"voice_handler error: {e}")
        await message.reply_text("❌ Xatolik yuz berdi")

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo messages (receipts)"""
    user = update.effective_user
    message = update.message
    if not user or not message or not message.photo:
        return
    
    if not OPENAI_API_KEY:
        await message.reply_text(t(user.id, "no_openai"))
        return
    
    await message.reply_text(t(user.id, "receipt_processing"))
    
    try:
        # Get photo file
        photo = message.photo[-1]  # Highest resolution
        photo_file = await photo.get_file()
        
        # Analyze receipt
        result = await analyze_receipt(photo_file.file_path)
        
        if not result or "error" in result:
            await message.reply_text("❌ Chekni o'qib bo'lmadi. Iltimos, matn yozing.")
            return
        
        amount = result.get("amount", 0)
        vendor = result.get("vendor", "Chek")
        category_id = result.get("category", "shopping")
        
        if category_id not in CATEGORIES:
            category_id = "shopping"
        
        final_amount = -abs(amount)
        cat = CATEGORIES.get(category_id)
        
        await save_transaction(user.id, vendor, final_amount, category_id, "receipt")
        
        balance = await get_balance(user.id)
        await message.reply_text(
            t(user.id, "saved").format(
                emoji=cat.emoji if cat else "🧾",
                name=vendor,
                type_emoji="💸",
                amount=format_money(abs(final_amount)),
                balance=format_money(balance)
            ),
            reply_markup=get_main_keyboard(user.id)
        )
        
    except Exception as e:
        logger.error(f"photo_handler error: {e}")
        await message.reply_text("❌ Xatolik yuz berdi")

async def check_and_notify_limit(user_id: int, category_id: str, context: ContextTypes.DEFAULT_TYPE):
    """Check if limit is exceeded and notify user"""
    limit = await get_category_limit(user_id, category_id)
    if not limit:
        return
    
    spent = await get_month_spent(user_id, category_id)
    percent = int((spent / limit) * 100) if limit > 0 else 0
    
    cat = CATEGORIES.get(category_id)
    if not cat:
        return
    
    if percent >= 100:
        await context.bot.send_message(
            chat_id=user_id,
            text=t(user_id, "limit_exceeded").format(
                emoji=cat.emoji,
                name=get_cat_name(cat, user_id),
                limit=format_money(limit),
                spent=format_money(spent),
                percent=percent
            )
        )
    elif percent >= 80:
        await context.bot.send_message(
            chat_id=user_id,
            text=t(user_id, "limit_warning").format(
                emoji=cat.emoji,
                name=get_cat_name(cat, user_id),
                limit=format_money(limit),
                spent=format_money(spent),
                percent=percent
            )
        )

# ============================================
# MAIN
# ============================================
def main():
    """Start the bot"""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Commands
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("balance", balance_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("export", export_command))
    
    # Callbacks
    application.add_handler(CallbackQueryHandler(callback_handler))
    
    # Messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    application.add_handler(MessageHandler(filters.VOICE, voice_handler))
    application.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    
    # Start
    logger.info("🚀 Hamyon Bot ishga tushdi...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
