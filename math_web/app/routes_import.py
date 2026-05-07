"""PDF 일괄 입력 API."""

import base64
import io
import json
import logging
import os
import subprocess
import tempfile
import uuid
from pathlib import Path

import anthropic
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from PIL import Image

from app.db import insert_problem

router = APIRouter(prefix="/db", tags=["import"])
log = logging.getLogger("mathweb.import")

_IMG_DIR = Path(__file__).parent.parent / "static" / "problem_images"
_IMG_DIR.mkdir(parents=True, exist_ok=True)

_DETECT_PROMPT = """이 이미지는 한국 수학 시험지 한 페이지입니다.
페이지에 있는 모든 수학 문제를 찾아 아래 JSON 형식으로만 응답하세요.

{
  "problems": [
    {
      "number": 1,
      "top_pct": 5.0,
      "bottom_pct": 32.0,
      "text": "문제 전체 텍스트 (한국어, 선지 제외)",
      "latex": "핵심 수식 LaTeX (없으면 빈 문자열)",
      "choices": ["① 보기1", "② 보기2", "③ 보기3", "④ 보기4", "⑤ 보기5"],
      "answer": "정답 (보이는 경우만, 없으면 빈 문자열)",
      "has_figure": false
    }
  ]
}

규칙:
- top_pct, bottom_pct: 이미지 총 높이 기준 문제 영역 위치(%), 선지·그림 포함
- choices: 5지선다 객관식만. 단답형/서술형이면 빈 배열 []
- has_figure: 그래프·도형·표가 포함된 문제면 true
- 순수 JSON만 반환, 마크다운 코드블록 없이
"""


@router.post("/import-pdf")
async def import_pdf(
    pdf: UploadFile = File(...),
    year: int = Form(...),
    exam_type: str = Form(...),
):
    """PDF 시험지 → 문제별 자동 분리 + 텍스트/LaTeX 추출."""
    if not (pdf.filename or "").lower().endswith(".pdf"):
        raise HTTPException(400, "PDF 파일만 지원합니다")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(500, "ANTHROPIC_API_KEY 미설정")

    pdf_bytes = await pdf.read()
    if len(pdf_bytes) > 50 * 1024 * 1024:
        raise HTTPException(413, "PDF 50MB 초과")

    with tempfile.TemporaryDirectory() as tmp_dir:
        pdf_path = Path(tmp_dir) / "exam.pdf"
        pdf_path.write_bytes(pdf_bytes)

        out_prefix = Path(tmp_dir) / "page"
        result = subprocess.run(
            ["pdftoppm", "-r", "200", "-png", str(pdf_path), str(out_prefix)],
            capture_output=True, timeout=120,
        )
        if result.returncode != 0:
            raise HTTPException(500, f"PDF 변환 실패: {result.stderr.decode()[:200]}")

        page_files = sorted(Path(tmp_dir).glob("page-*.png"))
        if not page_files:
            raise HTTPException(400, "PDF에서 페이지를 추출할 수 없습니다")

        client = anthropic.Anthropic(api_key=api_key)
        all_problems = []

        for page_path in page_files:
            page_bytes = page_path.read_bytes()
            img_b64 = base64.standard_b64encode(page_bytes).decode()

            try:
                response = client.messages.create(
                    model="claude-opus-4-7",
                    max_tokens=4096,
                    messages=[{
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": img_b64,
                                },
                            },
                            {"type": "text", "text": _DETECT_PROMPT},
                        ],
                    }],
                )
                raw = response.content[0].text.strip()
                if raw.startswith("```"):
                    parts = raw.split("```")
                    raw = parts[1].lstrip("json").strip() if len(parts) > 1 else raw
                data = json.loads(raw)
            except Exception as e:
                log.warning("페이지 분석 실패: %s", e)
                continue

            img = Image.open(io.BytesIO(page_bytes))
            w, h = img.size

            for prob in data.get("problems", []):
                try:
                    top_px    = max(0, int(h * prob["top_pct"] / 100) - 20)
                    bottom_px = min(h, int(h * prob["bottom_pct"] / 100) + 20)
                    cropped   = img.crop((0, top_px, w, bottom_px))
                    buf = io.BytesIO()
                    cropped.save(buf, "PNG")
                    crop_bytes = buf.getvalue()
                except Exception as e:
                    log.warning("크롭 실패 (문제 %s): %s", prob.get("number"), e)
                    continue

                filename  = f"{uuid.uuid4().hex}.png"
                (_IMG_DIR / filename).write_bytes(crop_bytes)

                all_problems.append({
                    "number":     prob.get("number"),
                    "year":       year,
                    "exam_type":  exam_type,
                    "score":      3,
                    "image_path": f"/static/problem_images/{filename}",
                    "text":       prob.get("text", ""),
                    "latex":      prob.get("latex", ""),
                    "choices":    prob.get("choices", []),
                    "answer":     prob.get("answer", ""),
                    "has_figure": bool(prob.get("has_figure", False)),
                    "unit":       "",
                    "difficulty": "",
                })

    if not all_problems:
        raise HTTPException(400, "문제를 감지하지 못했습니다. 다른 PDF를 시도해 보세요.")

    all_problems.sort(key=lambda p: p.get("number") or 0)
    return {"problems": all_problems, "page_count": len(page_files)}


@router.post("/import-pdf/save")
async def save_imported(problems: list[dict]):
    """검토 완료된 문제 목록을 DB에 일괄 저장."""
    saved_ids = []
    for p in problems:
        if not p.get("image_path"):
            continue
        try:
            pid = insert_problem({
                "year":       int(p["year"]),
                "exam_type":  p["exam_type"],
                "number":     int(p.get("number") or 0),
                "score":      int(p.get("score") or 3),
                "image_path": p["image_path"],
                "text":       p.get("text") or None,
                "latex":      p.get("latex") or None,
                "choices":    p.get("choices") or None,
                "answer":     p.get("answer") or None,
                "has_figure": bool(p.get("has_figure", False)),
                "unit":       p.get("unit") or None,
                "difficulty": p.get("difficulty") or None,
                "notes":      p.get("notes") or None,
            })
            saved_ids.append(pid)
        except Exception as e:
            log.warning("문제 저장 실패: %s", e)

    return {"saved": len(saved_ids), "ids": saved_ids}
