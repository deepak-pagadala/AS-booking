import os, contextlib
import psycopg
from dotenv import load_dotenv

load_dotenv()                                           # loads DATABASE_URL
DATABASE_URL = os.getenv("DATABASE_URL")                # postgresql://user:pw@host/db

# one global connection pool (thread-safe, quick)
_pool = psycopg.ConnectionPool.open(
    conninfo=DATABASE_URL,
    min_size=1,
    max_size=5,
)

@contextlib.contextmanager
def get_conn():
    with _pool.connection() as conn:
        with conn.cursor() as cur:
            yield cur
