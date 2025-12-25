import os
import re
import httpx
from telegram import (
    Update, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

from i18n import t
from nlp import parse_single_line, normalize_cat

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = os.getenv("API_URL")          # https://your-api.up.railway.app
API_SECRET = os.getenv("API_SECRET","")
WEBAPP_URL = os.getenv("WEBAPP_URL","") # optional mini-app link

if not TOKEN:
    raise ValueError("Missing TELEGRAM_BOT_TOKEN")
if not API_URL:
    raise ValueError("Missing API_URL")

def main_menu(lang: str):
    # Simple “startup-like” menu (reply keyboard)
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("➖ Xarajat"), KeyboardButton("➕ Daromad")],
            [KeyboardButton("🧾 Chek"), KeyboardButton("🎯 Maqsad")],
            [KeyboardButton("📊 Hisobot"), KeyboardButton("⚙️ Sozlama")],
        ],
        resize_keyboard=True
    )

def settings_menu(lang: str):
    row = [KeyboardButton("🌐 Til"), KeyboardButton("💰 Limit")]
    row2 = [KeyboardButton("⬅️ Orqaga")]
    return ReplyKeyboardMarkup([row, row2], resize_keyboard=True)

def lang_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇺🇿 Uzbek", callback_data="lang:uz"),
         InlineKeyboardButton("🇷🇺 Русский", callback_data="lang:ru"),
         InlineKeyboardButton("🇬🇧 English", callback_data="lang:en")]
    ])

def draft_kb(draft_id: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Saqlash", callback_data=f"draft:save:{draft_id}"),
         InlineKeyboardButton("✏️ Edit", callback_data=f"draft:edit:{draft_id}")],
        [InlineKeyboardButton("❌ Bekor", callback_data=f"draft:cancel:{draft_id}")]
    ])

def edit_kb(draft_id: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔁 Type", callback_data=f"edit:type:{draft_id}"),
         InlineKeyboardButton("🏷 Category", callback_data=f"edit:cat:{draft_id}")],
        [InlineKeyboardButton("💵 Amount", callback_data=f"edit:amount:{draft_id}"),
         InlineKeyboardButton("📝 Desc", callback_data=f"edit:desc:{draft_id}")],
        [InlineKeyboardButton("✅ Save", callback_data=f"draft:save:{draft_id}"),
         InlineKeyboardButton("❌ Cancel", callback_data=f"draft:cancel:{draft_id}")]
    ])

CATEGORIES = [
    ("food","🍕 Oziq-ovqat"),
    ("transport","🚕 Transport"),
    ("rent","🏠 Ijara"),
    ("bills","📶 Kommunal"),
    ("health","💊 Dori"),
    ("shopping","🛍 Xarid"),
    ("misc","📦 Boshqa"),
]

def cat_kb(prefix: str, draft_id: str):
    buttons = []
    for k, label in CATEGORIES:
        buttons.append([InlineKeyboardButton(label, callback_data=f"{prefix}:{draft_id}:{k}")])
    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data=f"edit:back:{draft_id}")])
    return InlineKeyboardMarkup(buttons)

async def api_post(path: str, json: dict):
    headers = {"X-API-SECRET": API_SECRET} if API_SECRET else {}
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(f"{API_URL}{path}", json=json, headers=headers)
        r.raise_for_status()
        return r.json()

async def api_get(path: str, params: dict):
    headers = {"X-API-SECRET": API_SECRET} if API_SECRET else {}
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(f"{API_URL}{path}", params=params, headers=headers)
        r.raise_for_status()
        return r

async def api_file(path: str, file_bytes: bytes, filename: str):
    headers = {"X-API-SECRET": API_SECRET} if API_SECRET else {}
    files = {"file": (filename, file_bytes)}
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(f"{API_URL}{path}", files=files, headers=headers)
        r.raise_for_status()
        return r.json()

def get_lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    return context.user_data.get("lang", "uz")

def set_lang(context: ContextTypes.DEFAULT_TYPE, lang: str):
    context.user_data["lang"] = lang

def draft_render(d: dict) -> str:
    # human-readable preview
    lines = []
    lines.append(f"Type: {d['type']}")
    lines.append(f"Category: {d['category_key']}")
    lines.append(f"Amount: {d['amount']} UZS")
    if d.get("merchant"):
        lines.append(f"Merchant: {d['merchant']}")
    if d.get("description"):
        lines.append(f"Desc: {d['description']}")
    if d.get("raw_text"):
        lines.append(f"Raw: {d['raw_text']}")
    return "\n".join(lines)

def new_draft(context, draft: dict) -> str:
    import uuid
    did = str(uuid.uuid4())[:8]
    drafts = context.user_data.setdefault("drafts", {})
    drafts[did] = draft
    return did

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    await update.message.reply_text(
        t(lang, "welcome"),
        parse_mode="Markdown",
        reply_markup=main_menu(lang)
    )
    # first time: show language switch
    await update.message.reply_text(t(lang, "choose_lang"), reply_markup=lang_menu())

async def on_lang_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data
    if data.startswith("lang:"):
        lang = data.split(":")[1]
        set_lang(context, lang)
        await q.edit_message_text("✅ OK")
        # refresh welcome/menu
        await q.message.reply_text(t(lang,"welcome"), parse_mode="Markdown", reply_markup=main_menu(lang))

# -------- Stats / CSV ----------
async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, days: int):
    lang = get_lang(context)
    tg_id = update.effective_user.id
    if days == 1:
        r = await api_get("/stats/today", {"telegram_id": tg_id})
        d = r.json()
        text = f"{t(lang,'stats_today')}\nXarajat: {d['expense']} UZS\nDaromad: {d['income']} UZS\nQarz: {d['debt']} UZS\nTranzaksiya: {d['count']}"
    else:
        r = await api_get("/stats/range", {"telegram_id": tg_id, "days": days})
        d = r.json()
        title = t(lang,'stats_week') if days==7 else t(lang,'stats_month')
        text = f"{title}\nXarajat: {d['expense']} UZS\nDaromad: {d['income']} UZS\nQarz: {d['debt']} UZS"
    await update.message.reply_text(text, reply_markup=main_menu(lang))

async def csv_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    tg_id = update.effective_user.id
    r = await api_get("/export/csv", {"telegram_id": tg_id})
    await update.message.reply_document(
        document=r.text.encode("utf-8"),
        filename="transactions.csv",
        caption=t(lang,"csv")
    )

# -------- Menu flows ----------
async def on_menu_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    txt = (update.message.text or "").strip()

    if txt == "📊 Hisobot":
        await show_stats(update, context, 1)
        await show_stats(update, context, 7)
        return

    if txt == "⚙️ Sozlama":
        await update.message.reply_text(t(lang,"settings"), reply_markup=settings_menu(lang))
        return

    if txt == "🌐 Til":
        await update.message.reply_text(t(lang,"choose_lang"), reply_markup=lang_menu())
        return

    if txt == "💰 Limit":
        context.user_data["await_budget"] = True
        await update.message.reply_text("Limit format:\n`food 1500000`\n`transport 500000`\nYoki umumiy: `all 3000000`", parse_mode="Markdown")
        return

    if txt == "⬅️ Orqaga":
        await update.message.reply_text("✅", reply_markup=main_menu(lang))
        return

    # If user types quick add like: "taksi 20000"
    parsed = parse_single_line(txt)
    if parsed:
        cat, amount, desc = parsed
        draft = {
            "type": "expense",
            "category_key": cat,
            "amount": amount,
            "description": desc,
            "source": "text",
            "raw_text": txt
        }
        did = new_draft(context, draft)
        await update.message.reply_text(t(lang,"draft_title") + "\n\n" + draft_render(draft), reply_markup=draft_kb(did))
        return

    # budget input waiting
    if context.user_data.get("await_budget"):
        context.user_data["await_budget"] = False
        m = re.match(r"^\s*(\w+)\s+(\d[\d\s]*)\s*$", txt.lower())
        if not m:
            await update.message.reply_text("❌ Format: `food 1500000`", parse_mode="Markdown")
            return
        cat = m.group(1)
        amount = int(re.sub(r"[^\d]","",m.group(2)))
        if cat == "all":
            cat = None

        tg_id = update.effective_user.id
        await api_post("/budgets", {"telegram_id": tg_id, "category_key": cat, "monthly_limit": amount, "enabled": True})
        await update.message.reply_text(t(lang,"budget_set"), reply_markup=main_menu(lang))
        return

# -------- Voice: auto parse, no button ----------
async def on_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    tg_id = update.effective_user.id

    voice = update.message.voice
    f = await context.bot.get_file(voice.file_id)
    b = await f.download_as_bytearray()

    # Parse via API
    data = await api_file("/parse/voice", bytes(b), "voice.ogg")
    text = data.get("text","")
    items = data.get("items", [])

    if not items:
        await update.message.reply_text(f"🎙 Matn: {text}\n\n❌ Tushunmadim. Misol: `taksi 20000`", parse_mode="Markdown")
        return

    # if multi-items: create one draft per item, or one combined draft?
    # We'll create combined draft as one expense with desc listing items (simple & safe)
    total = sum(int(x["amount"]) for x in items)
    desc_lines = []
    for it in items:
        desc_lines.append(f"{it['category_key']} {it['amount']}" + (f" {it.get('description')}" if it.get("description") else ""))
    draft = {
        "type": "expense",
        "category_key": "misc",
        "amount": total,
        "description": " | ".join(desc_lines),
        "source": "voice",
        "raw_text": text
    }
    did = new_draft(context, draft)
    await update.message.reply_text(t(lang,"draft_title") + "\n\n" + draft_render(draft), reply_markup=draft_kb(did))

# -------- Receipt photo: auto parse ----------
async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    photos = update.message.photo
    if not photos:
        return
    best = photos[-1]
    f = await context.bot.get_file(best.file_id)
    b = await f.download_as_bytearray()

    data = await api_file("/parse/receipt", bytes(b), "receipt.jpg")
    rec = data.get("data", {})
    suggested = data.get("suggested_category","misc")

    merchant = rec.get("merchant")
    total = rec.get("total")
    if not total:
        await update.message.reply_text("🧾 Chek o‘qildi, lekin total topilmadi. Summani yozing: `ovqat 97500`", parse_mode="Markdown")
        return

    draft = {
        "type": "expense",
        "category_key": suggested,
        "amount": int(float(total)),
        "description": "receipt",
        "merchant": merchant,
        "source": "receipt",
        "raw_text": None
    }
    did = new_draft(context, draft)
    await update.message.reply_text(t(lang,"draft_title") + "\n\n" + draft_render(draft), reply_markup=draft_kb(did))

# -------- Draft callbacks (save/edit/cancel) ----------
async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    lang = get_lang(context)
    data = q.data or ""
    drafts = context.user_data.setdefault("drafts", {})

    if data.startswith("draft:cancel:"):
        did = data.split(":")[2]
        drafts.pop(did, None)
        await q.edit_message_text(t(lang,"cancelled"))
        return

    if data.startswith("draft:edit:"):
        did = data.split(":")[2]
        d = drafts.get(did)
        if not d:
            await q.edit_message_text("❌ Draft not found")
            return
        await q.edit_message_text(t(lang,"edit_what") + "\n\n" + draft_render(d), reply_markup=edit_kb(did))
        return

    if data.startswith("edit:back:"):
        did = data.split(":")[2]
        d = drafts.get(did)
        await q.edit_message_text(t(lang,"edit_what") + "\n\n" + draft_render(d), reply_markup=edit_kb(did))
        return

    if data.startswith("edit:cat:"):
        did = data.split(":")[2]
        await q.edit_message_text("🏷 Category tanlang:", reply_markup=cat_kb("pickcat", did))
        return

    if data.startswith("pickcat:"):
        _, did, cat = data.split(":")
        d = drafts.get(did)
        if not d:
            await q.edit_message_text("❌ Draft not found")
            return
        d["category_key"] = cat
        await q.edit_message_text(t(lang,"edit_what") + "\n\n" + draft_render(d), reply_markup=edit_kb(did))
        return

    if data.startswith("edit:type:"):
        did = data.split(":")[2]
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➖ expense", callback_data=f"picktype:{did}:expense"),
             InlineKeyboardButton("➕ income", callback_data=f"picktype:{did}:income")],
            [InlineKeyboardButton("📄 debt", callback_data=f"picktype:{did}:debt")],
            [InlineKeyboardButton("⬅️ Back", callback_data=f"edit:back:{did}")]
        ])
        await q.edit_message_text("Type:", reply_markup=kb)
        return

    if data.startswith("picktype:"):
        _, did, tp = data.split(":")
        d = drafts.get(did)
        d["type"] = tp
        await q.edit_message_text(t(lang,"edit_what") + "\n\n" + draft_render(d), reply_markup=edit_kb(did))
        return

    if data.startswith("edit:amount:"):
        did = data.split(":")[2]
        context.user_data["await_amount_for"] = did
        await q.message.reply_text(t(lang,"ask_amount"))
        return

    if data.startswith("edit:desc:"):
        did = data.split(":")[2]
        context.user_data["await_desc_for"] = did
        await q.message.reply_text(t(lang,"ask_desc"), parse_mode="Markdown")
        return

    if data.startswith("draft:save:"):
        did = data.split(":")[2]
        d = drafts.get(did)
        if not d:
            await q.edit_message_text("❌ Draft not found")
            return
        tg_id = q.from_user.id
        payload = {
            "telegram_id": tg_id,
            "type": d["type"],
            "amount": d["amount"],
            "category_key": d["category_key"],
            "description": d.get("description"),
            "merchant": d.get("merchant"),
            "source": d.get("source","manual"),
            "raw_text": d.get("raw_text")
        }
        res = await api_post("/transactions", payload)
        drafts.pop(did, None)

        await q.edit_message_text(t(lang,"saved"))
        # budget alert
        if res.get("budget_exceeded"):
            limit_val = res.get("limit")
            spent = res.get("spent")
            cat = d["category_key"]
            await q.message.reply_text(t(lang,"budget_over").format(cat=cat, limit=limit_val, spent=spent))
        return

# -------- capture replies for amount/desc edit ----------
async def on_text_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (update.message.text or "").strip()
    lang = get_lang(context)
    drafts = context.user_data.setdefault("drafts", {})

    did = context.user_data.get("await_amount_for")
    if did:
        context.user_data["await_amount_for"] = None
        d = drafts.get(did)
        if not d:
            return
        try:
            amount = int(re.sub(r"[^\d]","",txt))
            d["amount"] = amount
            await update.message.reply_text("✅ Amount updated.")
        except:
            await update.message.reply_text("❌ Raqam yuboring.")
        return

    did = context.user_data.get("await_desc_for")
    if did:
        context.user_data["await_desc_for"] = None
        d = drafts.get(did)
        if not d:
            return
        d["description"] = None if txt == "-" else txt
        await update.message.reply_text("✅ Desc updated.")
        return

async def cmd_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_stats(update, context, 1)

async def cmd_week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_stats(update, context, 7)

async def cmd_month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_stats(update, context, 30)

async def cmd_csv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await csv_cmd(update, context)

def build_app():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("today", cmd_today))
    app.add_handler(CommandHandler("week", cmd_week))
    app.add_handler(CommandHandler("month", cmd_month))
    app.add_handler(CommandHandler("csv", cmd_csv))

    app.add_handler(CallbackQueryHandler(on_lang_cb, pattern=r"^lang:"))
    app.add_handler(CallbackQueryHandler(on_callback))

    # Priority: voice/photo first
    app.add_handler(MessageHandler(filters.VOICE, on_voice))
    app.add_handler(MessageHandler(filters.PHOTO, on_photo))

    # Menu / quick-add / settings
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_menu_text))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text_edit))

    return app

if __name__ == "__main__":
    # IMPORTANT: DO NOT wrap run_polling inside asyncio.run
    # This fixes your “event loop already running” error.
    application = build_app()
    application.run_polling(drop_pending_updates=True)
