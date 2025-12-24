import os
from psycopg_pool import AsyncConnectionPool

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("Missing DATABASE_URL")

pool = AsyncConnectionPool(DATABASE_URL, open=True)


async def fetchone(query: str, params=()):
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(query, params)
            return await cur.fetchone()


async def fetchall(query: str, params=()):
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(query, params)
            return await cur.fetchall()


async def execute(query: str, params=()):
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(query, params)


async def ensure_user(telegram_id: int, full_name: str | None = None):
    row = await fetchone("SELECT id FROM users WHERE telegram_id=%s", (telegram_id,))
    if row:
        return row[0]

    await execute(
        "INSERT INTO users (telegram_id, full_name) VALUES (%s, %s)",
        (telegram_id, full_name),
    )
    row2 = await fetchone("SELECT id FROM users WHERE telegram_id=%s", (telegram_id,))
    return row2[0]
