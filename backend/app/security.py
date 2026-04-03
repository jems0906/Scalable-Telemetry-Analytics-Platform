from datetime import datetime, timedelta, timezone
from typing import Callable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

bearer_scheme = HTTPBearer(auto_error=True)


def authenticate_user(username: str, password: str) -> str | None:
    users = {
        settings.auth_admin_username: {"password": settings.auth_admin_password, "role": "operator"},
        settings.auth_operator_username: {"password": settings.auth_operator_password, "role": "operator"},
        settings.auth_viewer_username: {"password": settings.auth_viewer_password, "role": "viewer"},
    }

    user = users.get(username)
    if not user:
        return None

    if password != user["password"]:
        return None

    return str(user["role"])


def create_access_token(subject: str, role: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_access_token_expires_minutes)
    payload = {
        "sub": subject,
        "role": role,
        "exp": int(expires_at.timestamp()),
        "iat": int(datetime.now(timezone.utc).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def verify_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        subject = payload.get("sub")
        role = payload.get("role")
        if not subject or not role:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
        return payload
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> str:
    payload = verify_access_token(credentials.credentials)
    return str(payload.get("sub"))


def get_current_role(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> str:
    payload = verify_access_token(credentials.credentials)
    return str(payload.get("role"))


def require_roles(*allowed_roles: str) -> Callable:
    def dependency(role: str = Depends(get_current_role)) -> str:
        if role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return role

    return dependency
