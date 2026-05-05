"""FastAPI 앱 — 수학 시험지 생성 웹 서비스."""

import json, logging, os, sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, File, Form, HTTPException, Response, UploadFile, status
from fastapi.staticfiles import StaticFiles

from rendering import _LATEX_OK, export_to_pdf_bytes
from app.extract import extract_problems
from app.variants import generate_variants

log = logging.getLogger("mathweb")
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logging.getLogger("fonttools").setLevel(logging.WARNING)
logging.getLogger("fpdf").setLevel(logging.WARNING)

app = FastAPI(title="수학 시험지 생성기", version="0.1")

# ── 정적 파일 ───────────────────────────────────────────────────────
_STATIC = Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=_STATIC, html=True), name="static")


@app.on_event("startup")
async def _startup():
    log.info("LaTeX 렌더링: %s", "pdflatex ✓" if _LATEX_OK else "matplotlib fallback")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        log.warning("ANTHROPIC_API_KEY 미설정 — /extract, /variants 비활성")


# ── 헬스체크 ────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"ok": True, "latex": _LATEX_OK}


# ── 이미지 → 문제 JSON ──────────────────────────────────────────────

_ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

@app.post("/extract")
async def extract(file: UploadFile = File(...)):
    """업로드된 이미지에서 문제를 추출하여 JSON 반환."""
    if file.content_type not in _ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"지원하지 않는 파일 형식: {file.content_type}",
        )
    image_bytes = await file.read()
    if len(image_bytes) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="파일 크기 20MB 초과")

    try:
        problems = extract_problems(image_bytes, media_type=file.content_type)
    except Exception as e:
        log.exception("extract 오류")
        raise HTTPException(status_code=500, detail=str(e))

    return {"problems": problems}


# ── 문제 JSON → 변형 ────────────────────────────────────────────────

@app.post("/variants")
async def variants(
    problem_json: str = Form(...),
    n: int = Form(3),
):
    """단일 문제 JSON → n개 변형 문제 리스트."""
    try:
        problem = json.loads(problem_json)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"JSON 파싱 오류: {e}")

    if n < 1 or n > 10:
        raise HTTPException(status_code=400, detail="n은 1~10 사이")

    try:
        result = generate_variants(problem, n=n)
    except Exception as e:
        log.exception("variants 오류")
        raise HTTPException(status_code=500, detail=str(e))

    return {"variants": result}


# ── 시험지 PDF 다운로드 ─────────────────────────────────────────────

@app.post("/pdf")
async def pdf(
    exam_json: str = Form(...),
    with_answers: bool = Form(False),
):
    """exam_info + problems JSON → PDF bytes."""
    try:
        data = json.loads(exam_json)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"JSON 파싱 오류: {e}")

    exam_info = {
        "title":    data.get("title", "수학 시험지"),
        "subtitle": data.get("subtitle", ""),
    }
    problems = data.get("problems", [])
    if not problems:
        raise HTTPException(status_code=400, detail="problems 배열이 비어 있습니다")

    try:
        pdf_bytes = export_to_pdf_bytes(exam_info, problems, with_answers=with_answers)
    except Exception as e:
        log.exception("PDF 생성 오류")
        raise HTTPException(status_code=500, detail=str(e))

    from urllib.parse import quote
    raw_name = exam_info["title"].replace(" ", "_") + ".pdf"
    safe_name = quote(raw_name, safe='')
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_name}"},
    )
