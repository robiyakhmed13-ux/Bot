import os
import csv
import io
from datetime import date, datetime, timedelta
from typing import Optional, Literal

from fastapi import FastAPI, Header, HTTPException, Response
from pydantic import BaseModel, Field

from db import pool, open_pool

API_SECRET = os.getenv("API_SECRET", "")  # optional (same in bot & app)

app = FastAPI(title="Hamyon API")

class TxIn(BaseModel):
    telegram_id: int
    type: Literal["expense", "income", "debt"] = "expense"
    amount: int = Field(ge=0)
    category_key: str
    description: Optional[str] = None
    merchant: Optional[str] = None
    tx_date: Optional[date] = None
    source: str = "text"

class LangIn(BaseModel):
    telegram_id: int
    language: Literal["uz","ru","en"]

def require_secret(x_api_secret: Optional[str]):
    if API_SECRET and x_api_secret != API_SECRET:
        raise HTTPException(status_code=401, detail="Invalid API secret")

@app.on_event("startup")
async def startup():
    await open_pool()

@app.get("/health")
async def health():
    return {"ok": True}

@app.post("/users/lang")
async def set_lang(payload: LangIn, x_api_secret: Optional[str] = Header(default=None, alias="X-API-SECRET")):
    require_secret(x_api_secret)
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                insert into users (telegram_id, language)
                values (%s, %s)
                on conflict (telegram_id)
                do update set language = excluded.language
                """,
                (payload.telegram_id, payload.language),
            )
    return {"ok": True, "language": payload.language}

@app.get("/users/lang")
async def get_lang(telegram_id: int, x_api_secret: Optional[str] = Header(default=None, alias="X-API-SECRET")):
    require_secret(x_api_secret)
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("select language from users where telegram_id=%s", (telegram_id,))
            row = await cur.fetchone()
    return {"language": (row[0] if row else "uz")}

@app.post("/transactions")
async def create_tx(payload: TxIn, x_api_secret: Optional[str] = Header(default=None, alias="X-API-SECRET")):
    require_secret(x_api_secret)
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                insert into transactions
                (telegram_id, type, amount, category_key, description, merchant, tx_date, source)
                values (%s,%s,%s,%s,%s,%s,%s,%s)
                returning id
                """,
                (
                    payload.telegram_id,
                    payload.type,
                    payload.amount,
                    payload.category_key,
                    payload.description,
                    payload.merchant,
                    payload.tx_date,
                    payload.source,
                ),
            )
            row = await cur.fetchone()
    return {"ok": True, "id": str(row[0])}

@app.get("/stats/today")
async def stats_today(telegram_id: int, x_api_secret: Optional[str] = Header(default=None, alias="X-API-SECRET")):
    require_secret(x_api_secret)
    today = date.today()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                select
                  coalesce(sum(case when type='expense' then amount end),0) as expense,
                  coalesce(sum(case when type='income' then amount end),0) as income,
                  coalesce(sum(case when type='debt' then amount end),0) as debt,
                  count(*) as count
                from transactions
                where telegram_id=%s
                  and coalesce(tx_date, created_at::date) = %s
                """,
                (telegram_id, today),
            )
            row = await cur.fetchone()
    return {"expense": row[0], "income": row[1], "debt": row[2], "count": row[3]}

@app.get("/stats/range")
async def stats_range(telegram_id: int, days: int = 7, x_api_secret: Optional[str] = Header(default=None, alias="X-API-SECRET")):
    require_secret(x_api_secret)
    since = date.today() - timedelta(days=days-1)
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                select
                  coalesce(sum(case when type='expense' then amount end),0) as expense,
                  coalesce(sum(case when type='income' then amount end),0) as income,
                  coalesce(sum(case when type='debt' then amount end),0) as debt,
                  count(*) as count
                from transactions
                where telegram_id=%s
                  and coalesce(tx_date, created_at::date) >= %s
                """,
                (telegram_id, since),
            )
            row = await cur.fetchone()
    return {"expense": row[0], "income": row[1], "debt": row[2], "count": row[3], "since": str(since)}

@app.get("/export/csv")
async def export_csv(telegram_id: int, x_api_secret: Optional[str] = Header(default=None, alias="X-API-SECRET")):
    require_secret(x_api_secret)
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                select created_at, type, amount, category_key, description, merchant, coalesce(tx_date, created_at::date) as day, source
                from transactions
                where telegram_id=%s
                order by created_at desc
                limit 2000
                """,
                (telegram_id,),
            )
            rows = await cur.fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["created_at","type","amount","category","description","merchant","date","source"])
    for r in rows:
        writer.writerow(list(r))

    content = output.getvalue().encode("utf-8")
    return Response(content=content, media_type="text/csv")
