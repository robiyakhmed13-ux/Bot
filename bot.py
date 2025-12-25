import os
import re
import httpx
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    WebAppInfo,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

from nlp import parse_quick_add

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = (os.getenv("API_URL") or "").rstrip("/")          # e.g. https://your-api.up.railway.app
API_SECRET = os.getenv("API_SECRET", "")
WEBAPP_URL = os.getenv("WEBAPP_URL", "")                    # your mini app URL
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")           # optional

if not TOKEN:
    raise ValueError("Missing TELEGRAM_BOT_TOKEN")
if not API_URL:
    raise ValueError("Missing API_URL")

# -----------------------------
# Menu labels (Uzbek)
# -----------------------------
BTN_APP = "📱 Ilova"
BTN_EXPENSE = "➖ Xarajat"
BTN_INCOME = "➕ Daromad"
BTN_DEBT = "📄 Qarz"
BTN_REPORTS = "📊 Hisobot"
BTN_SETTINGS = "⚙️ Sozlama"
BTN_CANCEL = "❌ Bekor qilish"

BTN_TODAY = "📅 Bugun"
BTN_7 = "🗓 7 kun"
BTN_30 = "🗓 30 kun"
BTN_CSV = "⬇️ CSV"

# Categories (label -> key)
CATS_EXPENSE = [
    ("🍕 Oziq-ovqat", "food"),
    ("🚕 Transport", "transport"),
    ("🏠 Uy", "home"),
    ("🧾 Kommunal", "bills"),
    ("💊 Dori", "health"),
    ("🛍 Xarid", "shopping"),
    ("🎁 Sovg'a", "gift"),
    ("📚 Ta'lim", "education"),
    ("🎬 Ko'ngilochar", "fun"),
    ("📌 Boshqa", "other"),
]

CATS_INCOME = [
    ("💼 Ish haqi", "salary"),
    ("🧾 Bonus", "bonus"),
    ("🎁 Sovg'a", "gift"),
    ("📌 Boshqa", "other"),
]

# Conversation states
CHOOSE_TYPE, CHOOSE_CAT, ENTER_AMOUNT, ENTER_DESC = range(4)

# -----------------------------
# Keyboards
# -----------------------------
def main_kb():
    rows = []

    if WEBAPP_URL:
        rows.append([KeyboardButton(BTN_APP, web_app=WebAppInfo(url=WEBAPP_URL))])

    rows += [
        [KeyboardButton(BTN_EXPENSE), KeyboardButton(BTN_INCOME)],
        [KeyboardButton(BTN_REPORTS), KeyboardButton(BTN_DEBT)],
        [KeyboardButton(BTN_SETTINGS)],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

def cancel_kb():
    return ReplyKeyboardMarkup([[KeyboardButton(BTN_CANCEL)]], resize_keyboard=True)

def categories_kb(cat_list):
    rows = []
    row = []
    for label, _key in cat_list:
        row.append(KeyboardButton(label))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([KeyboardButton(BTN_CANCEL)])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

def reports_kb():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(BTN_TODAY), KeyboardButton(BTN_7)],
            [KeyboardButton(BTN_30), KeyboardButton(BTN_CSV)],
            [KeyboardButton(BTN_CANCEL)],
        ],
        resize_keyboard=True,
    )

# -----------------------------
# API helpers
# -----------------------------
async def api_post(path: str, payload: dict):
    headers = {"X-API-SECRET": API_SECRET} if API_SECRET else {}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{API_URL}{path}", json=payload, headers=headers)
        r.raise_for_status()
        return r.json()

async def api_get_json(path: str, params: dict):
    headers = {"X-API-SECRET": API_SECRET} if API_SECRET else {}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{API_URL}{path}", params=params, headers=headers)
        r.raise_for_status()
        return r.json()

async def api_get_bytes(path: str, params: dict) -> bytes:
    headers = {"X-API-SECRET": API_SECRET} if API_SECRET else {}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{API_URL}{path}", params=params, headers=headers)
        r.raise_for_status()
        return r.content

# -----------------------------
# Utilities
# -----------------------------
def find_cat_key_by_label(label: str, cat_list):
    for l, k in cat_list:
        if l == label:
            return k
    return None

def parse_amount(text: str) -> int | None:
    # allow: "90 000", "90000", "90k" not included, keep simple
    digits = re.sub(r"[^\d]", "", text or "")
    if not digits:
        return None
    try:
        return int(digits)
    except Exception:
        return None

# -----------------------------
# Start / Menu
# -----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ Hamyon bot ishlayapti.\n\n"
        "Tez yozish ham mumkin:\n"
        "— `food 97500 lunch`\n"
        "— `transport 12000 taxi`\n\n"
        "Pastdagi tugmalar orqali foydalaning 👇",
        reply_markup=main_kb(),
        parse_mode="Markdown",
    )

# -----------------------------
# Conversation: Add transaction
# -----------------------------
async def add_expense_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["tx_type"] = "expense"
    await update.message.reply_text("Xarajat kategoriyasini tanlang:", reply_markup=categories_kb(CATS_EXPENSE))
    return CHOOSE_CAT

async def add_income_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["tx_type"] = "income"
    await update.message.reply_text("Daromad turini tanlang:", reply_markup=categories_kb(CATS_INCOME))
    return CHOOSE_CAT

async def choose_cat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (update.message.text or "").strip()
    if txt == BTN_CANCEL:
        await update.message.reply_text("Bekor qilindi ✅", reply_markup=main_kb())
        return ConversationHandler.END

    tx_type = context.user_data.get("tx_type", "expense")
    cat_list = CATS_EXPENSE if tx_type == "expense" else CATS_INCOME
    cat_key = find_cat_key_by_label(txt, cat_list)
    if not cat_key:
        await update.message.reply_text("Iltimos, tugmalardan birini tanlang 👇", reply_markup=categories_kb(cat_list))
        return CHOOSE_CAT

    context.user_data["category_key"] = cat_key
    await update.message.reply_text("Summani kiriting (masalan: 90000):", reply_markup=cancel_kb())
    return ENTER_AMOUNT

async def enter_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (update.message.text or "").strip()
    if txt == BTN_CANCEL:
        await update.message.reply_text("Bekor qilindi ✅", reply_markup=main_kb())
        return ConversationHandler.END

    amount = parse_amount(txt)
    if amount is None or amount <= 0:
        await update.message.reply_text("Summa noto‘g‘ri. Masalan: 90000", reply_markup=cancel_kb())
        return ENTER_AMOUNT

    context.user_data["amount"] = amount
    await update.message.reply_text("Izoh (ixtiyoriy). Yozing yoki '0' deb yuboring:", reply_markup=cancel_kb())
    return ENTER_DESC

async def enter_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (update.message.text or "").strip()
    if txt == BTN_CANCEL:
        await update.message.reply_text("Bekor qilindi ✅", reply_markup=main_kb())
        return ConversationHandler.END

    desc = None if txt in ("0", "-", "yo‘q", "yoq", "нет", "no") else txt

    tg_id = update.effective_user.id
    payload = {
        "telegram_id": tg_id,                         # keep required ✅
        "type": context.user_data.get("tx_type", "expense"),
        "amount": context.user_data["amount"],
        "category_key": context.user_data["category_key"],
        "description": desc,
        "source": "menu",
    }

    await api_post("/transactions", payload)
    await update.message.reply_text("✅ Saqlandi!", reply_markup=main_kb())
    return ConversationHandler.END

async def cancel_any(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bekor qilindi ✅", reply_markup=main_kb())
    return ConversationHandler.END

# -----------------------------
# Reports flow
# -----------------------------
async def reports_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Qaysi hisobot kerak?", reply_markup=reports_kb())
    return CHOOSE_TYPE

async def reports_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (update.message.text or "").strip()
    if txt == BTN_CANCEL:
        await update.message.reply_text("✅", reply_markup=main_kb())
        return ConversationHandler.END

    tg_id = update.effective_user.id

    if txt == BTN_TODAY:
        d = await api_get_json("/stats/today", {"telegram_id": tg_id})
        msg = (
            f"📊 Bugun:\n"
            f"➖ Xarajat: {d['expense']} UZS\n"
            f"➕ Daromad: {d['income']} UZS\n"
            f"📄 Qarz: {d['debt']} UZS\n"
            f"🔢 Tranzaksiya: {d['count']}"
        )
        await update.message.reply_text(msg, reply_markup=reports_kb())
        return CHOOSE_TYPE

    if txt in (BTN_7, BTN_30):
        days = 7 if txt == BTN_7 else 30
        d = await api_get_json("/stats/range", {"telegram_id": tg_id, "days": days})
        msg = (
            f"📆 {days} kun:\n"
            f"➖ Xarajat: {d['expense']} UZS\n"
            f"➕ Daromad: {d['income']} UZS\n"
            f"📄 Qarz: {d['debt']} UZS"
        )
        await update.message.reply_text(msg, reply_markup=reports_kb())
        return CHOOSE_TYPE

    if txt == BTN_CSV:
        content = await api_get_bytes("/export/csv", {"telegram_id": tg_id})
        await update.message.reply_document(
            document=content,
            filename="transactions.csv",
            caption="⬇️ CSV export",
        )
        await update.message.reply_text("Yana hisobot?", reply_markup=reports_kb())
        return CHOOSE_TYPE

    await update.message.reply_text("Iltimos, tugmalardan tanlang 👇", reply_markup=reports_kb())
    return CHOOSE_TYPE

# -----------------------------
# Free text quick add (NLP)
# Works when user types: "food 97500 lunch"
# -----------------------------
async def on_text_quick_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if text in (BTN_EXPENSE, BTN_INCOME, BTN_REPORTS, BTN_DEBT, BTN_SETTINGS, BTN_APP, BTN_CANCEL):
        return

    parsed = parse_quick_add(text)
    if not parsed:
        return

    cat, amount, desc = parsed
    tg_id = update.effective_user.id

    await api_post("/transactions", {
        "telegram_id": tg_id,
        "type": "expense",
        "amount": amount,
        "category_key": cat,
        "description": desc,
        "source": "text",
    })
    await update.message.reply_text("✅ Saqlandi!", reply_markup=main_kb())

# -----------------------------
# Voice -> text (optional)
# -----------------------------
async def transcribe_voice(file_bytes: bytes) -> str | None:
    if not OPENAI_API_KEY:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        resp = client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=("voice.ogg", file_bytes),
        )
        return resp.text
    except Exception:
        return None

async def on_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    voice = update.message.voice
    if not voice:
        return

    f = await context.bot.get_file(voice.file_id)
    b = await f.download_as_bytearray()

    text = await transcribe_voice(bytes(b))
    if not text:
        await update.message.reply_text("🎙 Ovozni o‘qish uchun OPENAI_API_KEY kerak.", reply_markup=main_kb())
        return

    parsed = parse_quick_add(text)
    if not parsed:
        await update.message.reply_text(f"🎙 Matn: {text}\n\n❌ Tushunmadim. Misol: 'food 97500'", reply_markup=main_kb())
        return

    cat, amount, desc = parsed
    tg_id = update.effective_user.id

    await api_post("/transactions", {
        "telegram_id": tg_id,
        "type": "expense",
        "amount": amount,
        "category_key": cat,
        "description": desc or f"(voice) {text}",
        "source": "voice",
    })
    await update.message.reply_text(f"🎙 {text}\n✅ Saqlandi!", reply_markup=main_kb())

# -----------------------------
# Router for menu buttons
# -----------------------------
async def menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (update.message.text or "").strip()

    if txt == BTN_EXPENSE:
        return await add_expense_entry(update, context)
    if txt == BTN_INCOME:
        return await add_income_entry(update, context)
    if txt == BTN_REPORTS:
        return await reports_entry(update, context)

    if txt == BTN_SETTINGS:
        await update.message.reply_text("⚙️ Sozlama (keyin qo‘shamiz).", reply_markup=main_kb())
        return ConversationHandler.END

    if txt == BTN_DEBT:
        await update.message.reply_text("📄 Qarz (keyin qo‘shamiz).", reply_markup=main_kb())
        return ConversationHandler.END

    if txt == BTN_CANCEL:
        await update.message.reply_text("✅", reply_markup=main_kb())
        return ConversationHandler.END

    # if not a menu button, try quick add
    await on_text_quick_add(update, context)
    return ConversationHandler.END

# -----------------------------
# App bootstrap
# -----------------------------
def build_app() -> Application:
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    # Add/Report are handled via one conversation for “menu feeling”
    conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.TEXT & ~filters.COMMAND, menu_router),
        ],
        states={
            CHOOSE_CAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_cat)],
            ENTER_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_amount)],
            ENTER_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_desc)],

            # reuse CHOOSE_TYPE for reports menu selection
            CHOOSE_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, reports_choice)],
        },
        fallbacks=[MessageHandler(filters.Regex(f"^{re.escape(BTN_CANCEL)}$"), cancel_any)],
        allow_reentry=True,
    )
    app.add_handler(conv)

    app.add_handler(MessageHandler(filters.VOICE, on_voice))

    return app

if __name__ == "__main__":
    application = build_app()
    # IMPORTANT: no asyncio.run, no await here ✅
    application.run_polling(drop_pending_updates=True)
