"""Claude: 문제 JSON → 변형 문제 JSON."""

import json, os

import anthropic

from app.prompts import VARIANTS_SYSTEM, VARIANTS_USER_TMPL

_client = None

def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


def generate_variants(problem: dict, n: int = 3) -> list[dict]:
    """단일 문제 → n개 변형 문제 리스트."""
    prompt = VARIANTS_USER_TMPL.format(
        n=n,
        problem_json=json.dumps(problem, ensure_ascii=False, indent=2),
    )

    response = _get_client().messages.create(
        model="claude-sonnet-4-5",
        max_tokens=4096,
        system=VARIANTS_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    variants = json.loads(raw)

    for v in variants:
        ch = v.get("choices", [])
        while len(ch) < 5:
            ch.append("")
        v["choices"] = ch[:5]

    return variants


def generate_variants_batch(problems: list[dict], n: int = 3) -> list[list[dict]]:
    """여러 문제 각각에 대해 n개씩 변형 생성."""
    return [generate_variants(p, n) for p in problems]
