from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from fastapi import Depends, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from config import auth_settings

log = logging.getLogger("auth")

USERS_FILE = Path(__file__).parent / "data" / "users.json"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserCreate(BaseModel):
    username: str
    password: str
    display_name: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str


class UserPublic(BaseModel):
    id: str
    username: str
    display_name: str
    role: str
    created_at: str


def _load_users() -> list[dict]:
    if USERS_FILE.exists():
        try:
            return json.loads(USERS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
    return []


def _save_users(users: list[dict]):
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    USERS_FILE.write_text(json.dumps(users, indent=2, ensure_ascii=False), encoding="utf-8")


def _hash_password(password: str) -> str:
    return pwd_context.hash(password)


def _verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _create_token(user_id: str, username: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=auth_settings.token_expire_minutes)
    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, auth_settings.secret_key, algorithm=auth_settings.algorithm)


def _decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, auth_settings.secret_key, algorithms=[auth_settings.algorithm])
        return payload
    except JWTError:
        return None


def _set_auth_cookie(response: JSONResponse, token: str):
    max_age = auth_settings.token_expire_minutes * 60
    response.set_cookie(
        key="token",
        value=token,
        max_age=max_age,
        httponly=True,
        samesite="lax",
        path="/",
    )


def _clear_auth_cookie(response: JSONResponse):
    response.delete_cookie(key="token", path="/")


def ensure_admin_user():
    users = _load_users()
    admin_exists = any(u.get("role") == "admin" for u in users)
    if not admin_exists:
        admin_user = {
            "id": str(uuid.uuid4()),
            "username": auth_settings.admin_username,
            "password_hash": _hash_password(auth_settings.admin_password),
            "display_name": "Administrador",
            "role": "admin",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        users.append(admin_user)
        _save_users(users)
        log.info("Admin user created: %s", auth_settings.admin_username)


def authenticate_user(username: str, password: str) -> Optional[dict]:
    users = _load_users()
    for u in users:
        if u["username"] == username and _verify_password(password, u["password_hash"]):
            return u
    return None


def register_user(username: str, password: str, display_name: str = None) -> dict:
    users = _load_users()
    if any(u["username"] == username for u in users):
        return {"error": "Nome de usuario ja existe"}

    if len(username) < 3:
        return {"error": "Usuario deve ter pelo menos 3 caracteres"}
    if len(password) < 4:
        return {"error": "Senha deve ter pelo menos 4 caracteres"}

    user = {
        "id": str(uuid.uuid4()),
        "username": username,
        "password_hash": _hash_password(password),
        "display_name": display_name or username,
        "role": "user",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    users.append(user)
    _save_users(users)
    return {"id": user["id"], "username": user["username"], "role": user["role"]}


def list_users() -> list[UserPublic]:
    users = _load_users()
    return [
        UserPublic(
            id=u["id"],
            username=u["username"],
            display_name=u.get("display_name", u["username"]),
            role=u["role"],
            created_at=u["created_at"],
        )
        for u in users
    ]


def delete_user(user_id: str) -> bool:
    users = _load_users()
    original_len = len(users)
    users = [u for u in users if u["id"] != user_id]
    if len(users) < original_len:
        _save_users(users)
        return True
    return False


def get_current_user(request: Request) -> Optional[dict]:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        payload = _decode_token(token)
        if payload:
            return payload

    cookie_token = request.cookies.get("token")
    if cookie_token:
        payload = _decode_token(cookie_token)
        if payload:
            return payload

    return None
