import os
from psycopg_pool import ConnectionPool

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("Missing DATABASE_URL")

pool = ConnectionPool(conninfo=DATABASE_URL, min_size=1, max_size=5)

def q_one(sql: str, params: tuple = ()):
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            return row

def q_all(sql: str, params: tuple = ()):
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()

def q_exec(sql: str, params: tuple = ()):
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            conn.commit()
