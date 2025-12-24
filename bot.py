# bot.py — HAMYON Telegram Bot (WORKING VERSION for your current Supabase schema)
# Assumes Supabase tables:
# - users: telegram_id (bigint), name (text/varchar), balance (numeric/bigint), language (text/varchar)
# - transactions: user_telegram_id (bigint), type (varchar: expense/income/debt), amount (numeric),
#                 category (varchar), source (varchar), created_at (timestamptz default now)
#
# IMPORTANT:
# - Backend MUST use sb_secret_... key (service role) to avoid RLS problems.
# - Frontend uses sb_publishable_... key.

import os
import re
import io
import csv
import logging
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from supabase import create_client
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
    InputFile,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

load_dotenv()

# -----------------------
# Logging (MUST be first)
# -----------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("hamyon-bot")

# -----------------------
# ENV
# -----------------------
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()

# Prefer service-role key for bot
SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    or os.getenv("SUPABASE_SECRET_KEY", "").strip()
    or os.getenv("SUPABASE_ANON_KEY", "").strip()  # fallback only (not recommended)
)

WEBAPP_URL = os.getenv("WEBAPP_URL", "").strip()  # optional

if not BOT_TOKEN:
    raise ValueError("Missing TELEGRAM_BOT_TOKEN")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL / SUPABASE key")

logger.info("Supabase key prefix in use: %s", SUPABASE_KEY[:12])

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# -----------------------
# Simple i18n
# -----------------------
I18N = {
    "uz": {
        "welcome": "👋 Salom! Hamyon botga xush kelibsiz.\n\n✅ Kategoriya tanlang yoki masalan: `taksi 30k` yozing.",
        "cant_parse": "❌ Summani tushunmadim. Masalan: `97500` yoki `97.5k`",
        "saved": "✅ Saqlandi: {type}\n📂 {cat}\n💵 {amt}\n💰 Balans: {bal}",
        "reports": "📊 Hisobot",
        "export": "📥 CSV eksport",
        "back": "◀️ Orqaga",
    },
    "ru": {
        "welcome": "👋 Привет! Добро пожаловать в Hamyon.\n\n✅ Выберите категорию или напишите: `такси 30k`",
        "cant_parse": "❌ Не понял сумму. Пример: `97500` или `97.5k`",
        "saved": "✅ Сохранено: {type}\n📂 {cat}\n💵 {amt}\n💰 Баланс: {bal}",
        "reports": "📊 Отчёт",
        "export": "📥 Экспорт CSV",
        "back": "◀️ Назад",
    },
    "en": {
        "welcome": "👋 Hello! Welcome to Hamyon.\n\n✅ Select a category or type: `taxi 30k`",
        "cant_parse": "❌ Couldn't parse amount. Example: `97500` or `97.5k`",
        "saved": "✅ Saved: {type}\n📂 {cat}\n💵 {amt}\n💰 Balance: {bal}",
        "reports": "📊 Reports",
        "export": "📥 Export CSV",
        "back": "◀️ Back",
    },
}

def t(lang: str, key: str) -> str:
    return I18N.get(lang, I18N["uz"]).get(key, key)

def format_uzs(x: int) -> str:
    return f"{x:,}".replace(",", " ") + " UZS"

# -----------------------
# Categories (match your DB column 'category' as string)
# -----------------------
EXPENSE_CATS = [
    ("food", "🍕 Oziq-ovqat"),
    ("restaurants", "🍽️ Restoran"),
    ("coffee", "☕ Kofe"),
    ("taxi", "🚕 Taksi"),
    ("transport", "🚌 Transport"),
    ("bills", "💡 Kommunal"),
    ("shopping", "🛍️ Xaridlar"),
    ("health", "💊 Salomatlik"),
    ("education", "📚 Ta'lim"),
    ("other", "📦 Boshqa"),
]
INCOME_CATS = [
    ("salary", "💰 Oylik"),
    ("freelance", "💻 Frilanser"),
    ("bonus", "🎉 Bonus"),
    ("other_income", "💵 Boshqa"),
]

# -----------------------
# Per-user pending state
# -----------------------
pending = {}  # telegram_id -> {"type": "expense"/"income"/"debt", "category": "taxi"}

def parse_amount(text: str) -> int | None:
    """
    Accepts:
      97500
      97.5k, 97k, 97 ming
      1.2m, 1 mln
    Returns int UZS.
    """
    s = text.strip().lower()
    s = s.replace("сум", "").replace("uzs", "").strip()

    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(mln|million|млн|m)\b", s)
    if m:
        return int(float(m.group(1).replace(",", ".")) * 1_000_000)

    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(k|к|ming|тыс)\b", s)
    if m:
        return int(float(m.group(1).replace(",", ".")) * 1_000)

    m = re.search(r"(\d{1,3}(?:[,\s]\d{3})+)", s)
    if m:
        return int(re.sub(r"[,\s]", "", m.group(1)))

    m = re.search(r"(\d+)", s)
    if m:
        v = int(m.group(1))
        return v if v >= 1 else None

    return None

def detect_category_and_type(text: str) -> tuple[str, str]:
    """
    Very simple keyword detection. Defaults to expense/other.
    """
    s = text.lower()
    # Income hints
    if any(k in s for k in ["salary", "oylik", "maosh", "зарп", "income", "daromad"]):
        return ("salary", "income")
    # Taxi hints
    if any(k in s for k in ["taxi", "taksi", "yandex", "uber", "bolt"]):
        return ("taxi", "expense")
    # Food hints
    if any(k in s for k in ["food", "ovqat", "oziq", "grocery", "magazin", "продукт"]):
        return ("food", "expense")

    return ("other", "expense")

# -----------------------
# DB helpers
# -----------------------
async def get_user_lang(telegram_id: int) -> str:
    try:
        r = supabase.table("users").select("language").eq("telegram_id", telegram_id).maybe_single().execute()
        if r.data and r.data.get("language"):
            return r.data["language"]
    except Exception:
        pass
    return "uz"

async def ensure_user(telegram_id: int, name: str) -> None:
    try:
        r = supabase.table("users").select("telegram_id").eq("telegram_id", telegram_id).maybe_single().execute()
        if r.data:
            return
        supabase.table("users").insert(
            {"telegram_id": telegram_id, "name": name, "balance": 0, "language": "uz"}
        ).execute()
    except Exception as e:
        logger.exception("ensure_user failed: %s", str(e))

async def get_balance(telegram_id: int) -> int:
    try:
        r = supabase.table("users").select("balance").eq("telegram_id", telegram_id).maybe_single().execute()
        if r.data and r.data.get("balance") is not None:
            return int(r.data["balance"])
    except Exception:
        pass
    return 0

async def set_balance_delta(telegram_id: int, delta: int) -> None:
    """
    No RPC. Just update balance = balance + delta.
    """
    try:
        current = await get_balance(telegram_id)
        supabase.table("users").update({"balance": current + int(delta)}).eq("telegram_id", telegram_id).execute()
    except Exception as e:
        logger.exception("set_balance_delta failed: %s", str(e))

async def insert_transaction(telegram_id: int, tx_type: str, amount_abs: int, category: str, source: str) -> bool:
    """
    Inserts row into YOUR CURRENT transactions table:
      user_telegram_id, type, amount, category, source
    """
    try:
        supabase.table("transactions").insert({
            "user_telegram_id": telegram_id,
            "type": tx_type,              # expense/income/debt
            "amount": int(amount_abs),    # positive
            "category": category,         # string
            "source": source
        }).execute()
        return True
    except Exception as e:
        logger.exception("insert_transaction failed: %s", str(e))
        return False

async def today_stats(telegram_id: int) -> dict:
    """
    Computes stats directly from transactions.
    Uses UTC day start to avoid timezone confusion.
    """
    try:
        start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        r = (
            supabase.table("transactions")
            .select("amount,type")
            .eq("user_telegram_id", telegram_id)
            .gte("created_at", start)
            .execute()
        )
        exp = inc = 0
        for row in (r.data or []):
            a = int(row.get("amount", 0) or 0)
            ty = (row.get("type") or "").lower()
            if ty == "expense":
                exp += a
            elif ty == "income":
                inc += a
        return {"expense": exp, "income": inc, "count": len(r.data or [])}
    except Exception as e:
        logger.exception("today_stats failed: %s", str(e))
        return {"expense": 0, "income": 0, "count": 0}

async def period_stats(telegram_id: int, days: int) -> dict:
    try:
        start = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        r = (
            supabase.table("transactions")
            .select("amount,type,category")
            .eq("user_telegram_id", telegram_id)
            .gte("created_at", start)
            .execute()
        )
        exp = inc = 0
        top = {}
        for row in (r.data or []):
            a = int(row.get("amount", 0) or 0)
            ty = (row.get("type") or "").lower()
            cat = row.get("category") or "other"
            if ty == "expense":
                exp += a
                top[cat] = top.get(cat, 0) + a
            elif ty == "income":
                inc += a
        return {"expense": exp, "income": inc, "count": len(r.data or []), "top": top}
    except Exception as e:
        logger.exception("period_stats failed: %s", str(e))
        return {"expense": 0, "income": 0, "count": 0, "top": {}}

async def export_csv(telegram_id: int, days: int = 30) -> bytes:
    start = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    r = (
        supabase.table("transactions")
        .select("created_at,type,amount,category,source")
        .eq("user_telegram_id", telegram_id)
        .gte("created_at", start)
        .order("created_at", desc=True)
        .execute()
    )

    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["created_at", "type", "amount", "category", "source"])
    for row in (r.data or []):
        w.writerow([
            (row.get("created_at") or "")[:19],
            row.get("type") or "",
            row.get("amount") or 0,
            row.get("category") or "",
            row.get("source") or "",
        ])
    return out.getvalue().encode("utf-8")

# -----------------------
# UI Keyboards
# -----------------------
def main_kb(lang: str) -> InlineKeyboardMarkup:
    rows = []
    if WEBAPP_URL:
        rows.append([InlineKeyboardButton("📱 Web App", web_app=WebAppInfo(url=WEBAPP_URL))])

    rows += [
        [InlineKeyboardButton("➖ Xarajat", callback_data="m:expense"),
         InlineKeyboardButton("➕ Daromad", callback_data="m:income")],
        [InlineKeyboardButton(t(lang, "reports"), callback_data="m:reports")],
    ]
    return InlineKeyboardMarkup(rows)

def cats_kb(tx_type: str) -> InlineKeyboardMarkup:
    items = EXPENSE_CATS if tx_type == "expense" else INCOME_CATS
    rows = []
    row = []
    for cat, label in items:
        row.append(InlineKeyboardButton(label, callback_data=f"c:{tx_type}:{cat}"))
        if len(row) == 2:
            rows.append(row); row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
    return InlineKeyboardMarkup(rows)

def reports_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 1 day", callback_data="r:1"),
         InlineKeyboardButton("📆 7 days", callback_data="r:7")],
        [InlineKeyboardButton("🗓 30 days", callback_data="r:30"),
         InlineKeyboardButton(t(lang, "export"), callback_data="export")],
        [InlineKeyboardButton(t(lang, "back"), callback_data="back")]
    ])

# -----------------------
# Handlers
# -----------------------
async def start_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or not update.message:
        return
    await ensure_user(user.id, user.first_name or "User")
    lang = await get_user_lang(user.id)
    await update.message.reply_text(t(lang, "welcome"), parse_mode="Markdown", reply_markup=main_kb(lang))

async def balance_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or not update.message:
        return
    lang = await get_user_lang(user.id)
    bal = await get_balance(user.id)
    ts = await today_stats(user.id)
    text = (
        f"💰 Balans: *{format_uzs(bal)}*\n\n"
        f"📅 Bugun:\n"
        f"↘️ Xarajat: {format_uzs(ts['expense'])}\n"
        f"↗️ Daromad: {format_uzs(ts['income'])}\n"
        f"🧾 Soni: {ts['count']}"
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=main_kb(lang))

async def cb_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q:
        return
    await q.answer()
    user = q.from_user
    lang = await get_user_lang(user.id)
    data = q.data or ""

    if data == "cancel":
        pending.pop(user.id, None)
        await q.edit_message_text("❌ Cancelled.", reply_markup=main_kb(lang))
        return

    if data == "back":
        bal = await get_balance(user.id)
        await q.edit_message_text(f"💰 Balans: *{format_uzs(bal)}*", parse_mode="Markdown", reply_markup=main_kb(lang))
        return

    if data == "m:expense":
        await q.edit_message_text("➖ Xarajat kategoriyasi:", reply_markup=cats_kb("expense"))
        return

    if data == "m:income":
        await q.edit_message_text("➕ Daromad kategoriyasi:", reply_markup=cats_kb("income"))
        return

    if data == "m:reports":
        await q.edit_message_text(t(lang, "reports"), reply_markup=reports_kb(lang))
        return

    if data.startswith("c:"):
        # c:expense:taxi
        _, tx_type, cat = data.split(":", 2)
        pending[user.id] = {"type": tx_type, "category": cat}
        await q.edit_message_text(f"✅ Tanlandi: *{tx_type} / {cat}*\n\nSummani yuboring:", parse_mode="Markdown")
        return

    if data.startswith("r:"):
        days = int(data.split(":")[1])
        st = await period_stats(user.id, days)
        top = st["top"]
        top_lines = []
        for k, v in sorted(top.items(), key=lambda x: x[1], reverse=True)[:5]:
            top_lines.append(f"• {k}: {format_uzs(v)}")
        top_txt = "\n".join(top_lines) if top_lines else "-"

        text = (
            f"📊 *{days} days*\n\n"
            f"↘️ Xarajat: {format_uzs(st['expense'])}\n"
            f"↗️ Daromad: {format_uzs(st['income'])}\n"
            f"🧾 Soni: {st['count']}\n\n"
            f"*Top:*\n{top_txt}"
        )
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=reports_kb(lang))
        return

    if data == "export":
        await q.edit_message_text("📥 Tayyorlanmoqda...")
        content = await export_csv(user.id, 30)
        f = io.BytesIO(content)
        f.name = f"hamyon_{datetime.now().strftime('%Y%m%d')}.csv"
        await ctx.bot.send_document(chat_id=user.id, document=InputFile(f), caption=t(lang, "export"))
        return

async def text_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = update.message
    if not user or not msg or not msg.text:
        return

    text = msg.text.strip()
    lang = await get_user_lang(user.id)
    await ensure_user(user.id, user.first_name or "User")

    # If user picked a category button earlier
    if user.id in pending:
        amt = parse_amount(text)
        if amt is None:
            await msg.reply_text(t(lang, "cant_parse"), parse_mode="Markdown")
            return

        tx_type = pending[user.id]["type"]
        category = pending[user.id]["category"]
        pending.pop(user.id, None)

        ok = await insert_transaction(user.id, tx_type, amt, category, "manual")
        if not ok:
            await msg.reply_text("❌ Insert failed. Check Railway logs (Supabase error shown).")
            return

        # balance delta: expense = -amt, income = +amt
        delta = -amt if tx_type == "expense" else amt
        await set_balance_delta(user.id, delta)

        bal = await get_balance(user.id)
        await msg.reply_text(
            t(lang, "saved").format(
                type=tx_type,
                cat=category,
                amt=format_uzs(amt),
                bal=format_uzs(bal),
            ),
            reply_markup=main_kb(lang),
        )
        return

    # Otherwise parse free text: "taxi 30k"
    amt = parse_amount(text)
    if amt is None:
        await msg.reply_text(t(lang, "cant_parse"), parse_mode="Markdown", reply_markup=main_kb(lang))
        return

    cat, tx_type = detect_category_and_type(text)

    ok = await insert_transaction(user.id, tx_type, amt, cat, "text")
    if not ok:
        await msg.reply_text("❌ Insert failed. Check Railway logs (Supabase error shown).")
        return

    delta = -amt if tx_type == "expense" else amt
    await set_balance_delta(user.id, delta)

    bal = await get_balance(user.id)
    await msg.reply_text(
        t(lang, "saved").format(
            type=tx_type,
            cat=cat,
            amt=format_uzs(amt),
            bal=format_uzs(bal),
        ),
        reply_markup=main_kb(lang),
    )

# -----------------------
# App
# -----------------------
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("balance", balance_cmd))
    app.add_handler(CallbackQueryHandler(cb_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    logger.info("🚀 Hamyon bot started (polling).")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
