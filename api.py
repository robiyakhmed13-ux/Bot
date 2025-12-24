import os
from datetime import datetime, timezone
from typing import Optional

import psycopg
from psycopg_pool import ConnectionPool
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if not DATABASE_URL:
    raise ValueError("Missing DATABASE_URL")

pool = ConnectionPool(conninfo=DATABASE_URL, min_size=1, max_size=5, open=True)

app = FastAPI()

# allow your Vercel miniapp domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later to your real domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TxIn(BaseModel):
    telegram_id: int
    name: str = "User"
    description: str
    amount: int
    category_id: str
    source: str = "app"
    created_at: Optional[str] = None  # ISO

def ensure_user(telegram_id: int, name: str) -> tuple:
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, balance FROM public.users WHERE telegram_id=%s", (telegram_id,))
            row = cur.fetchone()
            if row:
                return row
            cur.execute(
                "INSERT INTO public.users (telegram_id, name) VALUES (%s,%s) RETURNING id, balance",
                (telegram_id, name),
            )
            row = cur.fetchone()
        conn.commit()
    return row

@app.get("/api/sync")
def sync(telegram_id: int):
    user_row = None
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, telegram_id, name, balance, language FROM public.users WHERE telegram_id=%s", (telegram_id,))
            user_row = cur.fetchone()

            if not user_row:
                return {"user": None, "transactions": []}

            cur.execute(
                """
                SELECT id, description, amount, category_id, source, created_at
                FROM public.transactions
                WHERE user_telegram_id=%s
                ORDER BY created_at DESC
                LIMIT 200
                """,
                (telegram_id,),
            )
            tx = cur.fetchall()

    user = {"id": str(user_row[0]), "telegram_id": user_row[1], "name": user_row[2], "balance": user_row[3], "language": user_row[4]}
    transactions = [
        {
            "id": str(r[0]),
            "description": r[1],
            "amount": r[2],
            "category_id": r[3],
            "source": r[4],
            "created_at": r[5].isoformat() if r[5] else None,
        }
        for r in tx
    ]
    return {"user": user, "transactions": transactions}

@app.post("/api/transactions")
def create_tx(payload: TxIn):
    user_id, _bal = ensure_user(payload.telegram_id, payload.name)

    created_at = datetime.now(timezone.utc)
    if payload.created_at:
        try:
            created_at = datetime.fromisoformat(payload.created_at.replace("Z", "+00:00"))
        except:
            pass

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.transactions
                  (user_id, user_telegram_id, description, amount, category_id, source, created_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                RETURNING id
                """,
                (user_id, payload.telegram_id, payload.description, payload.amount, payload.category_id, payload.source, created_at),
            )
            tx_id = cur.fetchone()[0]

            cur.execute(
                "UPDATE public.users SET balance = balance + %s, updated_at=NOW() WHERE id=%s RETURNING balance",
                (payload.amount, user_id),
            )
            new_balance = cur.fetchone()[0]
        conn.commit()

    return {"id": str(tx_id), "balance": int(new_balance)}
