import os
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from nlp import parse_quick_add

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = os.getenv("API_URL")          # e.g. https://your-api.up.railway.app
API_SECRET = os.getenv("API_SECRET", "") # must match API

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")  # optional voice

if not TOKEN:
    raise ValueError("Missing TELEGRAM_BOT_TOKEN")
if not API_URL:
    raise ValueError("Missing API_URL")


def kb_main():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 1 day", callback_data="stats:1"),
            InlineKeyboardButton("📆 7 days", callback_data="stats:7"),
        ],
        [
            InlineKeyboardButton("🗓 30 days", callback_data="stats:30"),
            InlineKeyboardButton("⬇️ CSV", callback_data="csv"),
        ],
    ])


async def api_post(path: str, json: dict):
    headers = {"X-API-SECRET": API_SECRET} if API_SECRET else {}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{API_URL}{path}", json=json, headers=headers)
        r.raise_for_status()
        return r.json()


async def api_get_json(path: str, params: dict) -> dict:
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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ Hamyon bot ishlayapti.\n\n"
        "Tez qo‘shish: `food 97500` yoki `transport 12000 taxi`\n"
        "Buyruqlar:\n"
        "/add <category> <amount> [desc]\n"
        "/today\n"
        "/range 7\n"
        "/csv\n",
        parse_mode="Markdown",
        reply_markup=kb_main(),
    )


async def add_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id

    if len(context.args) < 2:
        await update.message.reply_text("Misol: /add food 97500 lunch")
        return

    category_key = context.args[0]
    amount_str = context.args[1]
    digits = "".join([c for c in amount_str if c.isdigit()])
    if not digits:
        await update.message.reply_text("❌ Amount noto‘g‘ri. Misol: /add food 97500 lunch")
        return

    amount = int(digits)
    desc = " ".join(context.args[2:]) if len(context.args) > 2 else None

    await api_post("/transactions", {
        "telegram_id": tg_id,
        "type": "expense",
        "amount": amount,
        "category_key": category_key,
        "description": desc,
        "source": "manual",
    })

    await update.message.reply_text("✅ Saqlandi!", reply_markup=kb_main())


async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    data = await api_get_json("/stats/today", {"telegram_id": tg_id})

    msg = (
        f"📊 Bugun:\n"
        f"Xarajat: {data['expense']} UZS\n"
        f"Daromad: {data['income']} UZS\n"
        f"Qarz: {data['debt']} UZS\n"
        f"Tranzaksiya: {data['count']}"
    )
    await update.message.reply_text(msg, reply_markup=kb_main())


async def range_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    days = int(context.args[0]) if context.args else 7

    data = await api_get_json("/stats/range", {"telegram_id": tg_id, "days": days})

    msg = (
        f"📆 {days} days:\n"
        f"Xarajat: {data['expense']} UZS\n"
        f"Daromad: {data['income']} UZS\n"
        f"Qarz: {data['debt']} UZS"
    )
    await update.message.reply_text(msg, reply_markup=kb_main())


async def csv_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    content = await api_get_bytes("/export/csv", {"telegram_id": tg_id})

    await update.message.reply_document(
        document=content,
        filename="transactions.csv",
        caption="⬇️ CSV export",
    )


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    tg_id = q.from_user.id
    data = q.data

    if data.startswith("stats:"):
        days = int(data.split(":")[1])
        if days == 1:
            d = await api_get_json("/stats/today", {"telegram_id": tg_id})
            text = (
                f"📊 1 day\n"
                f"Xarajat: {d['expense']} UZS\n"
                f"Daromad: {d['income']} UZS\n"
                f"Qarz: {d['debt']} UZS\n"
                f"Tranzaksiya: {d['count']}"
            )
        else:
            d = await api_get_json("/stats/range", {"telegram_id": tg_id, "days": days})
            text = (
                f"📆 {days} days\n"
                f"Xarajat: {d['expense']} UZS\n"
                f"Daromad: {d['income']} UZS\n"
                f"Qarz: {d['debt']} UZS"
            )

        await q.edit_message_text(text, reply_markup=kb_main())
        return

    if data == "csv":
        content = await api_get_bytes("/export/csv", {"telegram_id": tg_id})
        await q.message.reply_document(
            document=content,
            filename="transactions.csv",
            caption="⬇️ CSV export",
        )
        return


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    text = (update.message.text or "").strip()

    parsed = parse_quick_add(text)
    if not parsed:
        return

    cat, amount, desc = parsed

    await api_post("/transactions", {
        "telegram_id": tg_id,
        "type": "expense",
        "amount": amount,
        "category_key": cat,
        "description": desc,
        "source": "text",
    })

    await update.message.reply_text("✅ Saqlandi!", reply_markup=kb_main())


# -------- Voice -> text (optional) --------
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
    tg_id = update.effective_user.id
    voice = update.message.voice
    if not voice:
        return

    f = await context.bot.get_file(voice.file_id)
    b = await f.download_as_bytearray()

    text = await transcribe_voice(bytes(b))
    if not text:
        await update.message.reply_text("🎙 Ovozni o‘qish uchun OPENAI_API_KEY kerak.")
        return

    parsed = parse_quick_add(text)
    if not parsed:
        await update.message.reply_text(f"🎙 Matn: {text}\n\n❌ Tushunmadim. Misol: 'food 97500'")
        return

    cat, amount, desc = parsed
    await api_post("/transactions", {
        "telegram_id": tg_id,
        "type": "expense",
        "amount": amount,
        "category_key": cat,
        "description": desc or f"(voice) {text}",
        "source": "voice",
    })

    await update.message.reply_text(f"🎙 {text}\n✅ Saqlandi!", reply_markup=kb_main())


def build_application() -> Application:
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_cmd))
    app.add_handler(CommandHandler("today", today))
    app.add_handler(CommandHandler("range", range_cmd))
    app.add_handler(CommandHandler("csv", csv_cmd))

    app.add_handler(CallbackQueryHandler(on_callback))

    app.add_handler(MessageHandler(filters.VOICE, on_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    return app


def main():
    app = build_application()
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
