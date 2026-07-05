"""
Authentication helpers: password hashing (stdlib pbkdf2), JWT issue/verify,
and FastAPI dependencies to resolve the current user for HTTP and WebSocket.
"""
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

import database
import models

# For a local tool a static secret is fine; override via env in real deployments.
SECRET_KEY = os.environ.get("DATAGEN_SECRET_KEY", "datagen-dev-secret-change-me")
ALGORITHM = "HS256"
TOKEN_TTL_HOURS = 24 * 7  # a week

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)


# --- Password hashing (no external deps; pbkdf2-hmac-sha256) ---
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000).hex()
    return f"{salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, digest = stored.split("$", 1)
    except ValueError:
        return False
    check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000).hex()
    return hmac.compare_digest(check, digest)


# --- JWT ---
def create_access_token(user: models.User) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=TOKEN_TTL_HOURS)
    payload = {"sub": str(user.id), "username": user.username, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _user_from_token(token: str, db: Session):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
    except Exception:
        return None
    return db.query(models.User).filter(models.User.id == user_id).first()


# --- Dependencies ---
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(database.get_db),
) -> models.User:
    creds_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise creds_error
    user = _user_from_token(token, db)
    if not user:
        raise creds_error
    return user


def get_user_from_raw_token(token: str, db: Session):
    """Used by the WebSocket endpoint, which passes the token as a query param."""
    if not token:
        return None
    return _user_from_token(token, db)
