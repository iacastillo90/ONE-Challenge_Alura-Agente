from datetime import datetime, timezone

import jwt as pyjwt
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.auth import (
    audit_log,
    create_refresh_token,
    create_token,
    disable_2fa,
    enable_2fa,
    generate_totp_secret,
    get_totp_uri,
    get_user_by_id,
    get_user_by_username,
    revoke_all_user_refresh_tokens,
    revoke_refresh_token,
    verify_2fa,
    verify_credentials,
    verify_jwt,
    verify_refresh_token,
    sso_login_or_register,
    google_oauth_url,
    github_oauth_url,
    exchange_google_code,
    exchange_github_code,
    _sso_state,
)
from app.core.cache import rag_cache
from app.core.config import settings
from app.core.redis_store import check_register_rate, increment_register_count

router = APIRouter()

TWO_FA_MAX_ATTEMPTS = 5
TWO_FA_LOCKOUT_SECONDS = 300


async def _check_2fa_rate(user_id: str) -> None:
    key = f"2fa_rate:{user_id}"
    attempts = await rag_cache.get(key) or 0
    if attempts >= TWO_FA_MAX_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Demasiados intentos de 2FA. Por favor, reintente más tarde.")
    await rag_cache.set(key, attempts + 1, ttl=TWO_FA_LOCKOUT_SECONDS)


class LoginRequest(BaseModel):
    username: str
    password: str
    totp_code: str | None = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    refresh_token: str
    expires_at: str
    requires_2fa: bool = False


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=128)
    password: str = Field(..., min_length=6, max_length=256)


class RegisterResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    expires_at: str = ""


class UserResponse(BaseModel):
    user_id: str
    username: str
    is_admin: bool
    is_2fa_enabled: bool


class TokenQuotaResponse(BaseModel):
    used: int
    budget: int
    remaining: int
    pct: float


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str
    expires_at: str


class LogoutResponse(BaseModel):
    status: str


class TOTPSetupResponse(BaseModel):
    secret: str
    uri: str
    qr_code_url: str


class TOTPVerifyRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6)


class TOTPEnableRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6)


class SSOAuthURLResponse(BaseModel):
    url: str


class SSOCallbackRequest(BaseModel):
    code: str
    state: str


def _set_refresh_cookie(response, refresh_token_value: str, expires_at: str):
    response.set_cookie(
        key="refresh_token",
        value=refresh_token_value,
        httponly=True,
        secure=settings.refresh_cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=30 * 24 * 3600,
        path="/auth/refresh",
    )


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, http_request: Request):
    from fastapi.responses import JSONResponse

    user_id = await verify_credentials(request.username, request.password)
    if user_id is None:
        await audit_log(None, "login.failed", resource="user", details={"username": request.username},
                        ip_address=http_request.client.host if http_request.client else None)
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    user = await get_user_by_id(user_id)
    if user and user.is_2fa_enabled:
        if not request.totp_code:
            return LoginResponse(
                access_token="", user_id=user_id, username=user.username,
                refresh_token="", expires_at="", requires_2fa=True,
            )
        if not await verify_2fa(user_id, request.totp_code):
            raise HTTPException(status_code=401, detail="Código de 2FA inválido")

    token = create_token(user_id)
    refresh_token_value, expires_at = await create_refresh_token(user_id)
    username = user.username if user else request.username

    await audit_log(user_id, "login.success", resource="user", resource_id=user_id,
                    ip_address=http_request.client.host if http_request.client else None,
                    user_agent=http_request.headers.get("user-agent"))

    response = JSONResponse(content=LoginResponse(
        access_token=token,
        user_id=user_id,
        username=username,
        refresh_token="",
        expires_at=expires_at,
    ).model_dump())
    _set_refresh_cookie(response, refresh_token_value, expires_at)
    return response


@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(request: RegisterRequest, http_request: Request):
    if not settings.enable_registration:
        raise HTTPException(status_code=403, detail="El registro público de usuarios está deshabilitado")

    client_ip = http_request.client.host if http_request.client else "desconocido"
    ok, remaining = await check_register_rate(client_ip)
    if not ok:
        await audit_log(None, "register.rate_limited", resource="user",
                        details={"username": request.username, "ip": client_ip},
                        ip_address=client_ip)
        raise HTTPException(status_code=429, detail=f"Límite de registros alcanzado. Quedan {remaining} registros permitidos esta hora.")

    existing = await get_user_by_username(request.username)
    if existing is not None:
        raise HTTPException(status_code=409, detail="El nombre de usuario ya se encuentra registrado")

    from app.core.auth import create_user

    user_id = await create_user(request.username, request.password)
    await increment_register_count(client_ip)

    token = create_token(user_id)
    refresh_token_value, expires_at = await create_refresh_token(user_id)
    await audit_log(user_id, "register", resource="user", resource_id=user_id,
                    ip_address=client_ip,
                    user_agent=http_request.headers.get("user-agent"))

    from fastapi.responses import JSONResponse

    response = JSONResponse(
        status_code=201,
        content=RegisterResponse(
            access_token=token,
            user_id=user_id,
            username=request.username,
            expires_at=expires_at,
        ).model_dump(),
    )
    _set_refresh_cookie(response, refresh_token_value, expires_at)
    return response


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(request: RefreshRequest | None = None, http_request: Request = None):
    from fastapi.responses import JSONResponse

    rt = request.refresh_token if request and request.refresh_token else http_request.cookies.get("refresh_token", "")
    if not rt:
        raise HTTPException(status_code=401, detail="No se proporcionó un token de actualización")

    user_id = await verify_refresh_token(rt)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Token de actualización inválido o expirado")

    await revoke_refresh_token(rt)

    new_token = create_token(user_id)
    new_refresh, expires_at = await create_refresh_token(user_id)

    await audit_log(user_id, "token.refresh", resource="auth",
                    ip_address=http_request.client.host if http_request.client else None)

    response = JSONResponse(content=RefreshResponse(
        access_token=new_token,
        refresh_token="",
        expires_at=expires_at,
    ).model_dump())
    _set_refresh_cookie(response, new_refresh, expires_at)
    return response


@router.post("/logout")
async def logout(
    request: Request,
    user_id: str = Depends(verify_jwt),
):
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        try:
            payload = pyjwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
            jti = payload.get("jti")
            if jti:
                exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc) if payload.get("exp") else datetime.now(timezone.utc)
                from app.core.auth import blacklist_jti
                await blacklist_jti(jti, exp)
        except Exception:
            pass
    await revoke_all_user_refresh_tokens(user_id)

    await audit_log(user_id, "logout", resource="auth",
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"))

    return LogoutResponse(status="logged_out")


@router.get("/token/quota", response_model=TokenQuotaResponse)
async def token_quota_status(user_id: str = Depends(verify_jwt)):
    from app.core.token_quota import token_quota as tq
    usage = await tq.get_usage(user_id)
    return TokenQuotaResponse(**usage)


@router.get("/me", response_model=UserResponse)
async def me(user_id: str = Depends(verify_jwt)):
    user = await get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return UserResponse(
        user_id=user.id,
        username=user.username,
        is_admin=user.is_admin,
        is_2fa_enabled=user.is_2fa_enabled,
    )


# ── Autenticación 2FA ───────────────────────────────────────────────────


@router.post("/2fa/setup")
async def setup_2fa(user_id: str = Depends(verify_jwt)):
    user = await get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    from app.core.database import async_session_factory
    from app.core.models import UserRecord

    secret = generate_totp_secret()
    async with async_session_factory() as session:
        db_user = await session.get(UserRecord, user_id)
        db_user.totp_secret = secret
        db_user.is_2fa_enabled = False
        await session.commit()

    uri = get_totp_uri(secret, user.username)
    return TOTPSetupResponse(
        secret=secret,
        uri=uri,
        qr_code_url=f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={uri}",
    )


@router.post("/2fa/enable")
async def enable_2fa_endpoint(request: TOTPEnableRequest, user_id: str = Depends(verify_jwt)):
    await _check_2fa_rate(user_id)
    ok = await enable_2fa(user_id, request.code)
    if not ok:
        raise HTTPException(status_code=400, detail="Código 2FA inválido o 2FA no configurado")
    await audit_log(user_id, "2fa.enabled", resource="user", resource_id=user_id)
    return {"status": "2fa_enabled"}


@router.post("/2fa/disable")
async def disable_2fa_endpoint(request: TOTPVerifyRequest, user_id: str = Depends(verify_jwt)):
    await _check_2fa_rate(user_id)
    if not await verify_2fa(user_id, request.code):
        raise HTTPException(status_code=400, detail="Código 2FA inválido")
    await disable_2fa(user_id)
    await audit_log(user_id, "2fa.disabled", resource="user", resource_id=user_id)
    return {"status": "2fa_disabled"}


@router.post("/2fa/verify")
async def verify_2fa_endpoint(request: TOTPVerifyRequest, user_id: str = Depends(verify_jwt)):
    await _check_2fa_rate(user_id)
    ok = await verify_2fa(user_id, request.code)
    return {"verified": ok}


# ── SSO / OAuth2 ──────────────────────────────────────────────────────────


@router.get("/sso/google", response_model=SSOAuthURLResponse)
async def sso_google():
    state = _sso_state()
    url = google_oauth_url(state)
    return SSOAuthURLResponse(url=url)


@router.get("/sso/google/callback")
async def sso_google_callback(code: str, state: str, http_request: Request):
    try:
        user_data = await exchange_google_code(code)
        sso_id = user_data.get("id")
        email = user_data.get("email", "")
        name = user_data.get("name", email.split("@")[0])
        if not sso_id:
            raise HTTPException(status_code=400, detail="No se pudo obtener la información de usuario desde Google")
        user_id = await sso_login_or_register("google", str(sso_id), email, name)
        token = create_token(user_id)
        refresh_token, expires_at = await create_refresh_token(user_id)
        await audit_log(user_id, "sso.login", resource="auth", details={"provider": "google"},
                        ip_address=http_request.client.host if http_request.client else None)
        return LoginResponse(
            access_token=token, user_id=user_id, username=name,
            refresh_token=refresh_token, expires_at=expires_at,
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Falló la autenticación SSO con Google: {e}")


@router.get("/sso/github", response_model=SSOAuthURLResponse)
async def sso_github():
    state = _sso_state()
    url = github_oauth_url(state)
    return SSOAuthURLResponse(url=url)


@router.get("/sso/github/callback")
async def sso_github_callback(code: str, state: str, http_request: Request):
    try:
        user_data = await exchange_github_code(code)
        sso_id = str(user_data.get("id"))
        email = user_data.get("email", "") or f"{user_data.get('login', 'user')}@github.local"
        name = user_data.get("name") or user_data.get("login", "user")
        if not sso_id:
            raise HTTPException(status_code=400, detail="No se pudo obtener la información de usuario desde GitHub")
        user_id = await sso_login_or_register("github", sso_id, email, name)
        token = create_token(user_id)
        refresh_token, expires_at = await create_refresh_token(user_id)
        await audit_log(user_id, "sso.login", resource="auth", details={"provider": "github"},
                        ip_address=http_request.client.host if http_request.client else None)
        return LoginResponse(
            access_token=token, user_id=user_id, username=name,
            refresh_token=refresh_token, expires_at=expires_at,
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Falló la autenticación SSO con GitHub: {e}")
