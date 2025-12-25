import os
from psycopg_pool import AsyncConnectionPool

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("Missing DATABASE_URL (Railway Postgres).")

pool = AsyncConnectionPool(conninfo=DATABASE_URL, min_size=1, max_size=10)

async def open_pool():
    # No .opened attribute in this psycopg_pool version
    await pool.open()

async def close_pool():
    await pool.close()
