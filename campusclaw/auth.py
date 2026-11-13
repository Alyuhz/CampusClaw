from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from functools import wraps
from typing import Any, TypeVar

import jwt
from flask import Blueprint, current_app, g, request
from werkzeug.security import check_password_hash

from .db import (
    create_session,
    get_active_session,
    get_user_by_username,
    revoke_session,
    utc_now,
)
from .http import ApiError, api_response

bp = Blueprint("auth", __name__, url_prefix="/api/v1")
F = TypeVar("F", bound=Callable[..., Any])


def _invalid_credentials() -> ApiError:
    return ApiError(code=1101, message="用户名或口令错误", status=401)


def _bearer_token() -> str:
    authorization = request.headers.get("Authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise ApiError(code=1100, message="未登录", status=401)
    return token


def authenticate() -> None:
    if getattr(g, "user", None) is not None:
        return
    try:
        payload = jwt.decode(
            _bearer_token(), current_app.config["JWT_SECRET"], algorithms=["HS256"]
        )
    except jwt.PyJWTError as error:
        raise ApiError(code=1100, message="未登录", status=401) from error
    jti = payload.get("jti")
    session = get_active_session(jti) if isinstance(jti, str) else None
    if session is None:
        raise ApiError(code=1100, message="未登录", status=401)
    g.user, g.token_id = session, jti


def protect_api() -> None:
    if not request.path.startswith("/api/v1/") or request.endpoint == "auth.login":
        return
    authenticate()


def auth_required(*roles: str) -> Callable[[F], F]:
    def decorator(view: F) -> F:
        @wraps(view)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            authenticate()
            if roles and g.user["role"] not in roles:
                raise ApiError(code=1204, message="无权执行此操作", status=403)
            return view(*args, **kwargs)

        return wrapped  # type: ignore[return-value]

    return decorator


@bp.post("/auth/login")
def login() -> tuple:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise _invalid_credentials()
    username = payload.get("username")
    password = payload.get("password")
    if not isinstance(username, str) or not isinstance(password, str):
        raise _invalid_credentials()
    if not username or len(username) > 80 or not password or len(password) > 256:
        raise _invalid_credentials()

    user = get_user_by_username(username)
    if user is None or not check_password_hash(user["password_hash"], password):
        raise _invalid_credentials()

    now = datetime.now(UTC)
    expires = now + timedelta(seconds=int(current_app.config["TOKEN_TTL_SECONDS"]))
    jti = uuid.uuid4().hex
    token = jwt.encode(
        {"sub": user["username"], "jti": jti, "iat": now, "exp": expires},
        current_app.config["JWT_SECRET"],
        algorithm="HS256",
    )
    create_session(
        jti=jti,
        user_id=int(user["id"]),
        expires_at=expires.isoformat(),
        created_at=utc_now(),
    )
    return api_response(
        {
            "token": token,
            "user": {
                "username": user["username"],
                "role": user["role"],
                "class_id": user["class_id"],
            },
        }
    )


@bp.get("/me")
@auth_required()
def me() -> tuple:
    return api_response(
        {
            "username": g.user["username"],
            "role": g.user["role"],
            "class_id": g.user["class_id"],
        }
    )


@bp.post("/auth/logout")
@auth_required()
def logout() -> tuple:
    revoke_session(g.token_id)
    return api_response({"revoked": True})


@bp.get("/audit-logs")
@auth_required("teacher")
def audit_logs() -> tuple:
    from .db import query_operations

    allowed = {"actor_id", "start", "end", "limit", "offset"}
    if set(request.args) - allowed:
        raise ApiError(code=1101, message="非法筛选", status=400)
    try:
        actor_id = int(request.args["actor_id"]) if "actor_id" in request.args else None
        limit, offset = int(request.args.get("limit", "50")), int(request.args.get("offset", "0"))
        start, end = request.args.get("start", "0000"), request.args.get("end", "9999")
        if not 1 <= limit <= 100 or offset < 0 or (actor_id is not None and actor_id < 1):
            raise ValueError()
        for key in ("start", "end"):
            if key in request.args:
                value = datetime.fromisoformat(request.args[key])
                if value.tzinfo is None:
                    raise ValueError()
                if key == "start":
                    start = value.astimezone(UTC).replace(microsecond=0).isoformat()
                else:
                    end = value.astimezone(UTC).replace(microsecond=0).isoformat()
        if start > end:
            raise ValueError()
    except ValueError as error:
        raise ApiError(code=1101, message="非法筛选", status=400) from error
    return api_response(
        {"items": query_operations(g.user["class_id"], actor_id, start, end, limit, offset)}
    )
