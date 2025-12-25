import os
import json
import uuid
from dataclasses import dataclass
from typing import Optional, Dict, Tuple

import httpx
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from nlp import parse_one, parse_multi, normalize_category

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = os.getenv("API_URL") or os.getenv("PUBLIC_URL") or os.getenv("BACKEND_URL")  # accept aliases
API_SECRET = os.getenv("API_SECRET", "")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY".lower()) or ""

if not TOKEN:
    raise ValueError("Missing TELEGRAM_BOT_TOKEN")
if not API_URL:
    raise ValueError("Missing API_URL (set API_URL to your FastAPI Railway public URL)")

# ---------------- I18N ----------------
I18N = {
    "uz": {
        "welcome": "👋 Assalomu alaykum!\n\nMen *Hamyon* — moliyaviy yordamchingiz.\n"
                   "Tez yozish: `taksi 2000`, `ovqat 45000`, `internet 50000`\n"
                   "Yoki audio yuboring 🎙\n\nPastdagi tugmalar orqali foydalaning 👇",
        "choose_lang": "Tilni tanlang / Choose language / Выберите язык:",
        "menu": "🏠 Menyu",
        "btn_income": "➕ Daromad",
        "btn_expense": "➖ Xarajat",
        "btn_debt": "📄 Qarz",
        "btn_stats": "📊 Hisobot",
        "btn_settings": "⚙️ Sozlama",
        "btn_app": "📱 Ilova",
        "stats_1": "📊 1 kun",
        "stats_7": "📆 7 kun",
        "stats_30": "🗓 30 kun",
        "csv": "⬇️ CSV",
        "confirm_title": "🧾 Qoralama topildi. Tasdiqlaysizmi?",
        "save": "✅ Saqlash",
        "edit": "✏️ Edit",
        "cancel": "❌ Bekor",
        "edit_choose": "Nimani o‘zgartiramiz?",
        "edit_cat": "🏷 Kategoriya",
        "edit_amt": "💰 Summa",
        "edit_desc": "📝 Izoh",
        "edit_type": "🔁 Tur",
        "ask_amount": "Summani yuboring (faqat raqam):",
        "ask_desc": "Izohni yuboring:",
        "saved": "✅ Saqlandi!",
        "not_understood": "❌ Tushunmadim. Misol: `taksi 2000` yoki audio yuboring.",
        "voice_need_key": "🎙 Ovozni o‘qish uchun OPENAI_API_KEY kerak.",
        "app_link": "📱 Ilova: pastdagi tugma orqali oching.",
        "settings": "⚙️ Sozlamalar:\nTilni tanlang:",
        "type_expense": "Xarajat",
        "type_income": "Daromad",
        "type_debt": "Qarz",
    },
    "ru": {
        "welcome": "👋 Привет!\n\nЯ *Hamyon* — ваш финансовый помощник.\n"
                   "Быстро: `такси 2000`, `еда 45000`, `интернет 50000`\n"
                   "Или отправьте голосовое 🎙\n\nИспользуйте кнопки ниже 👇",
        "choose_lang": "Выберите язык / Choose language / Tilni tanlang:",
        "menu": "🏠 Меню",
        "btn_income": "➕ Доход",
        "btn_expense": "➖ Расход",
        "btn_debt": "📄 Долг",
        "btn_stats": "📊 Статистика",
        "btn_settings": "⚙️ Настройки",
        "btn_app": "📱 Приложение",
        "stats_1": "📊 1 день",
        "stats_7": "📆 7 дней",
        "stats_30": "🗓 30 дней",
        "csv": "⬇️ CSV",
        "confirm_title": "🧾 Черновик найден. Подтвердить?",
        "save": "✅ Сохранить",
        "edit": "✏️ Изменить",
        "cancel": "❌ Отмена",
        "edit_choose": "Что изменить?",
        "edit_cat": "🏷 Категория",
        "edit_amt": "💰 Сумма",
        "edit_desc": "📝 Описание",
        "edit_type": "🔁 Тип",
        "ask_amount": "Отправьте сумму (только цифры):",
        "ask_desc": "Отправьте описание:",
        "saved": "✅ Сохранено!",
        "not_understood": "❌ Не понял. Пример: `такси 2000` или голосом.",
        "voice_need_key": "🎙 Для распознавания нужен OPENAI_API_KEY.",
        "app_link": "📱 Приложение: откройте кнопкой ниже.",
        "settings": "⚙️ Настройки:\nВыберите язык:",
        "type_expense": "Расход",
        "type_income": "Доход",
        "type_debt": "Долг",
    },
    "en": {
        "welcome": "👋 Hi!\n\nI’m *Hamyon* — your money assistant.\n"
                   "Quick add: `taxi 2000`, `food 45000`, `internet 50000`\n"
                   "Or send a voice message 🎙\n\nUse buttons below 👇",
        "choose_lang": "Choose language / Tilni tanlang / Выберите язык:",
        "menu": "🏠 Menu",
        "btn_income": "➕ Income",
        "btn_expense": "➖ Expense",
        "btn_debt": "📄 Debt",
        "btn_stats": "📊 Stats",
        "btn_settings": "⚙️ Settings",
        "btn_app": "📱 App",
        "stats_1": "📊 1 day",
        "stats_7": "📆 7 days",
        "stats_30": "🗓 30 days",
        "csv": "⬇️ CSV",
        "confirm_title": "🧾 Draft found. Confirm?",
        "save": "✅ Save",
        "edit": "✏️ Edit",
        "cancel": "❌ Cancel",
        "edit_choose": "What to edit?",
        "edit_cat": "🏷 Category",
        "edit_amt": "💰 Amount",
        "edit_desc": "📝 Note",
        "edit_type": "🔁 Type",
        "ask_amount": "Send amount (numbers only):",
        "ask_desc": "Send description:",
        "saved": "✅ Saved!",
        "not_understood": "❌ I didn’t understand. Example: `taxi 2000` or voice.",
        "voice_need_key": "🎙 OPENAI_API_KEY required for voice transcription.",
        "app_link": "📱 App: open using the button below.",
        "settings": "⚙️ Settings:\nChoose language:",
        "type_expense": "Expense",
        "type_income": "Income",
        "type_debt": "Debt",
    },
}

# ---------------- Draft state ----------------
@dataclass
class Draft:
    tx_type: str = "expense"
    category_key: str = "other"
    amount: int = 0
    description: Optional[str] = None
    source: str = "text"

DRAFTS: Dict[Tuple[int, str], Draft] = {}  # (tg_id, draft_id) -> Draft
EDIT_MODE: Dict[int, Tuple[str, str]] = {} # tg_id -> (draft_id, field)

# ---------------- API helpers ----------------
async def api_post(path: str, json_body: dict):
    headers = {"X-API-SECRET": API_SECRET} if API_SECRET else {}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{API_URL}{path}", json=json_body, headers=headers)
        r.raise_for_status()
        return r.json()

async def api_get(path: str, params: dict):
    headers = {"X-API-SECRET": API_SECRET} if API_SECRET else {}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{API_URL}{path}", params=params, headers=headers)
        r.raise_for_status()
        return r.json(), r

async def get_lang(tg_id: int) -> str:
    try:
        data, _ = await api_get("/users/lang", {"telegram_id": tg_id})
        return data.get("language", "uz")
    except:
        return "uz"

async def set_lang(tg_id: int, lang: str):
    try:
        await api_post("/users/lang", {"telegram_id": tg_id, "language": lang})
    except:
        pass

# ---------------- UI keyboards ----------------
def kb_lang():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇺🇿 O‘zbek", callback_data="lang:uz"),
         InlineKeyboardButton("🇷🇺 Русский", callback_data="lang:ru"),
         InlineKeyboardButton("🇬🇧 English", callback_data="lang:en")]
    ])

def kb_menu(lang: str):
    t = I18N[lang]
    # Reply keyboard (like “startup product”)
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(t["btn_expense"]), KeyboardButton(t["btn_income"])],
            [KeyboardButton(t["btn_debt"]), KeyboardButton(t["btn_stats"])],
            [KeyboardButton(t["btn_settings"]), KeyboardButton(t["btn_app"])],
        ],
        resize_keyboard=True
    )

def kb_stats(lang: str):
    t = I18N[lang]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t["stats_1"], callback_data="stats:1"),
         InlineKeyboardButton(t["stats_7"], callback_data="stats:7")],
        [InlineKeyboardButton(t["stats_30"], callback_data="stats:30"),
         InlineKeyboardButton(t["csv"], callback_data="csv")]
    ])

def kb_confirm(lang: str, draft_id: str):
    t = I18N[lang]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t["save"], callback_data=f"draft:save:{draft_id}"),
         InlineKeyboardButton(t["edit"], callback_data=f"draft:edit:{draft_id}")],
        [InlineKeyboardButton(t["cancel"], callback_data=f"draft:cancel:{draft_id}")]
    ])

def kb_edit(lang: str, draft_id: str):
    t = I18N[lang]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t["edit_cat"], callback_data=f"edit:cat:{draft_id}"),
         InlineKeyboardButton(t["edit_amt"], callback_data=f"edit:amt:{draft_id}")],
        [InlineKeyboardButton(t["edit_desc"], callback_data=f"edit:desc:{draft_id}"),
         InlineKeyboardButton(t["edit_type"], callback_data=f"edit:type:{draft_id}")],
        [InlineKeyboardButton(t["cancel"], callback_data=f"draft:cancel:{draft_id}")]
    ])

def kb_pick_type(lang: str, draft_id: str):
    t = I18N[lang]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"➖ {t['type_expense']}", callback_data=f"picktype:expense:{draft_id}")],
        [InlineKeyboardButton(f"➕ {t['type_income']}", callback_data=f"picktype:income:{draft_id}")],
        [InlineKeyboardButton(f"📄 {t['type_debt']}", callback_data=f"picktype:debt:{draft_id}")],
        [InlineKeyboardButton(t["cancel"], callback_data=f"draft:cancel:{draft_id}")]
    ])

def kb_pick_cat(lang: str, draft_id: str):
    # simple set, extend later
    cats = [
        ("food", "🍕"), ("transport", "🚕"), ("internet", "📱"),
        ("health", "💊"), ("rent", "🏠"), ("utilities", "💡"), ("other", "🧾"),
    ]
    rows = []
    row = []
    for key, emoji in cats:
        row.append(InlineKeyboardButton(f"{emoji} {key}", callback_data=f"pickcat:{key}:{draft_id}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(I18N[lang]["cancel"], callback_data=f"draft:cancel:{draft_id}")])
    return InlineKeyboardMarkup(rows)

# ---------------- Format draft ----------------
def format_draft(lang: str, d: Draft, raw: str) -> str:
    t = I18N[lang]
    return (
        f"{t['confirm_title']}\n\n"
        f"Type: {d.tx_type}\n"
        f"Category: {d.category_key}\n"
        f"Amount: {d.amount} UZS\n"
        f"Desc: {d.description or '-'}\n"
        f"Raw: {raw}"
    )

# ---------------- Voice transcription (auto) ----------------
async def transcribe_voice(file_bytes: bytes) -> Optional[str]:
    if not OPENAI_API_KEY:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        resp = client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=("voice.ogg", file_bytes),
        )
        return (resp.text or "").strip()
    except:
        return None

# ---------------- Handlers ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    lang = await get_lang(tg_id)
    t = I18N[lang]

    # First time: offer language
    if lang not in ("uz","ru","en"):
        await update.message.reply_text(I18N["uz"]["choose_lang"], reply_markup=kb_lang())
        return

    await update.message.reply_text(
        t["welcome"],
        parse_mode="Markdown",
        reply_markup=kb_menu(lang)
    )

async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    lang = await get_lang(tg_id)
    await update.message.reply_text(I18N[lang]["settings"], reply_markup=kb_lang())

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    lang = await get_lang(tg_id)
    await update.message.reply_text("📊", reply_markup=kb_stats(lang))

async def on_lang_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    tg_id = q.from_user.id
    _, lang = q.data.split(":")
    await set_lang(tg_id, lang)
    t = I18N[lang]
    await q.message.reply_text(t["welcome"], parse_mode="Markdown", reply_markup=kb_menu(lang))

async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    tg_id = q.from_user.id
    lang = await get_lang(tg_id)
    t = I18N[lang]

    try:
        data = q.data

        # ----- Stats -----
        if data.startswith("stats:"):
            days = int(data.split(":")[1])
            if days == 1:
                d, _ = await api_get("/stats/today", {"telegram_id": tg_id})
                text = f"{t['stats_1']}\nXarajat/Expense: {d['expense']} UZS\nDaromad/Income: {d['income']} UZS\nQarz/Debt: {d['debt']} UZS\nCount: {d['count']}"
            else:
                d, _ = await api_get("/stats/range", {"telegram_id": tg_id, "days": days})
                text = f"📆 {days}\nXarajat/Expense: {d['expense']} UZS\nDaromad/Income: {d['income']} UZS\nQarz/Debt: {d['debt']} UZS\nCount: {d['count']}"
            await q.edit_message_text(text, reply_markup=kb_stats(lang))
            return

        if data == "csv":
            _, r = await api_get("/export/csv", {"telegram_id": tg_id})
            await q.message.reply_document(document=r.content, filename="transactions.csv", caption="⬇️ CSV")
            return

        # ----- Draft flow -----
        if data.startswith("draft:"):
            _, action, draft_id = data.split(":")
            key = (tg_id, draft_id)
            d = DRAFTS.get(key)

            if action == "cancel":
                if key in DRAFTS:
                    del DRAFTS[key]
                if tg_id in EDIT_MODE:
                    del EDIT_MODE[tg_id]
                await q.edit_message_text("✅ OK", reply_markup=None)
                return

            if not d:
                await q.message.reply_text("⚠️ Draft not found.")
                return

            if action == "edit":
                await q.edit_message_reply_markup(reply_markup=kb_edit(lang, draft_id))
                await q.message.reply_text(t["edit_choose"], reply_markup=kb_edit(lang, draft_id))
                return

            if action == "save":
                await api_post("/transactions", {
                    "telegram_id": tg_id,
                    "type": d.tx_type,
                    "amount": d.amount,
                    "category_key": d.category_key,
                    "description": d.description,
                    "source": d.source,
                })
                del DRAFTS[key]
                if tg_id in EDIT_MODE:
                    del EDIT_MODE[tg_id]
                await q.edit_message_text(t["saved"], reply_markup=None)
                return

        # ----- Edit menu -----
        if data.startswith("edit:"):
            _, field, draft_id = data.split(":")
            key = (tg_id, draft_id)
            if key not in DRAFTS:
                await q.message.reply_text("⚠️ Draft not found.")
                return

            if field == "cat":
                await q.message.reply_text("🏷 Category:", reply_markup=kb_pick_cat(lang, draft_id))
                return
            if field == "type":
                await q.message.reply_text("🔁 Type:", reply_markup=kb_pick_type(lang, draft_id))
                return
            if field == "amt":
                EDIT_MODE[tg_id] = (draft_id, "amount")
                await q.message.reply_text(t["ask_amount"])
                return
            if field == "desc":
                EDIT_MODE[tg_id] = (draft_id, "description")
                await q.message.reply_text(t["ask_desc"])
                return

        if data.startswith("pickcat:"):
            _, cat, draft_id = data.split(":")
            key = (tg_id, draft_id)
            d = DRAFTS.get(key)
            if not d:
                await q.message.reply_text("⚠️ Draft not found.")
                return
            d.category_key = cat
            await q.message.reply_text("✅ Updated.", reply_markup=kb_confirm(lang, draft_id))
            return

        if data.startswith("picktype:"):
            _, tx_type, draft_id = data.split(":")
            key = (tg_id, draft_id)
            d = DRAFTS.get(key)
            if not d:
                await q.message.reply_text("⚠️ Draft not found.")
                return
            d.tx_type = tx_type
            await q.message.reply_text("✅ Updated.", reply_markup=kb_confirm(lang, draft_id))
            return

    except Exception as e:
        await q.message.reply_text(f"⚠️ Error: {e}")

async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    lang = await get_lang(tg_id)
    t = I18N[lang]
    text = (update.message.text or "").strip()

    # Menu buttons
    if text in (t["btn_settings"], I18N["ru"]["btn_settings"], I18N["en"]["btn_settings"]):
        await update.message.reply_text(t["settings"], reply_markup=kb_lang())
        return
    if text in (t["btn_stats"], I18N["ru"]["btn_stats"], I18N["en"]["btn_stats"]):
        await update.message.reply_text("📊", reply_markup=kb_stats(lang))
        return
    if text in (t["btn_app"], I18N["ru"]["btn_app"], I18N["en"]["btn_app"]):
        # optional WebApp URL if you have it
        webapp_url = os.getenv("WEBAPP_URL", "")
        if webapp_url:
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("📱 Open App", url=webapp_url)]])
            await update.message.reply_text(t["app_link"], reply_markup=kb)
        else:
            await update.message.reply_text("WEBAPP_URL not set.")
        return
    if text in (t["btn_expense"], I18N["ru"]["btn_expense"], I18N["en"]["btn_expense"]):
        await update.message.reply_text("➖ OK. Send: `taksi 2000`", parse_mode="Markdown")
        return
    if text in (t["btn_income"], I18N["ru"]["btn_income"], I18N["en"]["btn_income"]):
        await update.message.reply_text("➕ OK. Send: `salary 5000000`", parse_mode="Markdown")
        return
    if text in (t["btn_debt"], I18N["ru"]["btn_debt"], I18N["en"]["btn_debt"]):
        await update.message.reply_text("📄 OK. Send: `debt 200000 friend`", parse_mode="Markdown")
        return

    # If user is editing a draft
    if tg_id in EDIT_MODE:
        draft_id, field = EDIT_MODE[tg_id]
        key = (tg_id, draft_id)
        d = DRAFTS.get(key)
        if not d:
            del EDIT_MODE[tg_id]
            await update.message.reply_text("⚠️ Draft not found.")
            return

        if field == "amount":
            digits = "".join(ch for ch in text if ch.isdigit())
            if not digits:
                await update.message.reply_text(t["ask_amount"])
                return
            d.amount = int(digits)
            del EDIT_MODE[tg_id]
            await update.message.reply_text("✅ Updated.", reply_markup=kb_confirm(lang, draft_id))
            return

        if field == "description":
            d.description = text
            del EDIT_MODE[tg_id]
            await update.message.reply_text("✅ Updated.", reply_markup=kb_confirm(lang, draft_id))
            return

    # Parse as expense text
    parsed = parse_one(text)
    if not parsed:
        await update.message.reply_text(t["not_understood"], parse_mode="Markdown")
        return

    cat, amount, desc = parsed
    draft_id = uuid.uuid4().hex[:8]
    d = Draft(tx_type="expense", category_key=normalize_category(cat), amount=amount, description=desc, source="text")
    DRAFTS[(tg_id, draft_id)] = d

    await update.message.reply_text(
        format_draft(lang, d, raw=text),
        reply_markup=kb_confirm(lang, draft_id)
    )

async def on_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    lang = await get_lang(tg_id)
    t = I18N[lang]

    voice = update.message.voice
    if not voice:
        return

    f = await context.bot.get_file(voice.file_id)
    b = await f.download_as_bytearray()

    text = await transcribe_voice(bytes(b))
    if not text:
        await update.message.reply_text(t["voice_need_key"])
        return

    parsed = parse_one(text)
    if not parsed:
        await update.message.reply_text(f"🎙 {text}\n\n{t['not_understood']}", parse_mode="Markdown")
        return

    cat, amount, desc = parsed
    draft_id = uuid.uuid4().hex[:8]
    d = Draft(tx_type="expense", category_key=normalize_category(cat), amount=amount, description=desc, source="voice")
    DRAFTS[(tg_id, draft_id)] = d

    await update.message.reply_text(
        format_draft(lang, d, raw=text),
        reply_markup=kb_confirm(lang, draft_id)
    )

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_cmd))
    app.add_handler(CommandHandler("today", today))
    app.add_handler(CommandHandler("range", range_cmd))
    app.add_handler(CommandHandler("csv", csv_cmd))

    app.add_handler(CallbackQueryHandler(on_callback))

    app.add_handler(MessageHandler(filters.VOICE, on_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
main()
