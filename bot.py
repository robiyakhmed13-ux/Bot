import os
import re
import logging
from datetime import datetime, timezone

from dotenv import load_dotenv
from supabase import create_client
from postgrest.exceptions import APIError

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
# LOGGING
# -----------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("hamyon-bot")

# -----------------------
# ENV
# -----------------------
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()

# REQUIRED: use service role (sb_secret_...)
SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    or os.getenv("SUPABASE_SECRET_KEY", "").strip()
)

if not BOT_TOKEN:
    raise ValueError("Missing TELEGRAM_BOT_TOKEN")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY (sb_secret_...)")

logger.info("Supabase key prefix in use: %s", SUPABASE_KEY[:12])

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# -----------------------
# PARSING
# -----------------------
def parse_amount(text: str) -> int | None:
    s = text.strip().lower()

    # 97.5k / 97k / 97 ming
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(k|к|ming|тыс)\b", s)
    if m:
        return int(float(m.group(1).replace(",", ".")) * 1_000)

    # 1.2m / 1 mln
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(mln|million|млн|m)\b", s)
    if m:
        return int(float(m.group(1).replace(",", ".")) * 1_000_000)

    # plain number
    m = re.search(r"(\d+)", s)
    return int(m.group(1)) if m else None


def format_uzs(x: int) -> str:
    return f"{x:,}".replace(",", " ") + " UZS"


# -----------------------
# DB HELPERS (NO maybe_single)
# -----------------------
def db_first_row(table: str, select_cols: str, where_key: str, where_val):
    r = supabase.table(table).select(select_cols).eq(where_key, where_val).execute()
    data = r.data or []
    return data[0] if len(data) else None


async def ensure_user(telegram_id: int, display_name: str) -> dict:
    # Only request columns that actually exist
    user = db_first_row("users", "id,telegram_id,balance,language", "telegram_id", telegram_id)
    if user:
        return user

    # Insert WITHOUT name (because your table doesn't have it)
    supabase.table("users").insert({
        "telegram_id": telegram_id,
        "balance": 0,
        "language": "uz",
    }).execute()

    user = db_first_row("users", "id,telegram_id,balance,language", "telegram_id", telegram_id)
    if not user:
        raise RuntimeError("Failed to create user in public.users")
    return user
    
async def update_balance(telegram_id: int, delta: int) -> int:
    user = db_first_row("users", "telegram_id,balance", "telegram_id", telegram_id)
    if not user:
        return 0
    cur = int(user.get("balance") or 0)
    new_bal = cur + int(delta)
    supabase.table("users").update({"balance": new_bal}).eq("telegram_id", telegram_id).execute()
    return new_bal


async def insert_transaction(user_uuid: str, telegram_id: int, tx_type: str, amount_abs: int, category: str, source: str):
    """
    Inserts into public.transactions with REQUIRED user_id (UUID).
    Your DB requires user_id NOT NULL -> we always provide it.
    """
    try:
        supabase.table("transactions").insert({
            "user_id": user_uuid,              # ✅ REQUIRED
            "user_telegram_id": telegram_id,   # optional but helpful
            "type": tx_type,                   # expense/income
            "amount": int(amount_abs),         # positive number
            "category": category,              # varchar
            "source": source,                  # manual/text
        }).execute()
        return True

    except APIError as e:
        logger.error("SUPABASE APIError: %s", getattr(e, "message", str(e)))
        logger.error("SUPABASE details: %s", getattr(e, "details", ""))
        logger.error("SUPABASE code: %s", getattr(e, "code", ""))
        return False

    except Exception as e:
        logger.exception("insert_transaction failed: %s", str(e))
        return False


async def today_stats(telegram_id: int) -> dict:
    """
    Sum today by type from DB. (UTC day start for simplicity.)
    """
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
        a = int(row.get("amount") or 0)
        t = (row.get("type") or "").lower()
        if t == "expense":
            exp += a
        elif t == "income":
            inc += a
    return {"expense": exp, "income": inc, "count": len(r.data or [])}


# -----------------------
# BOT UI
# -----------------------
pending = {}  # telegram_id -> {"type": "...", "category": "..."}

EXPENSE_CATS = [
    ("food", "🍕 Oziq-ovqat"),
    ("taxi", "🚕 Taksi"),
    ("shopping", "🛍️ Xaridlar"),
    ("bills", "💡 Kommunal"),
    ("other", "📦 Boshqa"),
]
INCOME_CATS = [
    ("salary", "💰 Oylik"),
    ("bonus", "🎉 Bonus"),
    ("other_income", "💵 Boshqa"),
]

def main_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➖ Xarajat", callback_data="m:expense"),
         InlineKeyboardButton("➕ Daromad", callback_data="m:income")],
        [InlineKeyboardButton("📅 Bugun", callback_data="m:today")],
    ])

def cats_kb(tx_type: str):
    items = EXPENSE_CATS if tx_type == "expense" else INCOME_CATS
    rows = [[InlineKeyboardButton(label, callback_data=f"c:{tx_type}:{cat}")]
            for cat, label in items]
    rows.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
    return InlineKeyboardMarkup(rows)


# -----------------------
# HANDLERS
# -----------------------
async def start_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    if not u or not update.message:
        return
    await ensure_user(u.id, u.first_name or "User")
    await update.message.reply_text(
        "👋 Salom! Kategoriya tanlang va summani yuboring (masalan: 97500 yoki 97k).",
        reply_markup=main_kb()
    )

async def cb_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q:
        return
    await q.answer()
    u = q.from_user
    data = q.data or ""

    if data == "cancel":
        pending.pop(u.id, None)
        await q.edit_message_text("❌ Cancelled.", reply_markup=main_kb())
        return

    if data == "m:expense":
        await q.edit_message_text("➖ Xarajat kategoriyasi:", reply_markup=cats_kb("expense"))
        return

    if data == "m:income":
        await q.edit_message_text("➕ Daromad kategoriyasi:", reply_markup=cats_kb("income"))
        return

    if data.startswith("c:"):
        _, tx_type, cat = data.split(":", 2)
        pending[u.id] = {"type": tx_type, "category": cat}
        await q.edit_message_text(f"✅ Tanlandi: {tx_type}/{cat}\n\nSummani yuboring:")
        return

    if data == "m:today":
        st = await today_stats(u.id)
        user = db_first_row("users", "balance", "telegram_id", u.id) or {}
        bal = int(user.get("balance") or 0)
        await q.edit_message_text(
            f"📅 Bugun\n"
            f"↘️ Xarajat: {format_uzs(st['expense'])}\n"
            f"↗️ Daromad: {format_uzs(st['income'])}\n"
            f"🧾 Soni: {st['count']}\n"
            f"💰 Balans: {format_uzs(bal)}",
            reply_markup=main_kb()
        )
        return


async def text_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    msg = update.message
    if not u or not msg or not msg.text:
        return

    amt = parse_amount(msg.text)
    if amt is None:
        await msg.reply_text("❌ Summani tushunmadim. Masalan: 97500 yoki 97k", reply_markup=main_kb())
        return

    user = await ensure_user(u.id, u.first_name or "User")
    user_uuid = str(user["id"])

    if u.id in pending:
        tx_type = pending[u.id]["type"]
        category = pending[u.id]["category"]
        pending.pop(u.id, None)
        source = "manual"
    else:
        tx_type = "expense"
        category = "other"
        source = "text"

    ok = await insert_transaction(user_uuid, u.id, tx_type, amt, category, source)
    if not ok:
        await msg.reply_text("❌ Insert failed. (See Railway logs for details.)")
        return

    delta = -amt if tx_type == "expense" else amt
    new_bal = await update_balance(u.id, delta)

    await msg.reply_text(
        f"✅ Saqlandi: {tx_type}\n"
        f"📂 {category}\n"
        f"💵 {format_uzs(amt)}\n"
        f"💰 Balans: {format_uzs(new_bal)}",
        reply_markup=main_kb()
    )


def main():
    app = Application.builder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CallbackQueryHandler(cb_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    logger.info("🚀 Hamyon bot started (polling).")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

