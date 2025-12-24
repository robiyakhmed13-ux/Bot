"""
HAMYON - Telegram Bot (Python)
Matches Supabase schema: users, transactions, limits, goals, debts
"""

import os, re, json, logging, io, csv
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List
from dataclasses import dataclass
from enum import Enum

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# ✅ Logging must be configured BEFORE using logger
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")

# ✅ Prefer backend secret key; fall back only if needed
SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    or os.getenv("SUPABASE_SECRET_KEY")
    or os.getenv("SUPABASE_ANON_KEY", "")
)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://your-app.vercel.app")

if not BOT_TOKEN:
    raise ValueError("Missing TELEGRAM_BOT_TOKEN")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing Supabase credentials")

# ✅ Safe debug: prints only prefix
logger.info("Supabase key prefix in use: %s", (SUPABASE_KEY or "")[:12])

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

openai_client = None
if OPENAI_API_KEY:
    try:
        import openai
        openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
    except Exception:
        pass


class TxType(Enum):
    EXPENSE = "expense"
    INCOME = "income"
    DEBT = "debt"


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
class PendingTx:
    category_id: str
    tx_type: TxType


@dataclass
class PendingDebt:
    debt_type: str
    person_name: Optional[str] = None


user_pending: Dict[int, PendingTx] = {}
user_pending_debt: Dict[int, PendingDebt] = {}
user_pending_goal: Dict[int, str] = {}

CATEGORIES = {
    "food": Category("food", "Oziq-ovqat", "Продукты", "Food", "🍕", ["food", "oziq", "ovqat", "grocery", "продукты", "magazin"], TxType.EXPENSE),
    "restaurants": Category("restaurants", "Restoranlar", "Рестораны", "Restaurants", "🍽️", ["restaurant", "restoran", "cafe", "ресторан", "oshxona"], TxType.EXPENSE),
    "coffee": Category("coffee", "Kofe", "Кофе", "Coffee", "☕", ["coffee", "kofe", "кофе", "starbucks"], TxType.EXPENSE),
    "taxi": Category("taxi", "Taksi", "Такси", "Taxi", "🚕", ["taxi", "taksi", "yandex", "uber", "bolt", "mytaxi"], TxType.EXPENSE),
    "fuel": Category("fuel", "Benzin", "Бензин", "Fuel", "⛽", ["fuel", "benzin", "petrol", "бензин", "zapravka"], TxType.EXPENSE),
    "transport": Category("transport", "Transport", "Транспорт", "Transport", "🚌", ["transport", "bus", "avtobus", "metro", "marshrutka"], TxType.EXPENSE),
    "bills": Category("bills", "Kommunal", "Коммунальные", "Bills", "💡", ["bills", "kommunal", "electric", "коммунальные", "свет", "газ"], TxType.EXPENSE),
    "rent": Category("rent", "Ijara", "Аренда", "Rent", "🏠", ["rent", "ijara", "kvartira", "аренда"], TxType.EXPENSE),
    "shopping": Category("shopping", "Xaridlar", "Покупки", "Shopping", "🛍️", ["shopping", "xarid", "buy", "покупки"], TxType.EXPENSE),
    "clothing": Category("clothing", "Kiyim", "Одежда", "Clothing", "👕", ["clothing", "kiyim", "clothes", "одежда"], TxType.EXPENSE),
    "health": Category("health", "Salomatlik", "Здоровье", "Health", "💊", ["health", "salomatlik", "medicine", "doctor", "здоровье", "dorixona"], TxType.EXPENSE),
    "beauty": Category("beauty", "Go'zallik", "Красота", "Beauty", "💄", ["beauty", "salon", "haircut", "sartarosh", "красота"], TxType.EXPENSE),
    "education": Category("education", "Ta'lim", "Образование", "Education", "📚", ["education", "talim", "course", "kurs", "kitob", "образование"], TxType.EXPENSE),
    "entertainment": Category("entertainment", "Ko'ngilochar", "Развлечения", "Entertainment", "🎬", ["entertainment", "movie", "kino", "развлечения"], TxType.EXPENSE),
    "sports": Category("sports", "Sport", "Спорт", "Sports", "🏃", ["sports", "sport", "gym", "fitness", "спорт"], TxType.EXPENSE),
    "travel": Category("travel", "Sayohat", "Путешествия", "Travel", "✈️", ["travel", "sayohat", "trip", "путешествие"], TxType.EXPENSE),
    "electronics": Category("electronics", "Elektronika", "Электроника", "Electronics", "📱", ["electronics", "phone", "telefon", "laptop", "электроника"], TxType.EXPENSE),
    "gifts": Category("gifts", "Sovg'alar", "Подарки", "Gifts", "🎁", ["gift", "sovga", "present", "подарок"], TxType.EXPENSE),
    "subscriptions": Category("subscriptions", "Obunalar", "Подписки", "Subscriptions", "📺", ["subscription", "netflix", "spotify", "подписка"], TxType.EXPENSE),
    "other_expense": Category("other_expense", "Boshqa", "Другое", "Other", "📦", ["other", "boshqa", "другое"], TxType.EXPENSE),
    "salary": Category("salary", "Oylik", "Зарплата", "Salary", "💰", ["salary", "oylik", "maosh", "зарплата"], TxType.INCOME),
    "freelance": Category("freelance", "Frilanser", "Фриланс", "Freelance", "💻", ["freelance", "frilanser", "фриланс", "project"], TxType.INCOME),
    "business": Category("business", "Biznes", "Бизнес", "Business", "🏢", ["business", "biznes", "бизнес", "savdo"], TxType.INCOME),
    "bonus": Category("bonus", "Bonus", "Бонус", "Bonus", "🎉", ["bonus", "mukofot", "бонус", "премия"], TxType.INCOME),
    "refund": Category("refund", "Qaytarish", "Возврат", "Refund", "↩️", ["refund", "qaytarish", "возврат"], TxType.INCOME),
    "other_income": Category("other_income", "Boshqa", "Другое", "Other", "💵", ["income", "daromad", "доход"], TxType.INCOME),
    "borrowed": Category("borrowed", "Qarz oldim", "Взял в долг", "Borrowed", "🤝", ["borrowed", "qarz oldim", "занял"], TxType.DEBT),
    "lent": Category("lent", "Qarz berdim", "Дал в долг", "Lent", "💸", ["lent", "qarz berdim", "дал в долг"], TxType.DEBT),
}

TR = {
    "uz": {"welcome": "👋 Salom! Hamyon botga xush kelibsiz!\n\n✅ Kategoriya tanlang yoki \"Taksi 30k\" yozing\n📱 Ilovani oching!",
           "balance": "💰 Balans", "today": "📅 Bugun", "exp": "↘️ Xarajat", "inc": "↗️ Daromad",
           "sel_exp": "🧾 Xarajat:", "sel_inc": "💰 Daromad:", "enter_amt": "✅ {e} {n}\n\nSumma yuboring:",
           "saved": "✅ {e} {n}\n{i} {a}\n💰 {b}", "cant": "❌ Summa aniqlanmadi", "back": "◀️ Orqaga", "cancel": "❌ Bekor",
           "open": "📱 Ilova", "add_exp": "➖ Xarajat", "add_inc": "➕ Daromad", "goals": "🎯 Maqsad", "debts": "📋 Qarz",
           "reports": "📊 Hisobot", "settings": "⚙️ Sozlama", "no_goals": "🎯 Maqsad yo'q", "no_debts": "📋 Qarz yo'q",
           "export": "📥 Eksport", "limit_warn": "⚠️ {e} {n}: {s}/{l} ({p}%)"},
    "ru": {"welcome": "👋 Привет! Добро пожаловать!\n\n✅ Выберите категорию или напишите \"Такси 30k\"\n📱 Откройте приложение!",
           "balance": "💰 Баланс", "today": "📅 Сегодня", "exp": "↘️ Расход", "inc": "↗️ Доход",
           "sel_exp": "🧾 Расход:", "sel_inc": "💰 Доход:", "enter_amt": "✅ {e} {n}\n\nОтправьте сумму:",
           "saved": "✅ {e} {n}\n{i} {a}\n💰 {b}", "cant": "❌ Не понял сумму", "back": "◀️ Назад", "cancel": "❌ Отмена",
           "open": "📱 Открыть", "add_exp": "➖ Расход", "add_inc": "➕ Доход", "goals": "🎯 Цели", "debts": "📋 Долги",
           "reports": "📊 Отчёт", "settings": "⚙️ Настройки", "no_goals": "🎯 Целей нет", "no_debts": "📋 Долгов нет",
           "export": "📥 Экспорт", "limit_warn": "⚠️ {e} {n}: {s}/{l} ({p}%)"},
    "en": {"welcome": "👋 Hello! Welcome to Hamyon!\n\n✅ Select category or type \"Taxi 30k\"\n📱 Open the app!",
           "balance": "💰 Balance", "today": "📅 Today", "exp": "↘️ Expense", "inc": "↗️ Income",
           "sel_exp": "🧾 Expense:", "sel_inc": "💰 Income:", "enter_amt": "✅ {e} {n}\n\nSend amount:",
           "saved": "✅ {e} {n}\n{i} {a}\n💰 {b}", "cant": "❌ Couldn't parse", "back": "◀️ Back", "cancel": "❌ Cancel",
           "open": "📱 Open App", "add_exp": "➖ Expense", "add_inc": "➕ Income", "goals": "🎯 Goals", "debts": "📋 Debts",
           "reports": "📊 Reports", "settings": "⚙️ Settings", "no_goals": "🎯 No goals", "no_debts": "📋 No debts",
           "export": "📥 Export", "limit_warn": "⚠️ {e} {n}: {s}/{l} ({p}%)"}
}

def t(l, k): return TR.get(l, TR["uz"]).get(k, k)
def cn(c, l): return c.name_ru if l == "ru" else c.name_en if l == "en" else c.name_uz

def parse_amt(txt):
    txt = txt.lower()
    m = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:mln|million|млн|m(?!ing))\b', txt, re.I)
    if m: return int(float(m.group(1).replace(",", ".")) * 1_000_000)
    m = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:k|к|ming|тысяч)\b', txt, re.I)
    if m: return int(float(m.group(1).replace(",", ".")) * 1_000)
    m = re.search(r'(\d{1,3}(?:[,\s]\d{3})+)', txt)
    if m: return int(re.sub(r'[,\s]', '', m.group(1)))
    m = re.search(r'(\d+)', txt)
    if m and int(m.group(1)) >= 100: return int(m.group(1))
    return None

def fmt(a): return f"{a/1_000_000:.1f}".replace(".0", "")+"M" if abs(a) >= 1_000_000 else f"{a:,}".replace(",", " ")+" UZS"

def detect(txt):
    txt = txt.lower()
    for cid, c in CATEGORIES.items():
        if c.tx_type == TxType.INCOME and any(k in txt for k in c.keywords): return cid, TxType.INCOME
    for cid, c in CATEGORIES.items():
        if c.tx_type == TxType.EXPENSE and any(k in txt for k in c.keywords): return cid, TxType.EXPENSE
    return "other_expense", TxType.EXPENSE

async def get_lang(uid):
    try:
        r = supabase.table("users").select("language").eq("telegram_id", uid).maybe_single().execute()
        return r.data.get("language", "uz") if r.data else "uz"
    except Exception:
        return "uz"

async def ensure_user(uid, name):
    try:
        r = supabase.table("users").select("*").eq("telegram_id", uid).maybe_single().execute()
        if r.data: return r.data
        n = supabase.table("users").insert({"telegram_id": uid, "name": name, "balance": 0, "language": "uz"}).execute()
        return n.data[0] if n.data else {"telegram_id": uid, "balance": 0, "language": "uz"}
    except Exception:
        return {"telegram_id": uid, "balance": 0, "language": "uz"}

async def get_bal(uid):
    try:
        r = supabase.table("users").select("balance").eq("telegram_id", uid).single().execute()
        return int(r.data.get("balance", 0)) if r.data else 0
    except Exception:
        return 0

async def save_tx(uid, desc, amt, cid, src="text"):
    try:
        supabase.table("transactions").insert({
            "user_telegram_id": uid,
            "description": desc,
            "amount": amt,
            "category_id": cid,
            "source": src
        }).execute()

        try:
            supabase.rpc("update_balance", {"p_telegram_id": uid, "p_amount": amt}).execute()
        except Exception:
            bal = await get_bal(uid)
            supabase.table("users").update({"balance": bal + amt}).eq("telegram_id", uid).execute()

        return True
    except Exception as e:
        logger.error(f"save_tx:{e}")
        return False

async def today_stats(uid):
    try:
        r = supabase.rpc("get_today_stats", {"p_telegram_id": uid}).execute()
        if r.data:
            row = r.data[0] if isinstance(r.data, list) else r.data
            return {
                "e": abs(int(row.get("total_expenses", 0))),
                "i": int(row.get("total_income", 0)),
                "c": int(row.get("transaction_count", 0))
            }
    except Exception:
        pass
    return {"e": 0, "i": 0, "c": 0}

async def period_stats(uid, days):
    try:
        # ✅ Use UTC to match Supabase timestamptz better
        start = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        r = supabase.table("transactions").select("amount,category_id").eq("user_telegram_id", uid).gte("created_at", start).execute()
        e, i, bc = 0, 0, {}
        for tx in (r.data or []):
            a = int(tx.get("amount", 0))
            c = tx.get("category_id", "other")
            if a < 0:
                e += abs(a)
                bc[c] = bc.get(c, 0) + abs(a)
            else:
                i += a
        return {"e": e, "i": i, "c": len(r.data or []), "bc": bc}
    except Exception:
        return {"e": 0, "i": 0, "c": 0, "bc": {}}

async def get_limit(uid, cid):
    try:
        r = supabase.table("limits").select("*").eq("user_telegram_id", uid).eq("category_id", cid).eq("is_active", True).maybe_single().execute()
        return r.data
    except Exception:
        return None

async def month_spent(uid, cid):
    try:
        r = supabase.rpc("get_category_spending", {"p_telegram_id": uid, "p_category_id": cid}).execute()
        return int(r.data) if r.data else 0
    except Exception:
        return 0

async def get_goals(uid):
    try:
        r = supabase.table("goals").select("*").eq("user_telegram_id", uid).eq("is_completed", False).execute()
        return r.data or []
    except Exception:
        return []

async def get_debts(uid):
    try:
        r = supabase.table("debts").select("*").eq("user_telegram_id", uid).eq("is_settled", False).execute()
        return r.data or []
    except Exception:
        return []

async def save_debt(uid, person, amt, dtype):
    try:
        supabase.table("debts").insert({"user_telegram_id": uid, "person_name": person, "amount": amt, "type": dtype}).execute()
        return True
    except Exception:
        return False

async def update_lang(uid, lang):
    try:
        supabase.table("users").update({"language": lang}).eq("telegram_id", uid).execute()
    except Exception:
        pass

async def export_csv(uid, days=30):
    try:
        start = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        r = supabase.table("transactions").select("*").eq("user_telegram_id", uid).gte("created_at", start).order("created_at", desc=True).execute()
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(["Date", "Description", "Amount", "Category", "Source"])
        for tx in (r.data or []):
            c = CATEGORIES.get(tx.get("category_id", ""))
            w.writerow([tx.get("created_at", "")[:10], tx.get("description", ""), tx.get("amount", 0), c.name_uz if c else "", tx.get("source", "")])
        return out.getvalue()
    except Exception:
        return ""

def main_kb(l):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t(l, "open"), web_app=WebAppInfo(url=WEBAPP_URL))],
        [InlineKeyboardButton(t(l, "add_exp"), callback_data="m:exp"), InlineKeyboardButton(t(l, "add_inc"), callback_data="m:inc")],
        [InlineKeyboardButton(t(l, "goals"), callback_data="m:goals"), InlineKeyboardButton(t(l, "debts"), callback_data="m:debts")],
        [InlineKeyboardButton(t(l, "reports"), callback_data="m:rep"), InlineKeyboardButton(t(l, "settings"), callback_data="m:set")]
    ])

def cat_kb(tx_type, l):
    btns, row = [], []
    for cid, c in CATEGORIES.items():
        if c.tx_type == tx_type:
            row.append(InlineKeyboardButton(f"{c.emoji} {cn(c, l)[:8]}", callback_data=f"c:{tx_type.value}:{cid}"))
            if len(row) == 2:
                btns.append(row)
                row = []
    if row: btns.append(row)
    btns.append([InlineKeyboardButton(t(l, "cancel"), callback_data="cancel")])
    return InlineKeyboardMarkup(btns)

def rep_kb(l):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 1 day", callback_data="r:1"), InlineKeyboardButton("📆 7 days", callback_data="r:7")],
        [InlineKeyboardButton("🗓 30 days", callback_data="r:30"), InlineKeyboardButton("📥 CSV", callback_data="export")],
        [InlineKeyboardButton(t(l, "back"), callback_data="back")]
    ])

def set_kb(l):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇺🇿 O'zbek", callback_data="l:uz"), InlineKeyboardButton("🇷🇺 Русский", callback_data="l:ru"), InlineKeyboardButton("🇬🇧 English", callback_data="l:en")],
        [InlineKeyboardButton(t(l, "back"), callback_data="back")]
    ])

async def start(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    usr = u.effective_user
    if not usr: return
    db = await ensure_user(usr.id, usr.first_name)
    l = db.get("language", "uz")
    await u.message.reply_text(t(l, "welcome"), reply_markup=main_kb(l))

async def balance_cmd(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    usr = u.effective_user
    if not usr: return
    l = await get_lang(usr.id)
    bal = await get_bal(usr.id)
    ts = await today_stats(usr.id)
    txt = f"{t(l,'balance')}: *{fmt(bal)}*\n\n{t(l,'today')}:\n{t(l,'exp')}: {fmt(ts['e'])}\n{t(l,'inc')}: {fmt(ts['i'])}\n🧾: {ts['c']}"
    await u.message.reply_text(txt, parse_mode="Markdown", reply_markup=main_kb(l))

async def cb(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = u.callback_query
    if not q: return
    await q.answer()
    usr = q.from_user
    d = q.data
    l = await get_lang(usr.id)

    if d == "cancel":
        user_pending.pop(usr.id, None); user_pending_debt.pop(usr.id, None)
        await q.edit_message_text(t(l, "cancel"), reply_markup=main_kb(l)); return
    if d == "back":
        bal = await get_bal(usr.id)
        await q.edit_message_text(f"{t(l,'balance')}: *{fmt(bal)}*", parse_mode="Markdown", reply_markup=main_kb(l)); return
    if d == "m:exp":
        await q.edit_message_text(t(l, "sel_exp"), reply_markup=cat_kb(TxType.EXPENSE, l)); return
    if d == "m:inc":
        await q.edit_message_text(t(l, "sel_inc"), reply_markup=cat_kb(TxType.INCOME, l)); return
    if d == "m:goals":
        goals = await get_goals(usr.id)
        if not goals:
            await q.edit_message_text(t(l, "no_goals"), reply_markup=main_kb(l))
        else:
            txt = "🎯 *Goals*\n"
            for g in goals[:5]:
                p = int((g.get("current_amount", 0) / max(g.get("target_amount", 1), 1)) * 100)
                txt += f"\n{g.get('emoji','🎯')} {g.get('name','')}: {p}%"
            await q.edit_message_text(txt, parse_mode="Markdown", reply_markup=main_kb(l))
        return
    if d == "m:debts":
        debts = await get_debts(usr.id)
        if not debts:
            await q.edit_message_text(t(l, "no_debts"), reply_markup=main_kb(l))
        else:
            txt = "📋 *Debts*\n"
            for db in debts[:5]:
                txt += f"\n{'🤝' if db.get('type')=='borrowed' else '💸'} {db.get('person_name','')}: {fmt(db.get('amount',0))}"
            await q.edit_message_text(txt, parse_mode="Markdown", reply_markup=main_kb(l))
        return
    if d == "m:rep":
        await q.edit_message_text(t(l, "reports"), reply_markup=rep_kb(l)); return
    if d == "m:set":
        await q.edit_message_text("🌐", reply_markup=set_kb(l)); return
    if d.startswith("c:"):
        _, ty, cid = d.split(":")
        user_pending[usr.id] = PendingTx(cid, TxType(ty))
        c = CATEGORIES.get(cid)
        if c:
            await q.edit_message_text(t(l, "enter_amt").format(e=c.emoji, n=cn(c, l)))
        return
    if d.startswith("l:"):
        nl = d.split(":")[1]
        await update_lang(usr.id, nl)
        await q.edit_message_text("✅", reply_markup=main_kb(nl)); return
    if d.startswith("r:"):
        days = int(d.split(":")[1])
        st = await period_stats(usr.id, days)
        cat_txt = ""
        for cid, amt in sorted(st["bc"].items(), key=lambda x: x[1], reverse=True)[:5]:
            c = CATEGORIES.get(cid)
            if c: cat_txt += f"\n{c.emoji} {cn(c, l)}: {fmt(amt)}"
        txt = f"📊 *{days} days*\n\n{t(l,'exp')}: {fmt(st['e'])}\n{t(l,'inc')}: {fmt(st['i'])}\n🧾: {st['c']}\n\n*Top:*{cat_txt or ' -'}"
        await q.edit_message_text(txt, parse_mode="Markdown", reply_markup=rep_kb(l)); return
    if d == "export":
        await q.edit_message_text("📥...")
        csv_data = await export_csv(usr.id, 30)
        if csv_data:
            f = io.BytesIO(csv_data.encode("utf-8"))
            f.name = f"hamyon_{datetime.now().strftime('%Y%m%d')}.csv"
            await ctx.bot.send_document(chat_id=usr.id, document=InputFile(f), caption=t(l, "export"))
        return

async def text_handler(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    usr = u.effective_user
    msg = u.message
    if not usr or not msg or not msg.text: return
    txt = msg.text.strip()
    if txt.startswith("/"): return
    l = await get_lang(usr.id)

    if usr.id in user_pending:
        pend = user_pending.pop(usr.id)
        amt = parse_amt(txt)
        if not amt:
            await msg.reply_text(t(l, "cant"))
            return
        final = -abs(amt) if pend.tx_type == TxType.EXPENSE else abs(amt)
        c = CATEGORIES.get(pend.category_id)
        if not c: return

        ok = await save_tx(usr.id, cn(c, l), final, pend.category_id, "manual")
        if not ok:
            await msg.reply_text("❌ Supabase insert failed (key/RLS).")
            return

        lim = await get_limit(usr.id, pend.category_id)
        if lim:
            spent = await month_spent(usr.id, pend.category_id)
            lim_amt = int(lim.get("limit_amount", 0))
            if lim_amt > 0:
                pct = int((spent / lim_amt) * 100)
                if pct >= int(lim.get("alert_threshold", 90)):
                    await msg.reply_text(t(l, "limit_warn").format(e=c.emoji, n=cn(c, l), s=fmt(spent), l=fmt(lim_amt), p=pct))

        bal = await get_bal(usr.id)
        await msg.reply_text(t(l, "saved").format(e=c.emoji, n=cn(c, l), i="💸" if final < 0 else "💰", a=fmt(abs(final)), b=fmt(bal)), reply_markup=main_kb(l))
        return

    amt = parse_amt(txt)
    if not amt:
        await msg.reply_text(t(l, "cant"), reply_markup=main_kb(l))
        return

    cid, ty = detect(txt)
    final = -abs(amt) if ty == TxType.EXPENSE else abs(amt)
    c = CATEGORIES.get(cid)

    ok = await save_tx(usr.id, txt, final, cid, "text")
    if not ok:
        await msg.reply_text("❌ Supabase insert failed (key/RLS).")
        return

    bal = await get_bal(usr.id)
    await msg.reply_text(t(l, "saved").format(e=c.emoji if c else "📦", n=cn(c, l) if c else cid, i="💸" if final < 0 else "💰", a=fmt(abs(final)), b=fmt(bal)), reply_markup=main_kb(l))

async def voice_handler(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    usr = u.effective_user
    msg = u.message
    if not usr or not msg: return
    l = await get_lang(usr.id)
    if not openai_client:
        await msg.reply_text("⚠️ Voice not available")
        return
    await msg.reply_text("🎤...")
    try:
        vf = await msg.voice.get_file()
        path = f"/tmp/v_{usr.id}.ogg"
        await vf.download_to_drive(path)
        with open(path, "rb") as f:
            resp = openai_client.audio.transcriptions.create(model="whisper-1", file=f)
        os.remove(path)
        txt = resp.text
        amt = parse_amt(txt)
        if not amt:
            await msg.reply_text(f"🎤 _{txt}_\n\n{t(l,'cant')}", parse_mode="Markdown")
            return
        cid, ty = detect(txt)
        final = -abs(amt) if ty == TxType.EXPENSE else abs(amt)
        c = CATEGORIES.get(cid)

        ok = await save_tx(usr.id, txt, final, cid, "voice")
        if not ok:
            await msg.reply_text("❌ Supabase insert failed (key/RLS).")
            return

        bal = await get_bal(usr.id)
        await msg.reply_text(
            f"🎤 _{txt}_\n\n" + t(l, "saved").format(
                e=c.emoji if c else "📦",
                n=cn(c, l) if c else cid,
                i="💸" if final < 0 else "💰",
                a=fmt(abs(final)),
                b=fmt(bal)
            ),
            parse_mode="Markdown",
            reply_markup=main_kb(l)
        )
    except Exception as e:
        logger.error(f"voice:{e}")
        await msg.reply_text("❌ Error")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", balance_cmd))
    app.add_handler(CallbackQueryHandler(cb))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(MessageHandler(filters.VOICE, voice_handler))
    logger.info("🚀 Hamyon Bot started!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
