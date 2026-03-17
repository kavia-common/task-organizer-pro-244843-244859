from contextlib import contextmanager
from typing import Iterator

import psycopg
from psycopg.rows import dict_row

from src.core.config import get_settings


# PUBLIC_INTERFACE
@contextmanager
def get_db_conn() -> Iterator[psycopg.Connection]:
    """Get a psycopg connection with dict row factory.

    Uses DATABASE_URL from environment variables.
    """
    settings = get_settings()
    conn = psycopg.connect(settings.database_url, row_factory=dict_row)
    try:
        yield conn
    finally:
        conn.close()
