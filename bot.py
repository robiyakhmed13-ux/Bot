"""
💰 Hamyon — Professional Financial Tracker Bot
Polished UI, smooth UX, production-ready

Features:
- Quick expense entry: "taksi 20000" or "food 45000"
- Voice message transcription
- Receipt OCR
- Multi-language (uz/ru/en)
- Statistics & CSV export
- Mini App integration
"""

import os
import json
import uuid
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Tuple, List

import httpx
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode

from nlp import parse_one, parse_multi, normalize_category

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = os.getenv("API_URL") or os.getenv("PUBLIC_URL") or os.getenv("BACKEND_URL")
API_SECRET = os.getenv("API_SECRET", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
WEBAPP_URL = os.getenv("WEBAPP_URL", "")

if not TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN not set")
if not API_URL:
    raise ValueError("❌ API_URL not set")

# ══════════════════════════════════════════════════════════════════════════════
# TRANSLATIONS - Clean & Professional
# ══════════════════════════════════════════════════════════════════════════════

I18N = {
    "uz": {
        # Welcome & Menu
        "welcome": (
            "👋 *Assalomu alaykum!*\n\n"
            "Men *Hamyon* — shaxsiy moliyaviy yordamchingiz.\n\n"
            "💡 *Tez qo'shish:*\n"
            "`taksi 20000` • `ovqat 45000` • `internet 50000`\n\n"
            "🎙 Ovozli xabar yoki 🧾 chek rasmini yuboring\n\n"
            "Pastdagi tugmalardan foydalaning 👇"
        ),
        "choose_lang": "🌐 *Tilni tanlang:*",
        "lang_changed": "✅ Til o'zgartirildi!",
        
        # Main menu buttons
        "btn_add": "➕ Qo'shish",
        "btn_expense": "💸 Xarajat",
        "btn_income": "💰 Daromad",
        "btn_debt": "📋 Qarz",
        "btn_stats": "📊 Statistika",
        "btn_settings": "⚙️ Sozlamalar",
        "btn_app": "📱 Ilova",
        "btn_help": "❓ Yordam",
        "btn_back": "◀️ Orqaga",
        
        # Quick add menu
        "quick_add_title": "➕ *Yangi yozuv qo'shish*\n\nTurni tanlang:",
        "quick_expense": "💸 Xarajat qo'shish",
        "quick_income": "💰 Daromad qo'shish",
        "quick_debt": "📋 Qarz yozish",
        
        # Categories
        "cat_food": "🍕 Ovqat",
        "cat_transport": "🚕 Transport",
        "cat_internet": "📱 Aloqa",
        "cat_health": "💊 Sog'liq",
        "cat_rent": "🏠 Ijara",
        "cat_utilities": "💡 Kommunal",
        "cat_entertainment": "🎬 Ko'ngil ochar",
        "cat_shopping": "🛍 Xaridlar",
        "cat_education": "📚 Ta'lim",
        "cat_salary": "💵 Maosh",
        "cat_business": "💼 Biznes",
        "cat_gift": "🎁 Sovg'a",
        "cat_other": "📦 Boshqa",
        
        # Stats
        "stats_title": "📊 *Statistika*\n\nDavrni tanlang:",
        "stats_today": "📊 Bugun",
        "stats_week": "📆 7 kun",
        "stats_month": "🗓 30 kun",
        "stats_csv": "⬇️ CSV yuklab olish",
        "stats_result": (
            "📊 *{period}*\n\n"
            "💸 Xarajat: *{expense:,}* so'm\n"
            "💰 Daromad: *{income:,}* so'm\n"
            "📋 Qarz: *{debt:,}* so'm\n"
            "━━━━━━━━━━━━━━━━\n"
            "📝 Jami yozuvlar: *{count}*"
        ),
        
        # Draft confirmation
        "draft_title": "📝 *Tasdiqlash*",
        "draft_type": "📌 Tur",
        "draft_category": "🏷 Kategoriya",
        "draft_amount": "💵 Summa",
        "draft_desc": "📝 Izoh",
        "draft_source": "📥 Manba",
        "btn_confirm": "✅ Tasdiqlash",
        "btn_edit": "✏️ Tahrirlash",
        "btn_cancel": "❌ Bekor qilish",
        
        # Edit menu
        "edit_title": "✏️ *Tahrirlash*\n\nNimani o'zgartirmoqchisiz?",
        "edit_category": "🏷 Kategoriya",
        "edit_amount": "💵 Summa",
        "edit_desc": "📝 Izoh",
        "edit_type": "📌 Tur",
        
        # Input prompts
        "ask_amount": "💵 *Summani kiriting:*\n\nFaqat raqam yuboring (masalan: `50000`)",
        "ask_desc": "📝 *Izoh kiriting:*\n\nYoki `-` yuboring",
        "ask_category": "🏷 *Kategoriyani tanlang:*",
        "ask_type": "📌 *Turni tanlang:*",
        
        # Messages
        "saved": "✅ *Muvaffaqiyatli saqlandi!*",
        "cancelled": "❌ Bekor qilindi",
        "updated": "✅ Yangilandi",
        "error": "⚠️ Xatolik yuz berdi",
        "not_found": "⚠️ Topilmadi",
        "invalid_input": "❌ Noto'g'ri kiritish",
        "not_understood": (
            "🤔 Tushunmadim.\n\n"
            "💡 *Misol:* `taksi 20000` yoki `ovqat 45000`\n"
            "🎙 Yoki ovozli xabar yuboring"
        ),
        "voice_no_key": "🎙 Ovozni o'qish uchun tizim sozlanmagan",
        "csv_caption": "📊 Sizning tranzaksiyalaringiz",
        
        # Settings
        "settings_title": "⚙️ *Sozlamalar*",
        "settings_lang": "🌐 Til",
        "settings_notifications": "🔔 Bildirishnomalar",
        
        # Help
        "help_text": (
            "❓ *Yordam*\n\n"
            "🔹 *Tez qo'shish:*\n"
            "  `taksi 20000` — transport xarajati\n"
            "  `ovqat 45000 tushlik` — izohli\n"
            "  `maosh 5000000` — daromad\n\n"
            "🔹 *Ovozli xabar:*\n"
            "  Shunchaki gapiring: \"taksi yigirma ming\"\n\n"
            "🔹 *Chek rasmi:*\n"
            "  Rasmni yuboring — avtomatik o'qiladi\n\n"
            "🔹 *Buyruqlar:*\n"
            "  /start — Bosh menyu\n"
            "  /stats — Statistika\n"
            "  /help — Yordam"
        ),
        
        # Types
        "type_expense": "💸 Xarajat",
        "type_income": "💰 Daromad",
        "type_debt": "📋 Qarz",
        
        # App
        "app_title": "📱 *Hamyon ilovasi*\n\nTo'liq funksiyalar uchun ilovani oching:",
        "app_open": "📱 Ilovani ochish",
        "app_not_set": "📱 Ilova hali sozlanmagan",
    },
    
    "ru": {
        "welcome": (
            "👋 *Привет!*\n\n"
            "Я *Hamyon* — ваш финансовый помощник.\n\n"
            "💡 *Быстрый ввод:*\n"
            "`такси 20000` • `еда 45000` • `интернет 50000`\n\n"
            "🎙 Голосовое или 🧾 фото чека\n\n"
            "Используйте кнопки ниже 👇"
        ),
        "choose_lang": "🌐 *Выберите язык:*",
        "lang_changed": "✅ Язык изменен!",
        
        "btn_add": "➕ Добавить",
        "btn_expense": "💸 Расход",
        "btn_income": "💰 Доход",
        "btn_debt": "📋 Долг",
        "btn_stats": "📊 Статистика",
        "btn_settings": "⚙️ Настройки",
        "btn_app": "📱 Приложение",
        "btn_help": "❓ Помощь",
        "btn_back": "◀️ Назад",
        
        "quick_add_title": "➕ *Новая запись*\n\nВыберите тип:",
        "quick_expense": "💸 Добавить расход",
        "quick_income": "💰 Добавить доход",
        "quick_debt": "📋 Записать долг",
        
        "cat_food": "🍕 Еда",
        "cat_transport": "🚕 Транспорт",
        "cat_internet": "📱 Связь",
        "cat_health": "💊 Здоровье",
        "cat_rent": "🏠 Аренда",
        "cat_utilities": "💡 Коммуналка",
        "cat_entertainment": "🎬 Развлечения",
        "cat_shopping": "🛍 Покупки",
        "cat_education": "📚 Образование",
        "cat_salary": "💵 Зарплата",
        "cat_business": "💼 Бизнес",
        "cat_gift": "🎁 Подарок",
        "cat_other": "📦 Другое",
        
        "stats_title": "📊 *Статистика*\n\nВыберите период:",
        "stats_today": "📊 Сегодня",
        "stats_week": "📆 7 дней",
        "stats_month": "🗓 30 дней",
        "stats_csv": "⬇️ Скачать CSV",
        "stats_result": (
            "📊 *{period}*\n\n"
            "💸 Расходы: *{expense:,}* сум\n"
            "💰 Доходы: *{income:,}* сум\n"
            "📋 Долги: *{debt:,}* сум\n"
            "━━━━━━━━━━━━━━━━\n"
            "📝 Всего записей: *{count}*"
        ),
        
        "draft_title": "📝 *Подтверждение*",
        "draft_type": "📌 Тип",
        "draft_category": "🏷 Категория",
        "draft_amount": "💵 Сумма",
        "draft_desc": "📝 Описание",
        "draft_source": "📥 Источник",
        "btn_confirm": "✅ Подтвердить",
        "btn_edit": "✏️ Изменить",
        "btn_cancel": "❌ Отмена",
        
        "edit_title": "✏️ *Редактирование*\n\nЧто изменить?",
        "edit_category": "🏷 Категория",
        "edit_amount": "💵 Сумма",
        "edit_desc": "📝 Описание",
        "edit_type": "📌 Тип",
        
        "ask_amount": "💵 *Введите сумму:*\n\nТолько цифры (например: `50000`)",
        "ask_desc": "📝 *Введите описание:*\n\nИли отправьте `-`",
        "ask_category": "🏷 *Выберите категорию:*",
        "ask_type": "📌 *Выберите тип:*",
        
        "saved": "✅ *Успешно сохранено!*",
        "cancelled": "❌ Отменено",
        "updated": "✅ Обновлено",
        "error": "⚠️ Произошла ошибка",
        "not_found": "⚠️ Не найдено",
        "invalid_input": "❌ Неверный ввод",
        "not_understood": (
            "🤔 Не понял.\n\n"
            "💡 *Пример:* `такси 20000` или `еда 45000`\n"
            "🎙 Или отправьте голосовое"
        ),
        "voice_no_key": "🎙 Распознавание голоса не настроено",
        "csv_caption": "📊 Ваши транзакции",
        
        "settings_title": "⚙️ *Настройки*",
        "settings_lang": "🌐 Язык",
        "settings_notifications": "🔔 Уведомления",
        
        "help_text": (
            "❓ *Помощь*\n\n"
            "🔹 *Быстрый ввод:*\n"
            "  `такси 20000` — расход\n"
            "  `еда 45000 обед` — с описанием\n"
            "  `зарплата 5000000` — доход\n\n"
            "🔹 *Голосовое:*\n"
            "  Просто скажите: \"такси двадцать тысяч\"\n\n"
            "🔹 *Фото чека:*\n"
            "  Отправьте фото — распознается автоматически\n\n"
            "🔹 *Команды:*\n"
            "  /start — Главное меню\n"
            "  /stats — Статистика\n"
            "  /help — Помощь"
        ),
        
        "type_expense": "💸 Расход",
        "type_income": "💰 Доход",
        "type_debt": "📋 Долг",
        
        "app_title": "📱 *Приложение Hamyon*\n\nОткройте для полного функционала:",
        "app_open": "📱 Открыть приложение",
        "app_not_set": "📱 Приложение пока не настроено",
    },
    
    "en": {
        "welcome": (
            "👋 *Hello!*\n\n"
            "I'm *Hamyon* — your personal finance assistant.\n\n"
            "💡 *Quick add:*\n"
            "`taxi 20000` • `food 45000` • `internet 50000`\n\n"
            "🎙 Voice message or 🧾 receipt photo\n\n"
            "Use the buttons below 👇"
        ),
        "choose_lang": "🌐 *Choose language:*",
        "lang_changed": "✅ Language changed!",
        
        "btn_add": "➕ Add",
        "btn_expense": "💸 Expense",
        "btn_income": "💰 Income",
        "btn_debt": "📋 Debt",
        "btn_stats": "📊 Statistics",
        "btn_settings": "⚙️ Settings",
        "btn_app": "📱 App",
        "btn_help": "❓ Help",
        "btn_back": "◀️ Back",
        
        "quick_add_title": "➕ *New Entry*\n\nSelect type:",
        "quick_expense": "💸 Add expense",
        "quick_income": "💰 Add income",
        "quick_debt": "📋 Record debt",
        
        "cat_food": "🍕 Food",
        "cat_transport": "🚕 Transport",
        "cat_internet": "📱 Internet",
        "cat_health": "💊 Health",
        "cat_rent": "🏠 Rent",
        "cat_utilities": "💡 Utilities",
        "cat_entertainment": "🎬 Entertainment",
        "cat_shopping": "🛍 Shopping",
        "cat_education": "📚 Education",
        "cat_salary": "💵 Salary",
        "cat_business": "💼 Business",
        "cat_gift": "🎁 Gift",
        "cat_other": "📦 Other",
        
        "stats_title": "📊 *Statistics*\n\nSelect period:",
        "stats_today": "📊 Today",
        "stats_week": "📆 7 days",
        "stats_month": "🗓 30 days",
        "stats_csv": "⬇️ Download CSV",
        "stats_result": (
            "📊 *{period}*\n\n"
            "💸 Expenses: *{expense:,}* UZS\n"
            "💰 Income: *{income:,}* UZS\n"
            "📋 Debts: *{debt:,}* UZS\n"
            "━━━━━━━━━━━━━━━━\n"
            "📝 Total entries: *{count}*"
        ),
        
        "draft_title": "📝 *Confirmation*",
        "draft_type": "📌 Type",
        "draft_category": "🏷 Category",
        "draft_amount": "💵 Amount",
        "draft_desc": "📝 Note",
        "draft_source": "📥 Source",
        "btn_confirm": "✅ Confirm",
        "btn_edit": "✏️ Edit",
        "btn_cancel": "❌ Cancel",
        
        "edit_title": "✏️ *Edit*\n\nWhat to change?",
        "edit_category": "🏷 Category",
        "edit_amount": "💵 Amount",
        "edit_desc": "📝 Note",
        "edit_type": "📌 Type",
        
        "ask_amount": "💵 *Enter amount:*\n\nNumbers only (e.g., `50000`)",
        "ask_desc": "📝 *Enter description:*\n\nOr send `-`",
        "ask_category": "🏷 *Select category:*",
        "ask_type": "📌 *Select type:*",
        
        "saved": "✅ *Successfully saved!*",
        "cancelled": "❌ Cancelled",
        "updated": "✅ Updated",
        "error": "⚠️ An error occurred",
        "not_found": "⚠️ Not found",
        "invalid_input": "❌ Invalid input",
        "not_understood": (
            "🤔 I didn't understand.\n\n"
            "💡 *Example:* `taxi 20000` or `food 45000`\n"
            "🎙 Or send a voice message"
        ),
        "voice_no_key": "🎙 Voice recognition not configured",
        "csv_caption": "📊 Your transactions",
        
        "settings_title": "⚙️ *Settings*",
        "settings_lang": "🌐 Language",
        "settings_notifications": "🔔 Notifications",
        
        "help_text": (
            "❓ *Help*\n\n"
            "🔹 *Quick add:*\n"
            "  `taxi 20000` — expense\n"
            "  `food 45000 lunch` — with note\n"
            "  `salary 5000000` — income\n\n"
            "🔹 *Voice message:*\n"
            "  Just say: \"taxi twenty thousand\"\n\n"
            "🔹 *Receipt photo:*\n"
            "  Send a photo — auto-recognized\n\n"
            "🔹 *Commands:*\n"
            "  /start — Main menu\n"
            "  /stats — Statistics\n"
            "  /help — Help"
        ),
        
        "type_expense": "💸 Expense",
        "type_income": "💰 Income",
        "type_debt": "📋 Debt",
        
        "app_title": "📱 *Hamyon App*\n\nOpen for full features:",
        "app_open": "📱 Open App",
        "app_not_set": "📱 App not configured yet",
    },
}

def t(lang: str, key: str) -> str:
    """Get translated text"""
    lang = lang if lang in I18N else "uz"
    return I18N[lang].get(key, I18N["uz"].get(key, key))


# ══════════════════════════════════════════════════════════════════════════════
# CATEGORIES
# ══════════════════════════════════════════════════════════════════════════════

CATEGORIES = {
    "expense": [
        ("food", "🍕"), ("transport", "🚕"), ("internet", "📱"),
        ("health", "💊"), ("rent", "🏠"), ("utilities", "💡"),
        ("entertainment", "🎬"), ("shopping", "🛍"), ("education", "📚"),
        ("other", "📦"),
    ],
    "income": [
        ("salary", "💵"), ("business", "💼"), ("gift", "🎁"),
        ("other", "📦"),
    ],
    "debt": [
        ("personal", "👤"), ("business", "💼"), ("other", "📦"),
    ],
}

def get_category_name(lang: str, cat_key: str) -> str:
    """Get localized category name"""
    return t(lang, f"cat_{cat_key}")


# ══════════════════════════════════════════════════════════════════════════════
# DRAFT STATE
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class Draft:
    tx_type: str = "expense"
    category_key: str = "other"
    amount: int = 0
    description: Optional[str] = None
    source: str = "text"

DRAFTS: Dict[Tuple[int, str], Draft] = {}
EDIT_MODE: Dict[int, Tuple[str, str]] = {}
USER_STATE: Dict[int, str] = {}


# ══════════════════════════════════════════════════════════════════════════════
# API HELPERS
# ══════════════════════════════════════════════════════════════════════════════

async def api_post(path: str, json_body: dict) -> dict:
    headers = {"X-API-SECRET": API_SECRET} if API_SECRET else {}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{API_URL}{path}", json=json_body, headers=headers)
        r.raise_for_status()
        return r.json()

async def api_get(path: str, params: dict) -> Tuple[dict, httpx.Response]:
    headers = {"X-API-SECRET": API_SECRET} if API_SECRET else {}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{API_URL}{path}", params=params, headers=headers)
        r.raise_for_status()
        return r.json(), r

async def get_user_lang(tg_id: int) -> str:
    try:
        data, _ = await api_get("/users/lang", {"telegram_id": tg_id})
        return data.get("language", "uz")
    except:
        return "uz"

async def set_user_lang(tg_id: int, lang: str):
    try:
        await api_post("/users/lang", {"telegram_id": tg_id, "language": lang})
    except:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# KEYBOARDS - Clean & Professional
# ══════════════════════════════════════════════════════════════════════════════

def kb_main_menu(lang: str) -> ReplyKeyboardMarkup:
    """Main reply keyboard - clean 2x3 grid"""
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(t(lang, "btn_add")), KeyboardButton(t(lang, "btn_stats"))],
            [KeyboardButton(t(lang, "btn_settings")), KeyboardButton(t(lang, "btn_app"))],
        ],
        resize_keyboard=True,
        input_field_placeholder=t(lang, "btn_add") + "..."
    )

def kb_language() -> InlineKeyboardMarkup:
    """Language selection"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🇺🇿 O'zbek", callback_data="lang:uz"),
            InlineKeyboardButton("🇷🇺 Русский", callback_data="lang:ru"),
        ],
        [
            InlineKeyboardButton("🇬🇧 English", callback_data="lang:en"),
        ],
    ])

def kb_quick_add(lang: str) -> InlineKeyboardMarkup:
    """Quick add type selection"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t(lang, "quick_expense"), callback_data="quickadd:expense")],
        [InlineKeyboardButton(t(lang, "quick_income"), callback_data="quickadd:income")],
        [InlineKeyboardButton(t(lang, "quick_debt"), callback_data="quickadd:debt")],
    ])

def kb_stats(lang: str) -> InlineKeyboardMarkup:
    """Statistics period selection"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(t(lang, "stats_today"), callback_data="stats:1"),
            InlineKeyboardButton(t(lang, "stats_week"), callback_data="stats:7"),
        ],
        [
            InlineKeyboardButton(t(lang, "stats_month"), callback_data="stats:30"),
            InlineKeyboardButton(t(lang, "stats_csv"), callback_data="stats:csv"),
        ],
    ])

def kb_settings(lang: str) -> InlineKeyboardMarkup:
    """Settings menu"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t(lang, "settings_lang"), callback_data="settings:lang")],
        [InlineKeyboardButton(t(lang, "btn_help"), callback_data="settings:help")],
    ])

def kb_draft_confirm(lang: str, draft_id: str) -> InlineKeyboardMarkup:
    """Draft confirmation - clean layout"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(t(lang, "btn_confirm"), callback_data=f"draft:save:{draft_id}"),
            InlineKeyboardButton(t(lang, "btn_edit"), callback_data=f"draft:edit:{draft_id}"),
        ],
        [
            InlineKeyboardButton(t(lang, "btn_cancel"), callback_data=f"draft:cancel:{draft_id}"),
        ],
    ])

def kb_draft_edit(lang: str, draft_id: str) -> InlineKeyboardMarkup:
    """Edit menu - what to change"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(t(lang, "edit_category"), callback_data=f"edit:cat:{draft_id}"),
            InlineKeyboardButton(t(lang, "edit_amount"), callback_data=f"edit:amt:{draft_id}"),
        ],
        [
            InlineKeyboardButton(t(lang, "edit_desc"), callback_data=f"edit:desc:{draft_id}"),
            InlineKeyboardButton(t(lang, "edit_type"), callback_data=f"edit:type:{draft_id}"),
        ],
        [
            InlineKeyboardButton(t(lang, "btn_back"), callback_data=f"draft:back:{draft_id}"),
        ],
    ])

def kb_categories(lang: str, draft_id: str, tx_type: str) -> InlineKeyboardMarkup:
    """Category picker based on transaction type"""
    cats = CATEGORIES.get(tx_type, CATEGORIES["expense"])
    rows = []
    row = []
    for key, emoji in cats:
        btn_text = f"{emoji} {key.capitalize()}"
        row.append(InlineKeyboardButton(btn_text, callback_data=f"pickcat:{key}:{draft_id}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(t(lang, "btn_back"), callback_data=f"draft:edit:{draft_id}")])
    return InlineKeyboardMarkup(rows)

def kb_tx_type(lang: str, draft_id: str) -> InlineKeyboardMarkup:
    """Transaction type picker"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t(lang, "type_expense"), callback_data=f"picktype:expense:{draft_id}")],
        [InlineKeyboardButton(t(lang, "type_income"), callback_data=f"picktype:income:{draft_id}")],
        [InlineKeyboardButton(t(lang, "type_debt"), callback_data=f"picktype:debt:{draft_id}")],
        [InlineKeyboardButton(t(lang, "btn_back"), callback_data=f"draft:edit:{draft_id}")],
    ])

def kb_app(lang: str) -> InlineKeyboardMarkup:
    """App button with WebApp"""
    if WEBAPP_URL:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(t(lang, "app_open"), web_app=WebAppInfo(url=WEBAPP_URL))],
        ])
    return None


# ══════════════════════════════════════════════════════════════════════════════
# FORMATTERS
# ══════════════════════════════════════════════════════════════════════════════

def format_amount(amount: int) -> str:
    """Format number with thousands separator"""
    return f"{amount:,}".replace(",", " ")

def format_draft(lang: str, d: Draft, raw_text: str = "") -> str:
    """Format draft for confirmation - clean card style"""
    type_labels = {
        "expense": t(lang, "type_expense"),
        "income": t(lang, "type_income"),
        "debt": t(lang, "type_debt"),
    }
    
    source_labels = {
        "text": "⌨️ Text",
        "voice": "🎙 Voice",
        "receipt": "🧾 Receipt",
    }
    
    lines = [
        t(lang, "draft_title"),
        "",
        f"{t(lang, 'draft_type')}: {type_labels.get(d.tx_type, d.tx_type)}",
        f"{t(lang, 'draft_category')}: {d.category_key.capitalize()}",
        f"{t(lang, 'draft_amount')}: *{format_amount(d.amount)}* so'm",
    ]
    
    if d.description:
        lines.append(f"{t(lang, 'draft_desc')}: {d.description}")
    
    lines.append(f"{t(lang, 'draft_source')}: {source_labels.get(d.source, d.source)}")
    
    if raw_text:
        lines.append("")
        lines.append(f"📝 _{raw_text}_")
    
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# VOICE TRANSCRIPTION
# ══════════════════════════════════════════════════════════════════════════════

async def transcribe_voice(file_bytes: bytes) -> Optional[str]:
    """Transcribe voice using OpenAI Whisper"""
    if not OPENAI_API_KEY:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        resp = client.audio.transcriptions.create(
            model="whisper-1",
            file=("voice.ogg", file_bytes),
            language="uz",  # Can be improved with language detection
        )
        return (resp.text or "").strip()
    except Exception as e:
        print(f"Voice transcription error: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# HANDLERS
# ══════════════════════════════════════════════════════════════════════════════

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    tg_id = update.effective_user.id
    lang = await get_user_lang(tg_id)
    
    await update.message.reply_text(
        t(lang, "welcome"),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb_main_menu(lang)
    )

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    tg_id = update.effective_user.id
    lang = await get_user_lang(tg_id)
    
    await update.message.reply_text(
        t(lang, "help_text"),
        parse_mode=ParseMode.MARKDOWN
    )

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command"""
    tg_id = update.effective_user.id
    lang = await get_user_lang(tg_id)
    
    await update.message.reply_text(
        t(lang, "stats_title"),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb_stats(lang)
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all inline button callbacks"""
    query = update.callback_query
    await query.answer()
    
    tg_id = query.from_user.id
    lang = await get_user_lang(tg_id)
    data = query.data
    
    try:
        # ═══════════════════════════════════════════════════════════════════
        # LANGUAGE SELECTION
        # ═══════════════════════════════════════════════════════════════════
        if data.startswith("lang:"):
            new_lang = data.split(":")[1]
            await set_user_lang(tg_id, new_lang)
            
            await query.edit_message_text(
                t(new_lang, "lang_changed"),
                parse_mode=ParseMode.MARKDOWN
            )
            
            await query.message.reply_text(
                t(new_lang, "welcome"),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb_main_menu(new_lang)
            )
            return
        
        # ═══════════════════════════════════════════════════════════════════
        # STATISTICS
        # ═══════════════════════════════════════════════════════════════════
        if data.startswith("stats:"):
            period = data.split(":")[1]
            
            if period == "csv":
                _, response = await api_get("/export/csv", {"telegram_id": tg_id})
                await query.message.reply_document(
                    document=response.content,
                    filename=f"hamyon_export_{datetime.now().strftime('%Y%m%d')}.csv",
                    caption=t(lang, "csv_caption")
                )
                return
            
            days = int(period)
            if days == 1:
                result, _ = await api_get("/stats/today", {"telegram_id": tg_id})
                period_text = t(lang, "stats_today")
            else:
                result, _ = await api_get("/stats/range", {"telegram_id": tg_id, "days": days})
                period_text = f"📆 {days} " + ("kun" if lang == "uz" else "дней" if lang == "ru" else "days")
            
            text = t(lang, "stats_result").format(
                period=period_text,
                expense=result.get("expense", 0),
                income=result.get("income", 0),
                debt=result.get("debt", 0),
                count=result.get("count", 0)
            )
            
            await query.edit_message_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb_stats(lang)
            )
            return
        
        # ═══════════════════════════════════════════════════════════════════
        # SETTINGS
        # ═══════════════════════════════════════════════════════════════════
        if data.startswith("settings:"):
            action = data.split(":")[1]
            
            if action == "lang":
                await query.edit_message_text(
                    t(lang, "choose_lang"),
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=kb_language()
                )
            elif action == "help":
                await query.edit_message_text(
                    t(lang, "help_text"),
                    parse_mode=ParseMode.MARKDOWN
                )
            return
        
        # ═══════════════════════════════════════════════════════════════════
        # QUICK ADD
        # ═══════════════════════════════════════════════════════════════════
        if data.startswith("quickadd:"):
            tx_type = data.split(":")[1]
            USER_STATE[tg_id] = f"quickadd:{tx_type}"
            
            prompt = {
                "expense": "💸 Xarajatni yozing:\n`taksi 20000` yoki `ovqat 45000`",
                "income": "💰 Daromadni yozing:\n`maosh 5000000` yoki `bonus 500000`",
                "debt": "📋 Qarzni yozing:\n`qarz 200000 Ali`",
            }
            
            await query.edit_message_text(
                prompt.get(tx_type, prompt["expense"]),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # ═══════════════════════════════════════════════════════════════════
        # DRAFT ACTIONS
        # ═══════════════════════════════════════════════════════════════════
        if data.startswith("draft:"):
            _, action, draft_id = data.split(":")
            key = (tg_id, draft_id)
            
            if action == "cancel":
                if key in DRAFTS:
                    del DRAFTS[key]
                if tg_id in EDIT_MODE:
                    del EDIT_MODE[tg_id]
                await query.edit_message_text(t(lang, "cancelled"))
                return
            
            draft = DRAFTS.get(key)
            if not draft:
                await query.edit_message_text(t(lang, "not_found"))
                return
            
            if action == "save":
                await api_post("/transactions", {
                    "telegram_id": tg_id,
                    "type": draft.tx_type,
                    "amount": draft.amount,
                    "category_key": draft.category_key,
                    "description": draft.description,
                    "source": draft.source,
                })
                del DRAFTS[key]
                if tg_id in EDIT_MODE:
                    del EDIT_MODE[tg_id]
                
                await query.edit_message_text(
                    t(lang, "saved"),
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            if action == "edit":
                await query.edit_message_text(
                    t(lang, "edit_title"),
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=kb_draft_edit(lang, draft_id)
                )
                return
            
            if action == "back":
                await query.edit_message_text(
                    format_draft(lang, draft),
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=kb_draft_confirm(lang, draft_id)
                )
                return
        
        # ═══════════════════════════════════════════════════════════════════
        # EDIT ACTIONS
        # ═══════════════════════════════════════════════════════════════════
        if data.startswith("edit:"):
            _, field, draft_id = data.split(":")
            key = (tg_id, draft_id)
            draft = DRAFTS.get(key)
            
            if not draft:
                await query.edit_message_text(t(lang, "not_found"))
                return
            
            if field == "cat":
                await query.edit_message_text(
                    t(lang, "ask_category"),
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=kb_categories(lang, draft_id, draft.tx_type)
                )
            elif field == "type":
                await query.edit_message_text(
                    t(lang, "ask_type"),
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=kb_tx_type(lang, draft_id)
                )
            elif field == "amt":
                EDIT_MODE[tg_id] = (draft_id, "amount")
                await query.edit_message_text(
                    t(lang, "ask_amount"),
                    parse_mode=ParseMode.MARKDOWN
                )
            elif field == "desc":
                EDIT_MODE[tg_id] = (draft_id, "description")
                await query.edit_message_text(
                    t(lang, "ask_desc"),
                    parse_mode=ParseMode.MARKDOWN
                )
            return
        
        # ═══════════════════════════════════════════════════════════════════
        # PICK CATEGORY
        # ═══════════════════════════════════════════════════════════════════
        if data.startswith("pickcat:"):
            _, cat, draft_id = data.split(":")
            key = (tg_id, draft_id)
            draft = DRAFTS.get(key)
            
            if not draft:
                await query.edit_message_text(t(lang, "not_found"))
                return
            
            draft.category_key = cat
            await query.edit_message_text(
                format_draft(lang, draft),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb_draft_confirm(lang, draft_id)
            )
            return
        
        # ═══════════════════════════════════════════════════════════════════
        # PICK TYPE
        # ═══════════════════════════════════════════════════════════════════
        if data.startswith("picktype:"):
            _, tx_type, draft_id = data.split(":")
            key = (tg_id, draft_id)
            draft = DRAFTS.get(key)
            
            if not draft:
                await query.edit_message_text(t(lang, "not_found"))
                return
            
            draft.tx_type = tx_type
            await query.edit_message_text(
                format_draft(lang, draft),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb_draft_confirm(lang, draft_id)
            )
            return
    
    except Exception as e:
        print(f"Callback error: {e}")
        await query.message.reply_text(t(lang, "error"))

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    tg_id = update.effective_user.id
    lang = await get_user_lang(tg_id)
    text = (update.message.text or "").strip()
    
    # ═══════════════════════════════════════════════════════════════════════
    # MENU BUTTON HANDLERS
    # ═══════════════════════════════════════════════════════════════════════
    
    # Add button
    if text in [t(l, "btn_add") for l in ["uz", "ru", "en"]]:
        await update.message.reply_text(
            t(lang, "quick_add_title"),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb_quick_add(lang)
        )
        return
    
    # Stats button
    if text in [t(l, "btn_stats") for l in ["uz", "ru", "en"]]:
        await update.message.reply_text(
            t(lang, "stats_title"),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb_stats(lang)
        )
        return
    
    # Settings button
    if text in [t(l, "btn_settings") for l in ["uz", "ru", "en"]]:
        await update.message.reply_text(
            t(lang, "settings_title"),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb_settings(lang)
        )
        return
    
    # App button
    if text in [t(l, "btn_app") for l in ["uz", "ru", "en"]]:
        kb = kb_app(lang)
        if kb:
            await update.message.reply_text(
                t(lang, "app_title"),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb
            )
        else:
            await update.message.reply_text(t(lang, "app_not_set"))
        return
    
    # ═══════════════════════════════════════════════════════════════════════
    # EDIT MODE - User is editing a draft field
    # ═══════════════════════════════════════════════════════════════════════
    if tg_id in EDIT_MODE:
        draft_id, field = EDIT_MODE[tg_id]
        key = (tg_id, draft_id)
        draft = DRAFTS.get(key)
        
        if not draft:
            del EDIT_MODE[tg_id]
            await update.message.reply_text(t(lang, "not_found"))
            return
        
        if field == "amount":
            digits = "".join(ch for ch in text if ch.isdigit())
            if not digits:
                await update.message.reply_text(
                    t(lang, "ask_amount"),
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            draft.amount = int(digits)
            del EDIT_MODE[tg_id]
        
        elif field == "description":
            draft.description = None if text == "-" else text
            del EDIT_MODE[tg_id]
        
        await update.message.reply_text(
            format_draft(lang, draft),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb_draft_confirm(lang, draft_id)
        )
        return
    
    # ═══════════════════════════════════════════════════════════════════════
    # QUICK ADD - Parse expense/income text
    # ═══════════════════════════════════════════════════════════════════════
    
    # Determine transaction type from state or default
    tx_type = "expense"
    if tg_id in USER_STATE:
        state = USER_STATE[tg_id]
        if state.startswith("quickadd:"):
            tx_type = state.split(":")[1]
        del USER_STATE[tg_id]
    
    # Try to parse the text
    parsed = parse_one(text)
    if not parsed:
        await update.message.reply_text(
            t(lang, "not_understood"),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    cat, amount, desc = parsed
    draft_id = uuid.uuid4().hex[:8]
    
    draft = Draft(
        tx_type=tx_type,
        category_key=normalize_category(cat),
        amount=amount,
        description=desc,
        source="text"
    )
    DRAFTS[(tg_id, draft_id)] = draft
    
    await update.message.reply_text(
        format_draft(lang, draft, raw_text=text),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb_draft_confirm(lang, draft_id)
    )

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice messages"""
    tg_id = update.effective_user.id
    lang = await get_user_lang(tg_id)
    
    voice = update.message.voice
    if not voice:
        return
    
    # Download voice file
    file = await context.bot.get_file(voice.file_id)
    file_bytes = await file.download_as_bytearray()
    
    # Transcribe
    text = await transcribe_voice(bytes(file_bytes))
    if not text:
        await update.message.reply_text(t(lang, "voice_no_key"))
        return
    
    # Parse transcription
    parsed = parse_one(text)
    if not parsed:
        await update.message.reply_text(
            f"🎙 _{text}_\n\n{t(lang, 'not_understood')}",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    cat, amount, desc = parsed
    draft_id = uuid.uuid4().hex[:8]
    
    draft = Draft(
        tx_type="expense",
        category_key=normalize_category(cat),
        amount=amount,
        description=desc,
        source="voice"
    )
    DRAFTS[(tg_id, draft_id)] = draft
    
    await update.message.reply_text(
        format_draft(lang, draft, raw_text=text),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb_draft_confirm(lang, draft_id)
    )


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    """Start the bot"""
    print("🚀 Starting Hamyon Bot...")
    
    app = Application.builder().token(TOKEN).build()
    
    # Commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("stats", cmd_stats))
    
    # Callbacks
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    # Messages
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    print("✅ Bot is running!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
