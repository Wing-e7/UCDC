from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

import jwt
from fastapi import HTTPException, status

from .config import get_settings


def encode_consent_token(
    *,
    consent_id: str,
    user_id: str,
    agent_id: str,
    consent_hash: str,
    expires_at: datetime,
) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    # SQLite often drops tzinfo on DateTime(timezone=True). Treat naive datetimes as UTC.
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    payload: Dict[str, Any] = {
        "iss": settings.consent_issuer,
        "sub": user_id,
        "consent_id": consent_id,
        "agent_id": agent_id,
        "consent_hash": consent_hash,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    # PyJWT may return bytes depending on version; normalize to str.
    if isinstance(token, bytes):
        return token.decode("utf-8")
    return token


def decode_consent_token(token: str) -> Dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "iss", "sub"]},
            issuer=settings.consent_issuer,
        )
        return payload
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Consent token expired",
        ) from e
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid consent token",
        ) from e

