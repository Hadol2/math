"""기출문제 DB API 라우터."""

import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from app.db import (
    DIFFICULTIES, EXAM_TYPES, UNITS,
    delete_problem, get_problem, insert_problem,
    list_problems, update_problem,
)

router = APIRouter(prefix="/db", tags=["database"])

_IMG_DIR = Path(__file__).parent.parent / "static" / "problem_images"
_IMG_DIR.mkdir(parents=True, exist_ok=True)

_ALLOWED_IMG = {"image/jpeg", "image/png", "image/webp"}


# ── 메타 ──────────────────────────────────────────────────────────────

@router.get("/meta")
def meta():
    """프론트엔드 필터 옵션용 목록."""
    return {"units": UNITS, "difficulties": DIFFICULTIES, "exam_types": EXAM_TYPES}


# ── 문제 목록/필터 ────────────────────────────────────────────────────

@router.get("/problems")
def get_problems(
    year: Optional[int] = None,
    exam_type: Optional[str] = None,
    unit: Optional[str] = None,
    difficulty: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    if limit > 200:
        raise HTTPException(400, "limit 최대 200")
    rows, total = list_problems(year, exam_type, unit, difficulty, limit, offset)
    return {"total": total, "problems": rows}


# ── 문제 단건 ─────────────────────────────────────────────────────────

@router.get("/problems/{problem_id}")
def get_one(problem_id: int):
    p = get_problem(problem_id)
    if not p:
        raise HTTPException(404, "문제를 찾을 수 없습니다")
    return p


# ── 문제 추가 (이미지 + 메타데이터) ──────────────────────────────────

@router.post("/problems", status_code=status.HTTP_201_CREATED)
async def add_problem(
    image: UploadFile = File(...),
    year: int = Form(...),
    exam_type: str = Form(...),
    number: int = Form(...),
    score: int = Form(3),
    answer: str = Form(""),
    unit: str = Form(""),
    difficulty: str = Form(""),
    has_figure: bool = Form(False),
    text: str = Form(""),
    latex: str = Form(""),
    notes: str = Form(""),
):
    if image.content_type not in _ALLOWED_IMG:
        raise HTTPException(415, f"지원하지 않는 형식: {image.content_type}")
    img_bytes = await image.read()
    if len(img_bytes) > 10 * 1024 * 1024:
        raise HTTPException(413, "이미지 10MB 초과")

    ext = image.filename.rsplit(".", 1)[-1] if "." in image.filename else "png"
    filename = f"{uuid.uuid4().hex}.{ext}"
    (_IMG_DIR / filename).write_bytes(img_bytes)

    problem_id = insert_problem({
        "year":       year,
        "exam_type":  exam_type,
        "number":     number,
        "score":      score,
        "image_path": f"/static/problem_images/{filename}",
        "answer":     answer or None,
        "unit":       unit or None,
        "difficulty": difficulty or None,
        "has_figure": has_figure,
        "text":       text or None,
        "latex":      latex or None,
        "notes":      notes or None,
    })
    return {"id": problem_id}


# ── 문제 메타데이터 수정 ──────────────────────────────────────────────

@router.patch("/problems/{problem_id}")
def patch_problem(problem_id: int, data: dict):
    if not update_problem(problem_id, data):
        raise HTTPException(404, "문제를 찾을 수 없습니다")
    return {"ok": True}


# ── 문제 삭제 ─────────────────────────────────────────────────────────

@router.delete("/problems/{problem_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_problem(problem_id: int):
    p = get_problem(problem_id)
    if not p:
        raise HTTPException(404, "문제를 찾을 수 없습니다")
    # 이미지 파일 삭제
    img_path = Path(__file__).parent.parent / p["image_path"].lstrip("/")
    if img_path.exists():
        img_path.unlink()
    delete_problem(problem_id)
