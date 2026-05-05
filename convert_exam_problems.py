#!/usr/bin/env python3
# exam_problems.json → examA/examB.json 변환기

import json, re, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from math_maker import _unicode_to_latex


def text_cleanup(s: str) -> str:
    """문제 텍스트 가독성 정리 (fpdf2 한글 폰트로 렌더링)."""
    # 아래첨자 유니코드 → 일반 숫자 (한글폰트 미지원 우려)
    sub_d = {'₀':'0','₁':'1','₂':'2','₃':'3','₄':'4',
             '₅':'5','₆':'6','₇':'7','₈':'8','₉':'9'}
    for ch, d in sub_d.items():
        s = s.replace(ch, d)
    # 위첨자 → 일반 문자
    sup = {'⁰':'0','¹':'1','²':'2','³':'3','⁴':'4',
           '⁵':'5','⁶':'6','⁷':'7','⁸':'8','⁹':'9',
           'ˣ':'x'}
    for ch, d in sup.items():
        s = s.replace(ch, d)
    return s


# ── 보기 변환 ───────────────────────────────────────────────────────

MATH_CHARS = set('√²³⁴⁵⁶⁷⁸⁹±∞≤≥≠₁₂₃₄₅₆₇₈₉')

def has_math(s):
    return any(c in s for c in MATH_CHARS) or 'lim' in s

def has_korean(s):
    return any(('가' <= c <= '힣') or ('㄰' <= c <= '㆏') for c in s)

def is_math_expr(s):
    """한글 없고 변수/기호가 포함된 수식 표현."""
    if has_korean(s):
        return False
    return bool(re.search(r'[a-zA-Z]', s)) or re.match(r'^-?\d', s) is not None

def wrap_choice(s: str) -> str:
    """한글 없는 보기 항목을 $...$로 감싼 LaTeX로 반환."""
    if has_korean(s):
        return s
    return f'${_unicode_to_latex(s)}$'


# ── lim 표현식 → LaTeX 변환 ────────────────────────────────────────

def lim_to_latex(expr: str) -> str:
    """lim(x→a) EXPR 형태의 평문을 LaTeX로 변환."""
    # 중괄호 → 일반 괄호 (LaTeX escape 불필요)
    s = expr.replace('{', '(').replace('}', ')')

    # lim(X→a) → \lim_{X \to a}
    def lim_sub(m):
        inner = m.group(1)
        inner = inner.replace('∞', r'\infty')
        inner = re.sub(r'→\s*', r' \\to ', inner)
        inner = re.sub(r'(\\to\s+\S+)\+', r'\1^+', inner)
        inner = re.sub(r'(\\to\s+\S+)-$', r'\1^-', inner)
        return r'\lim_{' + inner.strip() + r'}'
    s = re.sub(r'lim\(([^)]+)\)', lim_sub, s)

    # 아래첨자 유니코드 → _ (반드시 분수 변환 전에)
    sub_d = {'₀':'0','₁':'1','₂':'2','₃':'3','₄':'4',
             '₅':'5','₆':'6','₇':'7','₈':'8','₉':'9'}
    for ch, d in sub_d.items():
        s = s.replace(ch, f'_{d}')

    # 위첨자 유니코드 → ^
    sup = {'²':'2','³':'3','⁴':'4','⁵':'5'}
    for ch, d in sup.items():
        s = s.replace(ch, f'^{d}')

    # 분수 변환: -a/b → -\frac{a}{b}  (마이너스를 분수 앞으로)
    def frac_r(m):
        raw_num = m.group(1)
        den     = m.group(2)
        if raw_num.startswith('-'):
            return r'-\frac{' + raw_num[1:] + r'}{' + den + r'}'
        return r'\frac{' + raw_num + r'}{' + den + r'}'
    s = re.sub(r'(-?\d+\.?\d*)\s*/\s*(\d+\.?\d*)', frac_r, s)

    s = s.replace('∞', r'\infty')
    s = s.replace('≤', r'\leq')
    s = s.replace('≥', r'\geq')
    return s.strip()


def extract_lim_latex(text: str):
    """문제 텍스트에서 lim 표현식을 추출해 (text, latex) 반환."""

    # 패턴: "lim(X) EXPR 의 값은?" 끝나는 경우
    m = re.search(
        r'(lim\([^)]+\)\s*(?:[^,?\n가-힣]*?))(?=\s*의\s*값은)',
        text
    )
    if not m:
        return text, ''

    raw_expr = m.group(1).strip()
    if not raw_expr:
        return text, ''

    latex_expr = lim_to_latex(raw_expr)
    # 한글이 latex에 섞이면 포기
    if any('가' <= c <= '힣' for c in latex_expr):
        return text, ''

    return text, f'${latex_expr}$'


# ── 문제 변환 ───────────────────────────────────────────────────────

def convert_problem(prob: dict) -> dict:
    q_type   = '서술형' if prob.get('유형') == '서술형' else '선택형'
    raw_text = prob.get('문제', '').strip()

    # lim 추출은 원본(유니코드 첨자 보존) 텍스트에서 먼저
    _, latex = extract_lim_latex(raw_text)
    # 텍스트 정리는 그 다음 (아래첨자/위첨자 → 일반 문자)
    text = text_cleanup(raw_text)

    raw = prob.get('선택지', [])
    stripped = [re.sub(r'^[①②③④⑤]\s*', '', c).strip() for c in raw]

    # 하나라도 한글이면 전체 평문으로 통일
    any_kor = any(has_korean(c) for c in stripped)
    choices = [c if any_kor else wrap_choice(c) for c in stripped]
    while len(choices) < 5:
        choices.append('')

    ans_raw   = prob.get('정답', '').strip()
    ans_match = re.match(r'^([①②③④⑤])', ans_raw)
    answer    = ans_match.group(1) if ans_match else ans_raw

    return {
        'type':    q_type,
        'score':   prob.get('배점', 4),
        'text':    text,
        'latex':   latex,
        'choices': choices,
        'answer':  answer,
    }


def convert_set(set_data: dict) -> list:
    problems = []
    for p in set_data.get('선택형', []):
        problems.append(convert_problem(p))
    for p in set_data.get('서술형', []):
        problems.append(convert_problem(p))
    return problems


def main():
    src = '/Users/janghayeon/Desktop/math/exam_problems.json'
    with open(src, 'r', encoding='utf-8') as f:
        data = json.load(f)

    title    = data.get('제목', '수학II 모의고사')
    subtitle = data.get('구성', '')
    out_dir  = '/Users/janghayeon/Desktop/math'

    for set_name in ['세트A', '세트B']:
        if set_name not in data:
            continue
        problems = convert_set(data[set_name])
        label    = set_name[-1]
        out      = {
            'title':    f'{title}  [{label}형]',
            'subtitle': subtitle,
            'problems': problems,
        }
        path = os.path.join(out_dir, f'exam{label}.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(f'exam{label}.json  ({len(problems)}문제)')

    print('\n앱에서 JSON 불러오기 → PDF 내보내기')


if __name__ == '__main__':
    main()
