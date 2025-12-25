import os, io, csv, datetime as dt
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, UploadFile, File, Header, HTTPException
from pydantic import BaseModel

from db import q_exec, q_one, q_all
from nlp import parse_multi

API_SECRET = os.getenv("API_SECRET", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

app = FastAPI(title="Hamyon API")

def auth(x_api_secret: Optional[str]):
    if API_SECRET and (x_api_secret != API_SECRET):
        raise HTTPException(status_code=401, detail="Bad secret")

def ensure_user(telegram_id: int, lang: str = "uz"):
    q_exec(
        "insert into users (telegram_id, lang) values (%s,%s) on conflict (telegram_id) do nothing",
        (telegram_id, lang),
    )

class TxIn(BaseModel):
    telegram_id: int
    type: str  # expense|income|debt
    amount: int
    category_key: str
    description: Optional[str] = None
    merchant: Optional[str] = None
    occurred_at: Optional[str] = None
    source: str = "manual"
    raw_text: Optional[str] = None

@app.post("/transactions")
def create_tx(tx: TxIn, x_api_secret: Optional[str] = Header(default=None)):
    auth(x_api_secret)
    ensure_user(tx.telegram_id)

    occurred = None
    if tx.occurred_at:
        occurred = dt.datetime.fromisoformat(tx.occurred_at.replace("Z","+00:00"))
    else:
        occurred = dt.datetime.now(dt.timezone.utc)

    q_exec(
        """
        insert into transactions
          (telegram_id,type,amount,category_key,description,merchant,occurred_at,source,raw_text)
        values (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (tx.telegram_id, tx.type, tx.amount, tx.category_key, tx.description, tx.merchant, occurred, tx.source, tx.raw_text)
    )

    # budget check (monthly)
    month_start = occurred.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    spent_row = q_one(
        """
        select coalesce(sum(amount),0)
        from transactions
        where telegram_id=%s and type='expense' and category_key=%s
          and occurred_at >= %s
        """,
        (tx.telegram_id, tx.category_key, month_start)
    )
    spent = int(spent_row[0]) if spent_row else 0

    bud = q_one(
        """
        select monthly_limit
        from budgets
        where telegram_id=%s and category_key=%s and enabled=true
        """,
        (tx.telegram_id, tx.category_key)
    )
    budget_exceeded = False
    limit_val = None
    if bud:
        limit_val = int(bud[0])
        if spent > limit_val:
            budget_exceeded = True

    return {"ok": True, "budget_exceeded": budget_exceeded, "spent": spent, "limit": limit_val}

@app.get("/stats/today")
def stats_today(telegram_id: int, x_api_secret: Optional[str] = Header(default=None)):
    auth(x_api_secret)
    ensure_user(telegram_id)

    now = dt.datetime.now(dt.timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    rows = q_all(
        """
        select type, coalesce(sum(amount),0), count(*)
        from transactions
        where telegram_id=%s and occurred_at >= %s
        group by type
        """,
        (telegram_id, start)
    )
    totals = {"expense":0, "income":0, "debt":0, "count":0}
    for t, s, c in rows:
        totals[t] = int(s)
        totals["count"] += int(c)
    return totals

@app.get("/stats/range")
def stats_range(telegram_id: int, days: int = 7, x_api_secret: Optional[str] = Header(default=None)):
    auth(x_api_secret)
    ensure_user(telegram_id)

    now = dt.datetime.now(dt.timezone.utc)
    start = now - dt.timedelta(days=days)

    rows = q_all(
        """
        select type, coalesce(sum(amount),0)
        from transactions
        where telegram_id=%s and occurred_at >= %s
        group by type
        """,
        (telegram_id, start)
    )
    totals = {"expense":0, "income":0, "debt":0}
    for t, s in rows:
        totals[t] = int(s)
    return totals

@app.get("/export/csv")
def export_csv(telegram_id: int, x_api_secret: Optional[str] = Header(default=None)):
    auth(x_api_secret)
    ensure_user(telegram_id)

    rows = q_all(
        """
        select occurred_at, type, amount, category_key, merchant, description, source
        from transactions
        where telegram_id=%s
        order by occurred_at desc
        limit 5000
        """,
        (telegram_id,)
    )
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["occurred_at","type","amount","category_key","merchant","description","source"])
    for r in rows:
        w.writerow(list(r))
    return out.getvalue()

class BudgetIn(BaseModel):
    telegram_id: int
    category_key: Optional[str] = None  # null = overall
    monthly_limit: int
    enabled: bool = True

@app.post("/budgets")
def set_budget(b: BudgetIn, x_api_secret: Optional[str] = Header(default=None)):
    auth(x_api_secret)
    ensure_user(b.telegram_id)
    q_exec(
        """
        insert into budgets (telegram_id, category_key, monthly_limit, enabled)
        values (%s,%s,%s,%s)
        on conflict (telegram_id, category_key) do update
        set monthly_limit=excluded.monthly_limit, enabled=excluded.enabled
        """,
        (b.telegram_id, b.category_key, b.monthly_limit, b.enabled)
    )
    return {"ok": True}

# -------- AI parsing endpoints (voice & receipt) --------

def require_openai():
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=400, detail="OPENAI_API_KEY missing on API service")

@app.post("/parse/text")
def parse_text(payload: Dict[str, Any], x_api_secret: Optional[str] = Header(default=None)):
    auth(x_api_secret)
    text = (payload.get("text") or "").strip()
    items = parse_multi(text)
    # items: (cat, amount, desc)
    return {"items":[{"category_key":c,"amount":a,"description":d} for (c,a,d) in items]}

@app.post("/parse/receipt")
async def parse_receipt(file: UploadFile = File(...), x_api_secret: Optional[str] = Header(default=None)):
    auth(x_api_secret)
    require_openai()

    content = await file.read()

    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)

    # Vision extraction (startup-grade JSON)
    resp = client.responses.create(
        model="gpt-4o-mini",
        input=[{
          "role":"user",
          "content":[
            {"type":"input_text","text":
             "Extract receipt data as JSON with keys: merchant (string), date_iso (string|null), total (number|null), currency (string|null), items (array of {name, qty, price, amount}). If unsure, put null. Respond ONLY JSON."},
            {"type":"input_image","image_url": f"data:image/jpeg;base64,{__import__('base64').b64encode(content).decode()}"}
          ]
        }]
    )
    text = resp.output_text.strip()

    # Try parse JSON safely
    import json
    try:
        data = json.loads(text)
    except Exception:
        data = {"merchant": None, "date_iso": None, "total": None, "currency": None, "items": [], "raw": text}

    # Category suggestion heuristic
    merchant = (data.get("merchant") or "").lower()
    suggested = "food" if any(k in merchant for k in ["korzinka","havas","magnum","market","super"]) else "misc"

    return {"ok": True, "data": data, "suggested_category": suggested}

@app.post("/parse/voice")
async def parse_voice(file: UploadFile = File(...), x_api_secret: Optional[str] = Header(default=None)):
    auth(x_api_secret)
    require_openai()

    content = await file.read()

    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)

    # Transcribe
    tr = client.audio.transcriptions.create(
        model="gpt-4o-mini-transcribe",
        file=(file.filename or "voice.ogg", content),
    )
    text = (tr.text or "").strip()

    # Parse into structured items (fallback: regex)
    items = parse_multi(text)

    return {"ok": True, "text": text, "items":[{"category_key":c,"amount":a,"description":d} for (c,a,d) in items]}
