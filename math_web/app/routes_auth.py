"""인증 라우터 — /auth/*."""
from fastapi import APIRouter, Depends, Form, HTTPException, Response, status

from app.auth import (
    FREE_DAILY_LIMIT,
    create_token,
    get_current_user,
    hash_password,
    set_cookie,
    verify_password,
)
from app.db import create_user, get_user_by_email

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup")
def signup(
    response: Response,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
):
    if get_user_by_email(email):
        raise HTTPException(status_code=400, detail="이미 가입된 이메일입니다")
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="비밀번호는 8자 이상이어야 합니다")
    user_id = create_user(name=name, email=email, password_hash=hash_password(password))
    set_cookie(response, create_token(user_id))
    return {"ok": True}


@router.post("/login")
def login(
    response: Response,
    email: str = Form(...),
    password: str = Form(...),
):
    user = get_user_by_email(email)
    if not user or not verify_password(password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다")
    set_cookie(response, create_token(user["id"]))
    return {"ok": True, "name": user["name"], "plan": user["plan"]}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    return {"ok": True}


@router.get("/me")
def me(user=Depends(get_current_user)):
    return {
        "id":             user["id"],
        "name":           user["name"],
        "email":          user["email"],
        "plan":           user["plan"],
        "variants_today": user["variants_today"],
        "daily_limit":    FREE_DAILY_LIMIT if user["plan"] == "free" else None,
    }
