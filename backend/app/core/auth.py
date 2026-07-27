from __future__ import annotations

import base64
import hmac
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from loguru import logger
from sqlalchemy import select

from app.core.config import settings
from app.core.redis_store import (
    blacklist_jti as blacklist_jti,
    get_login_attempts,
    get_refresh_token_data,
    increment_login_attempts,
    is_jti_blacklisted,
    reset_login_attempts,
    revoke_all_user_refresh_tokens as revoke_all_user_refresh_tokens,
    revoke_refresh_token as revoke_refresh_token,
    store_refresh_token,
)

security = HTTPBearer(auto_error=False)

LOGIN_MAX_ATTEMPTS = 5
LOGIN_LOCKOUT_SECONDS = 300
REFRESH_TOKEN_BYTES = 32
REFRESH_EXPIRE_DAYS = 30


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_token(user_id: str, expire_minutes: int | None = None) -> str:
    expire = expire_minutes or settings.jwt_expire_minutes
    jti = secrets.token_hex(16)
    payload = {
        "sub": user_id,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=expire),
        "jti": jti,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


async def create_refresh_token(user_id: str) -> tuple[str, str]:
    token = secrets.token_hex(REFRESH_TOKEN_BYTES)
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_EXPIRE_DAYS)
    await store_refresh_token(token, user_id, expires_at)
    return token, expires_at.isoformat()


async def verify_refresh_token(token: str) -> str | None:
    data = await get_refresh_token_data(token)
    if data is None:
        return None
    return data["user_id"]


async def get_user_by_username(username: str):
    from app.core.database import async_session_factory
    from app.core.models import UserRecord

    async with async_session_factory() as session:
        row = await session.execute(
            select(UserRecord).where(UserRecord.username == username)
        )
        return row.scalar_one_or_none()


async def get_user_by_id(user_id: str):
    from app.core.database import async_session_factory
    from app.core.models import UserRecord

    async with async_session_factory() as session:
        return await session.get(UserRecord, user_id)


async def get_user_by_sso(provider: str, sso_id: str):
    from app.core.database import async_session_factory
    from app.core.models import UserRecord

    async with async_session_factory() as session:
        row = await session.execute(
            select(UserRecord).where(
                UserRecord.sso_provider == provider,
                UserRecord.sso_id == sso_id,
            )
        )
        return row.scalar_one_or_none()


async def create_user(username: str, password: str, is_admin: bool = False, **extra) -> str:
    from app.core.database import async_session_factory
    from app.core.models import UserRecord

    user_id = str(uuid.uuid4())
    record = UserRecord(
        id=user_id,
        username=username,
        password_hash=hash_password(password) if password else "",
        is_admin=is_admin,
        **{k: v for k, v in extra.items() if k in ("totp_secret", "is_2fa_enabled", "sso_provider", "sso_id")},
    )
    async with async_session_factory() as session:
        session.add(record)
        await session.commit()
    logger.info(f"Created user: {username} (admin={is_admin})")
    return user_id


async def verify_credentials(username: str, password: str) -> str | None:
    import time as _time

    attempts, lock_until = await get_login_attempts(username)
    if lock_until > _time.time():
        logger.warning(f"Login locked for {username} until {lock_until:.0f}")
        return None

    if username == settings.admin_username and password == settings.admin_password:
        await reset_login_attempts(username)
        user = await get_user_by_username(username)
        if user is not None:
            return user.id
        user_id = await create_user(username, password, is_admin=True)
        return user_id

    user = await get_user_by_username(username)
    if user is None:
        await increment_login_attempts(username, LOGIN_MAX_ATTEMPTS, LOGIN_LOCKOUT_SECONDS)
        return None

    if not verify_password(password, user.password_hash):
        await increment_login_attempts(username, LOGIN_MAX_ATTEMPTS, LOGIN_LOCKOUT_SECONDS)
        return None

    await reset_login_attempts(username)
    return user.id


def channel_username(channel: str, external_id: str) -> str:
    """Stable username for an external-channel identity (e.g. WhatsApp phone)."""
    return f"{channel}:{external_id}"


async def get_or_create_channel_user(channel: str, external_id: str) -> str:
    """Look up (or create) the user backing an external channel identity.

    Used for WhatsApp/n8n conversations so each phone number maps to a stable,
    isolated user with its own documents and chat history. The account has a
    random password and cannot log in through the web UI.
    """
    username = channel_username(channel, external_id)
    existing = await get_user_by_username(username)
    if existing is not None:
        return existing.id
    random_password = secrets.token_hex(REFRESH_TOKEN_BYTES)
    return await create_user(username, random_password, is_admin=False)


async def seed_admin_user() -> str:
    existing = await get_user_by_username(settings.admin_username)
    if existing is not None:
        return existing.id
    user_id = await create_user(settings.admin_username, settings.admin_password, is_admin=True)
    return user_id


async def seed_demo_user() -> str | None:
    """Seed the public demo account (credentials from config, hashed in DB).

    Idempotent: if the user exists its password is re-synced to the configured
    value so demos keep working even if it was changed. Returns None when
    demo seeding is disabled.
    """
    if not settings.demo_user_enabled:
        return None

    existing = await get_user_by_username(settings.demo_username)
    if existing is not None:
        # Keep the demo password in sync with config (non-static, hashed).
        from app.core.database import async_session_factory
        from app.core.models import UserRecord

        async with async_session_factory() as session:
            user = await session.get(UserRecord, existing.id)
            if user is not None:
                user.password_hash = hash_password(settings.demo_password)
                await session.commit()
        return existing.id

    return await create_user(settings.demo_username, settings.demo_password, is_admin=False)


async def verify_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str | None:
    api_key = request.headers.get("X-API-Key")
    if api_key and hmac.compare_digest(api_key, settings.api_key):
        return "api-key-user"

    if not credentials:
        # Sin credenciales → 403 (convención HTTPBearer de FastAPI). Los tokens
        # expirados o inválidos a continuación devuelven 401 para renovar.
        raise HTTPException(status_code=403, detail="No autenticado")
    try:
        payload = jwt.decode(
            credentials.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        jti = payload.get("jti")
        if jti and await is_jti_blacklisted(jti):
            raise HTTPException(status_code=401, detail="Token revocado")
        return payload.get("sub")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")


verify_jwt = verify_auth


# ── Autenticación de Dos Factores (2FA) ──────────────────────────────────


def generate_totp_secret() -> str:
    return base64.b32encode(os.urandom(20)).decode("utf-8")


def get_totp_uri(secret: str, username: str, issuer: str = "ONE AI Agent") -> str:
    import urllib.parse

    params = urllib.parse.urlencode({
        "secret": secret,
        "issuer": issuer,
        "algorithm": "SHA1",
        "digits": 6,
        "period": 30,
    })
    return f"otpauth://totp/{urllib.parse.quote(issuer)}:{urllib.parse.quote(username)}?{params}"


def verify_totp(secret: str, code: str) -> bool:
    try:
        import pyotp

        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=1)
    except ImportError:
        logger.error("pyotp no está instalado — no se puede verificar el 2FA")
        return False


async def verify_2fa(user_id: str, code: str) -> bool:
    user = await get_user_by_id(user_id)
    if user is None or not user.totp_secret or not user.is_2fa_enabled:
        return False
    return verify_totp(user.totp_secret, code)


async def enable_2fa(user_id: str, code: str) -> bool:
    user = await get_user_by_id(user_id)
    if user is None or not user.totp_secret:
        return False
    if not verify_totp(user.totp_secret, code):
        return False
    from app.core.database import async_session_factory

    async with async_session_factory() as session:
        user = await session.get(type(user), user_id)
        user.is_2fa_enabled = True
        await session.commit()
    return True


async def disable_2fa(user_id: str) -> None:
    from app.core.database import async_session_factory

    async with async_session_factory() as session:
        from app.core.models import UserRecord

        user = await session.get(UserRecord, user_id)
        if user:
            user.totp_secret = None
            user.is_2fa_enabled = False
            await session.commit()


# ── SSO / OAuth2 ─────────────────────────────────────────────────────────


def _sso_state() -> str:
    return secrets.token_hex(32)


def google_oauth_url(state: str) -> str:
    if not settings.google_client_id:
        raise HTTPException(status_code=501, detail="Google OAuth2 no está configurado")
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": f"{settings.public_url}/auth/sso/google/callback",
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
    }
    import urllib.parse

    return f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"


def github_oauth_url(state: str) -> str:
    if not settings.github_client_id:
        raise HTTPException(status_code=501, detail="GitHub OAuth2 no está configurado")
    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": f"{settings.public_url}/auth/sso/github/callback",
        "scope": "read:user user:email",
        "state": state,
    }
    import urllib.parse

    return f"https://github.com/login/oauth/authorize?{urllib.parse.urlencode(params)}"


async def exchange_google_code(code: str) -> dict:
    import httpx

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": f"{settings.public_url}/auth/sso/google/callback",
                "grant_type": "authorization_code",
            },
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        tokens = resp.json()

        user_resp = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        user_resp.raise_for_status()
        return user_resp.json()


async def exchange_github_code(code: str) -> dict:
    import httpx

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
            },
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        tokens = resp.json()

        user_resp = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {tokens['access_token']}", "Accept": "application/vnd.github.v3+json"},
        )
        user_resp.raise_for_status()
        return user_resp.json()


async def sso_login_or_register(provider: str, sso_id: str, email: str, name: str) -> str:
    existing = await get_user_by_sso(provider, sso_id)
    if existing is not None:
        return existing.id

    username_base = email.split("@")[0] if email else name.replace(" ", "_").lower()
    username = username_base
    counter = 1
    while await get_user_by_username(username) is not None:
        username = f"{username_base}_{counter}"
        counter += 1

    user_id = await create_user(
        username=username,
        password="",
        sso_provider=provider,
        sso_id=sso_id,
    )
    return user_id


# ── Registro de Auditoría (Audit Log) ────────────────────────────────────


async def audit_log(
    user_id: str | None,
    action: str,
    resource: str | None = None,
    resource_id: str | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
):
    from app.core.database import async_session_factory
    from app.core.models import AuditLogRecord

    record = AuditLogRecord(
        id=str(uuid.uuid4()),
        user_id=user_id,
        action=action,
        resource=resource,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    try:
        async with async_session_factory() as session:
            session.add(record)
            await session.commit()
    except Exception as e:
        logger.warning(f"Error al escribir en el registro de auditoría: {e}")
