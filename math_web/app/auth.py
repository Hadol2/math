"""JWT 인증 유틸리티."""
import os
from datetime import datetime, timedelta, timezone

from fastapi import Cookie, Depends, HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext

SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-please-set-in-env")
ALGORITHM  = "HS256"
TOKEN_DAYS = 30

FREE_DAILY_LIMIT = 10  # free 플랜 하루 변형 생성 횟수

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _pwd.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)


def create_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=TOKEN_DAYS)
    return jwt.encode({"sub": str(user_id), "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


def _decode_token(token: str) -> int:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="인증 필요")


def get_current_user(access_token: str | None = Cookie(default=None)):
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="로그인이 필요합니다")
    user_id = _decode_token(access_token)
    from app.db import get_user
    user = get_user(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="사용자를 찾을 수 없습니다")
    return user


def get_current_user_optional(access_token: str | None = Cookie(default=None)):
    if not access_token:
        return None
    try:
        user_id = _decode_token(access_token)
        from app.db import get_user
        return get_user(user_id)
    except HTTPException:
        return None


def set_cookie(response, token: str) -> None:
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=TOKEN_DAYS * 24 * 3600,
        samesite="lax",
        secure=False,  # HTTPS 적용 후 True로 변경
    )
