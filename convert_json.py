#!/usr/bin/env python3
"""
exam_variants.json → math_maker.py 용 JSON 변환기
변환 후 set1.json ~ set5.json 생성
"""

import json, re, os

# ── 수식 기호 → LaTeX 변환 ─────────────────────────────────────────

def to_latex(s: str) -> str:
    """평문 수식 표기를 LaTeX로 변환."""
    # □ 는 matplotlib mathtext 미지원 → safe_latex에서 별도 처리, 여기선 건드리지 않음

    # ∛(X) → \sqrt[3]{X}
    s = re.sub(r'∛\(([^)]+)\)', lambda m: r'\sqrt[3]{' + m.group(1) + r'}', s)
    s = re.sub(r'∛(\d+)',        lambda m: r'\sqrt[3]{' + m.group(1) + r'}', s)
    s = re.sub(r'∛([a-zA-Z])',   lambda m: r'\sqrt[3]{' + m.group(1) + r'}', s)

    # √(X) → \sqrt{X}   ← 위첨자 변환보다 먼저 처리
    s = re.sub(r'√\(([^)]+)\)',  lambda m: r'\sqrt{' + m.group(1) + r'}', s)
    s = re.sub(r'√(\d+\.?\d*)', lambda m: r'\sqrt{' + m.group(1) + r'}', s)
    s = re.sub(r'√([a-zA-Z])',  lambda m: r'\sqrt{' + m.group(1) + r'}', s)

    # 위첨자 문자 → ^숫자
    sup = {'⁰':'0','¹':'1','²':'2','³':'3','⁴':'4',
           '⁵':'5','⁶':'6','⁷':'7','⁸':'8','⁹':'9'}
    for ch, d in sup.items():
        s = s.replace(ch, f'^{d}')

    # 분수 변환: a/b → \frac{a}{b}
    def frac_replace(m):
        return r'\frac{' + m.group(1) + r'}{' + m.group(2) + r'}'

    # 숫자\sqrt{X}/숫자  또는  \sqrt{X}/숫자  또는  숫자/숫자
    s = re.sub(r'(\d*\.?\d*\\sqrt\{[^}]+\}|\d+\.?\d*)\s*/\s*(\d+\.?\d*)', frac_replace, s)
    # 숫자/변수  (예: 1/x)
    s = re.sub(r'(\d+)\s*/\s*([a-zA-Z])', frac_replace, s)

    # 특수 기호
    s = s.replace('±', r'\pm')
    s = s.replace('×', r'\times')
    s = s.replace('÷', r'\div')
    s = s.replace('π', r'\pi')
    s = s.replace('≤', r'\leq')
    s = s.replace('≥', r'\geq')
    s = s.replace('≠', r'\neq')
    s = s.replace('∞', r'\infty')

    return s

MATH_CHARS = set('√∛²³⁴⁵⁶⁷⁸⁹±π∞≤≥≠□')

def has_math(s: str) -> bool:
    return any(c in s for c in MATH_CHARS)

def has_korean(s: str) -> bool:
    return any('가' <= c <= '힣' for c in s)

def is_math_expr(s: str) -> bool:
    """한글 없고 변수/연산자가 포함된 수식 표현인지 확인."""
    if has_korean(s):
        return False
    return bool(re.search(r'[a-zA-Z]', s)) and not re.search(r'[가-힣]', s)

def wrap_latex(s: str) -> str:
    """수식이 있으면 $...$로 감싸고 LaTeX로 변환.
    한글이 섞여 있으면 matplotlib이 렌더링 못 하므로 감싸지 않음."""
    converted = to_latex(s)
    if has_korean(converted):
        return converted  # 한글 포함이면 fpdf2가 일반 텍스트로 처리
    # 특수 수식 기호 있거나, 변환되었거나, 변수 포함 순수 수식이면 $...$로 감싸기
    if has_math(s) or converted != s or is_math_expr(s):
        return f'${converted}$'
    return converted


# ── 문제 하나 변환 ──────────────────────────────────────────────────

def safe_latex(expr: str) -> str:
    """수식을 $...$로 감쌀 때 한글/□ 포함이면 별도 처리."""
    converted = to_latex(expr)
    if has_korean(converted):
        return expr      # 한글 섞인 수식은 그냥 텍스트로
    if '□' in converted:
        # □는 matplotlib mathtext 미지원 → LaTeX 바깥에 두기
        # 예: "4a^2 - 20a + □" → "$4a^2 - 20a + $□"
        parts = converted.split('□')
        wrapped = [f'${p}$' if p.strip() else '' for p in parts]
        return '□'.join(wrapped)
    return f'${converted}$'

def convert_choice(prob: dict) -> dict:
    """선택형 문제 변환."""
    q = prob['question']
    # \n 기준으로 텍스트(설명)와 수식 분리
    parts = q.split('\n', 1)
    text  = parts[0].strip()
    expr  = parts[1].strip() if len(parts) > 1 else ''

    if expr:
        result = safe_latex(expr)
        if result.startswith('$'):
            latex = result
        else:
            # 한글 포함 → 텍스트에 합치기
            text  = f"{text}\n{result}" if text else result
            latex = ''
    else:
        latex = ''

    # 보기: 앞의 ①②③④⑤ 제거 후 수식 처리
    raw_choices = prob.get('options', [])
    stripped = [re.sub(r'^[①②③④⑤]\s*', '', c).strip() for c in raw_choices]

    # 하나라도 한글이 있으면 전체 보기를 평문으로 통일 (크기 일관성)
    any_korean_in_choices = any(has_korean(c) for c in stripped)

    choices = []
    for opt in stripped:
        if any_korean_in_choices:
            choices.append(opt)          # 평문
        else:
            choices.append(wrap_latex(opt))
    while len(choices) < 5:
        choices.append('')

    # 정답: 앞 기호만 추출 (② ±3 → ②)
    ans_raw = prob.get('answer', '').strip()
    ans_match = re.match(r'^([①②③④⑤])', ans_raw)
    answer = ans_match.group(1) if ans_match else ans_raw

    return {
        'type':    '선택형',
        'score':   prob.get('points', 3),
        'text':    text,
        'latex':   latex,
        'choices': choices,
        'answer':  answer,
    }

def convert_essay(prob: dict) -> dict:
    """서술형 문제 변환."""
    q = prob['question']
    parts = q.split('\n', 1)
    text  = parts[0].strip()
    expr  = parts[1].strip() if len(parts) > 1 else ''

    if expr:
        result = safe_latex(expr)
        if result.startswith('$'):
            latex = result
        else:
            text  = f"{text}\n{result}" if text else result
            latex = ''
    elif has_math(text) and not has_korean(text):
        # 순수 수식만 있는 경우
        latex = f'${to_latex(text)}$'
        text  = ''
    else:
        latex = ''

    ans_raw = prob.get('answer', '').strip()

    return {
        'type':    '서술형',
        'score':   prob.get('points', 5),
        'text':    text,
        'latex':   latex,
        'choices': [],
        'answer':  ans_raw,
    }


# ── 메인 변환 ───────────────────────────────────────────────────────

def main():
    src = '/Users/janghayeon/Desktop/math/exam_variants.json'
    with open(src, 'r', encoding='utf-8') as f:
        data = json.load(f)

    meta  = data.get('meta', {})
    title = meta.get('title', '수학 시험지')
    sets  = data.get('sets', [])

    out_dir = '/Users/janghayeon/Desktop/math'
    created = []

    for s in sets:
        sid = s.get('set_id', '?')
        problems = []

        for p in s.get('선택형', []):
            problems.append(convert_choice(p))

        for p in s.get('서술형', []):
            problems.append(convert_essay(p))

        out = {
            'title':    title,
            'subtitle': f'[세트 {sid}]  선택형 1~16번 / 서술형 1~8번',
            'problems': problems,
        }
        out_path = os.path.join(out_dir, f'set{sid}.json')
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        created.append(out_path)
        print(f'set{sid}.json 생성 완료  ({len(problems)}문제)')

    print()
    print('앱에서 "JSON 불러오기"로 위 파일을 열면 됩니다.')
    return created

if __name__ == '__main__':
    main()
