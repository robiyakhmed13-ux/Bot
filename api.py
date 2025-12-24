import os
import csv
import io
from datetime import date, datetime, timedelta, timezone

from fastapi import FastAPI, HTTPException, Header, Response
from pydantic import BaseModel

from db import ensure_user, fetchall, fetchone, execute

app = FastAPI(title="Hamyon API")

# VERY IMPORTANT:
# For real security, verify Telegram initData.
# For now we use a simple shared secret header for bot/app.
API_SECRET = os.getenv("API_SECRET", "")

def check_secret(x_api_secret: str | None):
    if API_SECRET and x_api_secret != API_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")


class TxCreate(BaseModel):
    telegram_id: int
    type: str                 # expense|income|debt
    amount: int               # positive
    category_key: str
    description: str | None = None
    source: str = "manual"    # manual|text|voice|receipt


@app.get("/health")
async def health():
    return {"ok": True}


@app.post("/transactions")
async def create_transaction(payload: TxCreate, x_api_secret: str | None = Header(default=None)):
    check_secret(x_api_secret)

    if payload.type not in ("expense", "income", "debt"):
        raise HTTPException(400, "Invalid type")
    if payload.amount <= 0:
        raise HTTPException(400, "Amount must be > 0")

    user_id = await ensure_user(payload.telegram_id)

    await execute(
        """
        INSERT INTO transactions (user_id, type, amount, category_key, description, source)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (user_id, payload.type, payload.amount, payload.category_key, payload.description, payload.source),
    )
    return {"ok": True}


@app.get("/transactions")
async def list_transactions(telegram_id: int, limit: int = 100, x_api_secret: str | None = Header(default=None)):
    check_secret(x_api_secret)

    user_id = await ensure_user(telegram_id)
    rows = await fetchall(
        """
        SELECT id, type, amount, category_key, description, source, created_at
        FROM transactions
        WHERE user_id=%s
        ORDER BY created_at DESC
        LIMIT %s
        """,
        (user_id, limit),
    )
    return [
        {
            "id": r[0], "type": r[1], "amount": r[2], "category_key": r[3],
            "description": r[4], "source": r[5], "created_at": r[6].isoformat()
        }
        for r in rows
    ]


def day_bounds_utc():
    now = datetime.now(timezone.utc)
    start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    return start, end


@app.get("/stats/today")
async def stats_today(telegram_id: int, x_api_secret: str | None = Header(default=None)):
    check_secret(x_api_secret)

    user_id = await ensure_user(telegram_id)
    start, end = day_bounds_utc()

    rows = await fetchall(
        """
        SELECT type, COALESCE(SUM(amount),0) AS total, COUNT(*)
        FROM transactions
        WHERE user_id=%s AND created_at >= %s AND created_at < %s
        GROUP BY type
        """,
        (user_id, start, end),
    )

    out = {"expense": 0, "income": 0, "debt": 0, "count": 0}
    for t, total, cnt in rows:
        out[t] = int(total)
        out["count"] += int(cnt)
    return out


@app.get("/stats/range")
async def stats_range(telegram_id: int, days: int = 7, x_api_secret: str | None = Header(default=None)):
    check_secret(x_api_secret)

    user_id = await ensure_user(telegram_id)
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)

    rows = await fetchall(
        """
        SELECT type, COALESCE(SUM(amount),0) AS total
        FROM transactions
        WHERE user_id=%s AND created_at >= %s
        GROUP BY type
        """,
        (user_id, start),
    )

    out = {"expense": 0, "income": 0, "debt": 0}
    for t, total in rows:
        out[t] = int(total)
    return out


@app.get("/export/csv")
async def export_csv(telegram_id: int, x_api_secret: str | None = Header(default=None)):
    check_secret(x_api_secret)

    user_id = await ensure_user(telegram_id)
    rows = await fetchall(
        """
        SELECT id, type, amount, category_key, COALESCE(description,''), source, created_at
        FROM transactions
        WHERE user_id=%s
        ORDER BY created_at DESC
        """,
        (user_id,),
    )

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id","type","amount","category","description","source","created_at"])
    for r in rows:
        w.writerow([r[0], r[1], r[2], r[3], r[4], r[5], r[6].isoformat()])

    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=transactions.csv"},
    )
