"""기출문제 DB API 라우터."""

import random
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Body, File, Form, HTTPException, UploadFile, status
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
    img_path = Path(__file__).parent.parent / p["image_path"].lstrip("/")
    if img_path.exists():
        img_path.unlink()
    delete_problem(problem_id)


# ── 자동 시험지 구성 ──────────────────────────────────────────────────

@router.post("/compose")
def compose_exam(body: dict = Body(...)):
    """
    범위·난이도 비율 기반 자동 문제 구성.
    body: {
      units: ["대수", ...],          # 빈 배열 = 전체
      year_from: 2020,               # optional
      year_to: 2026,                 # optional
      difficulty_ratio: {상:30, 중:50, 하:20},  # 합계 100
      n_total: 30,
    }
    """
    units       = body.get("units", [])
    year_from   = body.get("year_from")
    year_to     = body.get("year_to")
    ratio       = body.get("difficulty_ratio", {"상": 34, "중": 33, "하": 33})
    n_total     = int(body.get("n_total", 30))

    # 각 난이도별 목표 문항 수 계산
    diffs  = ["상", "중", "하"]
    totals = {d: round(n_total * ratio.get(d, 0) / 100) for d in diffs}
    # 반올림 오차 보정
    diff = n_total - sum(totals.values())
    totals["중"] += diff

    selected   = []
    shortfalls = {}

    for d in diffs:
        needed = totals[d]
        if needed <= 0:
            continue
        pool, _ = list_problems(difficulty=d, limit=2000)
        if units:
            pool = [p for p in pool if p.get("unit") in units]
        if year_from:
            pool = [p for p in pool if (p.get("year") or 0) >= year_from]
        if year_to:
            pool = [p for p in pool if (p.get("year") or 0) <= year_to]

        random.shuffle(pool)
        picked = pool[:needed]
        selected.extend(picked)

        if len(picked) < needed:
            shortfalls[d] = {"needed": needed, "available": len(picked)}

    # 문항 번호 순서로 정렬 (연도 desc, 번호 asc)
    selected.sort(key=lambda p: (-p.get("year", 0), p.get("number", 0)))
    return {"problems": selected, "shortfalls": shortfalls}
