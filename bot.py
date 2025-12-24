import os
import re
import logging
from datetime import datetime, timezone

import asyncpg
from dotenv import load_dotenv

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

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("hamyon-bot")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

if not BOT_TOKEN:
    raise ValueError("Missing TELEGRAM_BOT_TOKEN")
if not DATABASE_URL:
    raise ValueError("Missing DATABASE_URL (Railway Postgres)")

# In-memory per-user state (fine for single-instance bot)
pending = {}  # telegram_id -> {"type": "expense"/"income", "category": "food"}


# -----------------------
# Parsing helpers
# -----------------------
def parse_amount(text: str) -> int | None:
    s = text.strip().lower()

    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(k|к|ming|тыс)\b", s)
    if m:
        return int(float(m.group(1).replace(",", ".")) * 1_000)

    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(mln|million|млн|m)\b", s)
    if m:
        return int(float(m.group(1).replace(",", ".")) * 1_000_000)

    m = re.search(r"(\d+)", s)
    return int(m.group(1)) if m else None


def format_uzs(x: int) -> str:
    return f"{x:,}".replace(",", " ") + " UZS"


# -----------------------
# UI
# -----------------------
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
# DB: schema + queries
# -----------------------
CREATE_SQL = """
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS public.users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  telegram_id BIGINT UNIQUE NOT NULL,
  name VARCHAR(255) NOT NULL DEFAULT 'User',
  balance BIGINT NOT NULL DEFAULT 0,
  language VARCHAR(10) NOT NULL DEFAULT 'uz',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.transactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  user_telegram_id BIGINT, -- optional convenience
  type VARCHAR(20) NOT NULL CHECK (type IN ('expense','income')),
  amount BIGINT NOT NULL CHECK (amount >= 0),
  category VARCHAR(50) NOT NULL DEFAULT 'other',
  source VARCHAR(20) NOT NULL DEFAULT 'manual',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON public.users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_tx_user_id_date ON public.transactions(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tx_telegram_date ON public.transactions(user_telegram_id, created_at DESC);
"""


async def db_init(app: Application):
    """
    Runs once on startup.
    """
    app.bot_data["db_pool"] = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
    async with app.bot_data["db_pool"].acquire() as conn:
        await conn.execute(CREATE_SQL)
    logger.info("✅ DB initialized (Railway Postgres) and schema ensured.")


def pool(ctx: ContextTypes.DEFAULT_TYPE) -> asyncpg.pool.Pool:
    return ctx.application.bot_data["db_pool"]


async def ensure_user(ctx: ContextTypes.DEFAULT_TYPE, telegram_id: int, name: str):
    """
    Upsert by telegram_id and return user row.
    """
    q = """
    INSERT INTO public.users (telegram_id, name)
    VALUES ($1, $2)
    ON CONFLICT (telegram_id) DO UPDATE
      SET name = EXCLUDED.name,
          updated_at = now()
    RETURNING id, telegram_id, name, balance, language;
    """
    async with pool(ctx).acquire() as conn:
        return await conn.fetchrow(q, telegram_id, name or "User")


async def insert_transaction(ctx: ContextTypes.DEFAULT_TYPE, user_id, telegram_id: int, tx_type: str, amount: int, category: str, source: str) -> bool:
    q = """
    INSERT INTO public.transactions (user_id, user_telegram_id, type, amount, category, source)
    VALUES ($1, $2, $3, $4, $5, $6);
    """
    try:
        async with pool(ctx).acquire() as conn:
            await conn.execute(q, user_id, telegram_id, tx_type, int(amount), category, source)
        return True
    except Exception as e:
        logger.exception("insert_transaction failed: %s", str(e))
        return False


async def update_balance(ctx: ContextTypes.DEFAULT_TYPE, telegram_id: int, delta: int) -> int:
    q = """
    UPDATE public.users
    SET balance = balance + $2,
        updated_at = now()
    WHERE telegram_id = $1
    RETURNING balance;
    """
    async with pool(ctx).acquire() as conn:
        row = await conn.fetchrow(q, telegram_id, int(delta))
        return int(row["balance"]) if row else 0


async def today_stats(ctx: ContextTypes.DEFAULT_TYPE, telegram_id: int) -> dict:
    # Use UTC day start (simple). You can switch to Asia/Tashkent later if you want.
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    q = """
    SELECT
      COALESCE(SUM(amount) FILTER (WHERE type='expense'), 0) AS expense,
      COALESCE(SUM(amount) FILTER (WHERE type='income'), 0)  AS income,
      COUNT(*) AS cnt
    FROM public.transactions
    WHERE user_telegram_id = $1 AND created_at >= $2;
    """
    async with pool(ctx).acquire() as conn:
        row = await conn.fetchrow(q, telegram_id, start)
        return {"expense": int(row["expense"]), "income": int(row["income"]), "count": int(row["cnt"])}


async def get_balance(ctx: ContextTypes.DEFAULT_TYPE, telegram_id: int) -> int:
    q = "SELECT balance FROM public.users WHERE telegram_id=$1;"
    async with pool(ctx).acquire() as conn:
        row = await conn.fetchrow(q, telegram_id)
        return int(row["balance"]) if row else 0


# -----------------------
# Handlers
# -----------------------
async def start_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    if not u or not update.message:
        return
    await ensure_user(ctx, u.id, u.first_name or "User")
    await update.message.reply_text(
        "👋 Salom! Kategoriya tanlang va summani yuboring (masalan: 97500 yoki 97k).",
        reply_markup=main_kb(),
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
        st = await today_stats(ctx, u.id)
        bal = await get_balance(ctx, u.id)
        await q.edit_message_text(
            f"📅 Bugun\n"
            f"↘️ Xarajat: {format_uzs(st['expense'])}\n"
            f"↗️ Daromad: {format_uzs(st['income'])}\n"
            f"🧾 Soni: {st['count']}\n"
            f"💰 Balans: {format_uzs(bal)}",
            reply_markup=main_kb(),
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

    user = await ensure_user(ctx, u.id, u.first_name or "User")
    user_id = user["id"]

    if u.id in pending:
        tx_type = pending[u.id]["type"]
        category = pending[u.id]["category"]
        pending.pop(u.id, None)
        source = "manual"
    else:
        tx_type = "expense"
        category = "other"
        source = "text"

    ok = await insert_transaction(ctx, user_id, u.id, tx_type, amt, category, source)
    if not ok:
        await msg.reply_text("❌ Insert failed. (Check Railway logs for SQL error.)")
        return

    delta = -amt if tx_type == "expense" else amt
    new_bal = await update_balance(ctx, u.id, delta)

    await msg.reply_text(
        f"✅ Saqlandi: {tx_type}\n"
        f"📂 {category}\n"
        f"💵 {format_uzs(amt)}\n"
        f"💰 Balans: {format_uzs(new_bal)}",
        reply_markup=main_kb(),
    )


def main():
    app = Application.builder().token(BOT_TOKEN).post_init(db_init).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CallbackQueryHandler(cb_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    logger.info("🚀 Hamyon bot started (polling). Make sure only ONE instance runs.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
