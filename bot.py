import os
import psycopg
from psycopg_pool import AsyncConnectionPool
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

if not TOKEN:
    raise ValueError("Missing TELEGRAM_BOT_TOKEN")

if not DATABASE_URL:
    raise ValueError("Missing DATABASE_URL")

pool = AsyncConnectionPool(DATABASE_URL, open=True)


CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS users (
    telegram_id BIGINT PRIMARY KEY,
    name TEXT,
    balance BIGINT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT REFERENCES users(telegram_id),
    amount BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT now()
);
"""


async def init_db():
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(CREATE_TABLES_SQL)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    name = update.effective_user.first_name

    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO users (telegram_id, name) VALUES (%s, %s) "
                "ON CONFLICT (telegram_id) DO NOTHING",
                (tg_id, name),
            )

    await update.message.reply_text("✅ Bot is connected to PostgreSQL!")


async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    amount = int(context.args[0])

    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO transactions (telegram_id, amount) VALUES (%s, %s)",
                (tg_id, amount),
            )
            await cur.execute(
                "UPDATE users SET balance = balance + %s WHERE telegram_id = %s",
                (amount, tg_id),
            )

    await update.message.reply_text(f"💸 Added {amount}")


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id

    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT balance FROM users WHERE telegram_id = %s",
                (tg_id,),
            )
            row = await cur.fetchone()

    bal = row[0] if row else 0
    await update.message.reply_text(f"💰 Balance: {bal}")


async def main():
    await init_db()

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("balance", balance))

    print("🚀 Bot started")
    await app.run_polling()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
