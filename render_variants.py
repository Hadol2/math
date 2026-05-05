#!/usr/bin/env python3
"""exam_variants.json → PDF 변환 렌더러."""

import json, re, sys, subprocess, os
sys.path.insert(0, os.path.dirname(__file__))
from math_maker import export_to_pdf, _unicode_to_latex
from figure_drawer import make_figure

_MATH_CHARS = set('√∛²³⁴⁵±π∞→≈≤≥≠×÷□½⅓⅔¼¾')

def _has_math(text: str) -> bool:
    return any(c in text for c in _MATH_CHARS)

def _is_pure_math(text: str) -> bool:
    """한글이 없고 수식 기호가 있으면 True. 한글 섞인 텍스트는 LaTeX로 안 보냄."""
    has_korean = any('가' <= c <= '힣' for c in text)
    return not has_korean and _has_math(text)

def _as_latex(expr: str) -> str:
    """수식 문자열을 $...$로 감싼 LaTeX로 반환."""
    return '$' + _unicode_to_latex(expr) + '$'

# ── 문제 변환 ──────────────────────────────────────────────────────

_CIRCLE_CHARS = '①②③④⑤'

def _strip_circle(s: str) -> str:
    """① 또는 ② 등의 접두사 제거."""
    s = s.strip()
    if s and s[0] in _CIRCLE_CHARS:
        s = s[1:].lstrip()
    return s

def _convert_problem(prob: dict, is_essay: bool = False) -> dict:
    question = prob.get('question', '').strip()
    points   = prob.get('points', prob.get('score', 3))

    # question을 \n 기준으로 분리: 첫 줄 = 한글 설명, 이후 = 수식
    lines = question.split('\n', 1)
    text_part  = lines[0].strip()
    latex_part = ''

    if len(lines) > 1:
        math_expr = lines[1].strip()
        if _is_pure_math(math_expr):
            latex_part = _as_latex(math_expr)
        else:
            # 한글 섞인 표현이나 수식 없는 경우 text에 붙임
            text_part += '\n' + math_expr

    # choices 변환 (선택형만)
    choices = ['', '', '', '', '']
    if not is_essay:
        raw_opts = prob.get('options', [])
        for i, opt in enumerate(raw_opts[:5]):
            content = _strip_circle(opt)
            has_korean = any('가' <= c <= '힣' for c in content)
            if not has_korean and content:
                choices[i] = _as_latex(content)
            else:
                choices[i] = content

    answer = prob.get('answer', '').strip()

    # 도형 감지: question 전체에서 도형 PNG 생성 시도
    figure_png = None
    try:
        figure_png = make_figure(question)
    except Exception:
        pass

    return {
        'type':    '서술형' if is_essay else '선택형',
        'score':   points,
        'text':    text_part,
        'latex':   latex_part,
        'choices': choices,
        'answer':  answer,
        'figure':  figure_png,
    }

# ── 메인 변환 + 렌더링 ─────────────────────────────────────────────

def render_set(set_data: dict, meta: dict, set_idx: int, out_path: str):
    problems = []
    for p in set_data.get('선택형', []):
        problems.append(_convert_problem(p, is_essay=False))
    for p in set_data.get('서술형', []):
        problems.append(_convert_problem(p, is_essay=True))

    exam_info = {
        'title':    meta.get('title', '수학 시험지'),
        'subtitle': f'[세트 {set_idx}]  선택형 1~16번 / 서술형 1~8번',
    }
    export_to_pdf(exam_info, problems, out_path)
    print(f'  → {out_path}  ({len(problems)}문제)')


if __name__ == '__main__':
    with open('exam_variants.json', encoding='utf-8') as f:
        data = json.load(f)

    meta = data['meta']
    sets = data['sets']

    # 세트 번호를 인자로 받거나 전체 렌더링
    target = int(sys.argv[1]) if len(sys.argv) > 1 else None

    for s in sets:
        sid = s['set_id']
        if target is not None and sid != target:
            continue
        out = f'variant_set{sid}.pdf'
        print(f'세트 {sid} 렌더링 중...')
        try:
            render_set(s, meta, sid, out)
        except Exception as e:
            print(f'  오류: {e}')

    if target:
        subprocess.run(['open', f'variant_set{target}.pdf'])
    else:
        subprocess.run(['open', 'variant_set1.pdf'])
