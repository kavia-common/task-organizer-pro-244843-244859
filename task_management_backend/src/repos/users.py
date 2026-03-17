from typing import Any, Dict, Optional

from src.core.security import hash_password, verify_password


class UsersRepo:
    def __init__(self, conn):
        self.conn = conn

    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        with self.conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE email = %s;", (email,))
            return cur.fetchone()

    def get_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        with self.conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE id = %s;", (user_id,))
            return cur.fetchone()

    def create(self, *, email: str, password: str) -> Dict[str, Any]:
        password_hash = hash_password(password)
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (email, password_hash)
                VALUES (%s, %s)
                RETURNING *;
                """.strip(),
                (email, password_hash),
            )
            user = cur.fetchone()
        self.conn.commit()
        return user

    def authenticate(self, *, email: str, password: str) -> Optional[Dict[str, Any]]:
        user = self.get_by_email(email)
        if not user:
            return None
        if not verify_password(password, user["password_hash"]):
            return None
        return user
