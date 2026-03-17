from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from src.core.config import get_settings
from src.core.security import decode_token
from src.db.connection import get_db_conn
from src.repos.users import UsersRepo


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# PUBLIC_INTERFACE
def get_conn():
    """FastAPI dependency that yields a DB connection."""
    with get_db_conn() as conn:
        yield conn


# PUBLIC_INTERFACE
def get_current_user(conn=Depends(get_conn), token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """FastAPI dependency that returns the currently authenticated user (dict)."""
    settings = get_settings()
    try:
        payload = decode_token(token=token, secret=settings.jwt_secret, algorithm=settings.jwt_algorithm)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    sub: Optional[str] = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")

    user = UsersRepo(conn).get_by_id(sub)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user
