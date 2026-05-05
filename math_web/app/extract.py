"""Claude Vision: 이미지 → 문제 JSON."""

import base64, hashlib, json, os, pickle
from pathlib import Path

import anthropic

from app.prompts import EXTRACT_SYSTEM, EXTRACT_USER

_client = None

def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


# 이미지 해시 기반 디스크 캐시 (Vision 호출 비용 절감)
_VISION_CACHE_DIR = Path(
    os.environ.get("MATHMAKER_CACHE", Path.home() / ".cache" / "MathMaker")
) / "vision"
_VISION_CACHE_DIR.mkdir(parents=True, exist_ok=True)

_PROMPT_VERSION = "v2"  # 프롬프트 바뀌면 올려서 기존 캐시 무효화


def _vision_cache_key(image_bytes: bytes) -> str:
    img_hash = hashlib.sha256(image_bytes).hexdigest()
    return f"{img_hash}-{_PROMPT_VERSION}"


def _vision_cache_get(key: str):
    path = _VISION_CACHE_DIR / f"{key}.pkl"
    if path.exists():
        try:
            return pickle.loads(path.read_bytes())
        except Exception:
            pass
    return None


def _vision_cache_set(key: str, val):
    path = _VISION_CACHE_DIR / f"{key}.pkl"
    try:
        path.write_bytes(pickle.dumps(val))
    except Exception:
        pass


def extract_problems(image_bytes: bytes, media_type: str = "image/jpeg") -> list[dict]:
    """이미지 바이트 → 문제 JSON 리스트.
    동일 이미지+프롬프트 버전이면 캐시 반환."""
    key = _vision_cache_key(image_bytes)
    cached = _vision_cache_get(key)
    if cached is not None:
        return cached

    b64 = base64.standard_b64encode(image_bytes).decode()

    response = _get_client().messages.create(
        model="claude-sonnet-4-5",
        max_tokens=4096,
        system=EXTRACT_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": b64,
                        },
                    },
                    {"type": "text", "text": EXTRACT_USER},
                ],
            }
        ],
    )

    raw = response.content[0].text.strip()
    # JSON 블록 처리 (모델이 가끔 ```json``` 으로 감쌀 수 있음)
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    problems = json.loads(raw)

    # choices 5개 보장
    for p in problems:
        ch = p.get("choices", [])
        while len(ch) < 5:
            ch.append("")
        p["choices"] = ch[:5]

    _vision_cache_set(key, problems)
    return problems
