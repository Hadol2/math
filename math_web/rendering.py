#!/usr/bin/env python3
"""
수학 시험지 PDF 렌더링 모듈 (서버 헤드리스 버전)
의존: pip install fpdf2 matplotlib pillow
LaTeX 고품질 렌더링: pdflatex + pdftoppm or gs (Docker: texlive-latex-base + poppler-utils)
"""

import glob
import matplotlib
matplotlib.use('Agg')   # headless — TkAgg 대신 Agg 백엔드
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from fpdf import FPDF
import base64, hashlib, io, json, logging, os, pickle, re, shutil, subprocess

log = logging.getLogger(__name__)

# ── 번들 폰트 등록 (fonts/ 디렉터리) ───────────────────────────────
_FONT_DIR = os.path.join(os.path.dirname(__file__), 'fonts')
for _ttf in glob.glob(os.path.join(_FONT_DIR, '*.ttf')):
    fm.fontManager.addfont(_ttf)

# ── 폰트 경로 탐지 ─────────────────────────────────────────────────
matplotlib.rcParams['mathtext.fontset'] = 'cm'

_GOTHIC_PATH   = None
_MYEONGJO_PATH = None

# 번들 fonts/ 우선 탐색
for _ttf in glob.glob(os.path.join(_FONT_DIR, '*.ttf')):
    name = os.path.basename(_ttf).lower()
    if 'myeongjo' in name and _MYEONGJO_PATH is None:
        _MYEONGJO_PATH = _ttf
    elif 'gothic' in name and _GOTHIC_PATH is None:
        _GOTHIC_PATH = _ttf

# 로컬 Mac/Linux 시스템 폰트 fallback
if not _GOTHIC_PATH or not _MYEONGJO_PATH:
    for _f in fm.fontManager.ttflist:
        if _f.name == 'Nanum Gothic'   and _GOTHIC_PATH   is None: _GOTHIC_PATH   = _f.fname
        if _f.name == 'Nanum Myeongjo' and _MYEONGJO_PATH is None: _MYEONGJO_PATH = _f.fname

_KR_PROP = fm.FontProperties(fname=_MYEONGJO_PATH or _GOTHIC_PATH) \
           if (_MYEONGJO_PATH or _GOTHIC_PATH) else None

# ── LaTeX 도구 탐지 ────────────────────────────────────────────────
_TEX_BIN = '/Library/TeX/texbin'   # Mac BasicTeX (Docker에서는 무시됨)
if os.path.isdir(_TEX_BIN) and _TEX_BIN not in os.environ.get('PATH', ''):
    os.environ['PATH'] = _TEX_BIN + ':' + os.environ.get('PATH', '')

def _detect_tools():
    pdflatex = shutil.which('pdflatex')
    for cmd in ['pdftoppm', 'gs']:
        if shutil.which(cmd):
            return pdflatex, cmd
    return pdflatex, None

_PDFLATEX, _PDF2PNG_CMD = _detect_tools()
_LATEX_OK = bool(_PDFLATEX and _PDF2PNG_CMD)

# ── 렌더링 디스크 캐시 ──────────────────────────────────────────────
_CACHE_DIR = os.environ.get(
    'MATHMAKER_CACHE',
    os.path.expanduser('~/.cache/MathMaker'),
)
os.makedirs(_CACHE_DIR, exist_ok=True)


# ── 수식 → PNG 렌더링 ───────────────────────────────────────────────

def _cache_get(key: str):
    path = os.path.join(_CACHE_DIR, hashlib.md5(key.encode()).hexdigest() + '.pkl')
    if os.path.exists(path):
        try:
            with open(path, 'rb') as f:
                return pickle.load(f)
        except Exception:
            pass
    return None

def _cache_set(key: str, val):
    path = os.path.join(_CACHE_DIR, hashlib.md5(key.encode()).hexdigest() + '.pkl')
    try:
        with open(path, 'wb') as f:
            pickle.dump(val, f)
    except Exception:
        pass


def render_math_png(latex: str, fontsize: int = 22, dpi: int = 300, tight: bool = False) -> tuple:
    """수식 PNG 렌더링. pdflatex 우선, 없으면 matplotlib fallback.
    반환: (png_bytes, width_mm, height_mm)"""
    key = f'{latex}|{fontsize}|{dpi}|{tight}'
    cached = _cache_get(key)
    if cached:
        return cached

    try:
        if _LATEX_OK:
            result = _render_pdflatex(latex, fontsize, dpi)
        else:
            result = _render_matplotlib(latex, fontsize, dpi, tight=tight)
    except Exception:
        result = _render_matplotlib(latex, fontsize, dpi, tight=tight)

    _cache_set(key, result)
    return result


def _render_pdflatex(latex: str, fontsize: int, dpi: int) -> tuple:
    """pdflatex + pdftoppm/gs — 완전한 LaTeX 품질 렌더링."""
    import tempfile
    from PIL import Image
    import numpy as np

    s = latex.strip()
    if s.startswith('$$') and s.endswith('$$'):
        inner = s[2:-2].strip()
    elif s.startswith('$') and s.endswith('$'):
        inner = s[1:-1].strip()
    else:
        inner = s

    pt = max(9, min(int(fontsize * 0.75), 20))
    expr = '$\\displaystyle ' + inner + '$'

    templates = [
        ('\\documentclass[' + str(pt) + 'pt]{standalone}\n'
         '\\usepackage{amsmath,amssymb,mathtools}\n'
         '\\standaloneconfig{border=5pt}\n'
         '\\begin{document}\n' + expr + '\n\\end{document}\n'),

        ('\\documentclass[' + str(pt) + 'pt]{article}\n'
         '\\usepackage[paperwidth=40cm,paperheight=8cm,margin=2pt]{geometry}\n'
         '\\usepackage{amsmath,amssymb,mathtools}\n'
         '\\pagestyle{empty}\n'
         '\\begin{document}\n\\noindent' + expr + '\n\\end{document}\n'),
    ]

    with tempfile.TemporaryDirectory() as tmp:
        pdf = os.path.join(tmp, 'eq.pdf')
        tex = os.path.join(tmp, 'eq.tex')
        last_err = ''

        for src in templates:
            with open(tex, 'w', encoding='utf-8') as f:
                f.write(src)
            r = subprocess.run(
                [_PDFLATEX, '-interaction=nonstopmode', '-halt-on-error',
                 '-output-directory', tmp, tex],
                capture_output=True, timeout=30
            )
            if r.returncode == 0 and os.path.exists(pdf):
                break
            last_err = r.stdout.decode(errors='replace')[-400:]
        else:
            raise RuntimeError(f'pdflatex 실패:\n{last_err}')

        pdfcrop = shutil.which('pdfcrop') or '/Library/TeX/texbin/pdfcrop'
        cropped = os.path.join(tmp, 'cropped.pdf')
        if os.path.isfile(pdfcrop):
            subprocess.run([pdfcrop, '--margins', '5', pdf, cropped],
                           capture_output=True, timeout=30)
            if os.path.exists(cropped):
                pdf = cropped

        if _PDF2PNG_CMD == 'gs':
            out = os.path.join(tmp, 'out.png')
            subprocess.run([
                'gs', '-dBATCH', '-dNOPAUSE', '-dQUIET', '-dSAFER',
                f'-r{dpi}', '-sDEVICE=png16m', f'-sOutputFile={out}', pdf
            ], capture_output=True, timeout=30, check=True)
        else:  # pdftoppm
            base = os.path.join(tmp, 'out')
            subprocess.run(
                ['pdftoppm', '-r', str(dpi), '-png', pdf, base],
                capture_output=True, timeout=30
            )
            pngs = sorted(f for f in os.listdir(tmp) if f.endswith('.png'))
            if not pngs:
                raise RuntimeError('pdftoppm: PNG 출력 없음')
            out = os.path.join(tmp, pngs[0])

        img = Image.open(out).convert('RGB')

        arr = np.array(img)
        mask = arr.min(axis=2) < 245
        rows, cols = np.any(mask, axis=1), np.any(mask, axis=0)
        if rows.any():
            r0, r1 = np.where(rows)[0][[0, -1]]
            c0, c1 = np.where(cols)[0][[0, -1]]
            pad = max(int(dpi * 0.055), 12)
            img = img.crop((max(0,c0-pad), max(0,r0-pad),
                            min(arr.shape[1],c1+pad+1), min(arr.shape[0],r1+pad+1)))

        buf = io.BytesIO()
        img.save(buf, 'PNG')
        buf.seek(0)
        return buf.read(), img.width / dpi * 25.4, img.height / dpi * 25.4


def _cases_to_array(s: str) -> str:
    r"""\begin{cases}...\end{cases} → \left\{\begin{array}{ll}...\end{array}\right."""
    return re.sub(
        r'\\begin\{cases\}(.*?)\\end\{cases\}',
        lambda m: r'\left\{\begin{array}{ll}' + m.group(1) + r'\end{array}\right.',
        s, flags=re.DOTALL,
    )


def _has_korean(s: str) -> bool:
    return any('가' <= c <= '힣' for c in s)


def _latex_kr_to_mixed(latex: str) -> str:
    r"""LaTeX에서 \text{한글} 블록을 추출, 수식 부분은 $...$로, 한글은 일반 텍스트로 변환."""
    s = latex.strip()
    if s.startswith('$') and s.endswith('$'):
        s = s[1:-1]
    s = s.replace(r'\;', ' ').replace(r'\quad', '  ').replace(r'\qquad', '   ')
    parts = re.split(r'(\\text\{[^}]*\})', s)
    result = []
    for part in parts:
        if part.startswith(r'\text{'):
            result.append(part[6:-1])
        elif part.strip():
            result.append(f'${part}$')
        else:
            result.append(part)
    text = ''.join(result)
    for _ in range(3):
        text = re.sub(r'\$([^$]*)\$\$([^$]*)\$', r'$\1\2$', text)
    return text


def _render_matplotlib(latex: str, fontsize: int, dpi: int, tight: bool = False) -> tuple:
    """matplotlib mathtext fallback 렌더러."""
    from PIL import Image
    import numpy as np

    def _pre(inner: str) -> str:
        inner = _cases_to_array(inner)
        return r'\displaystyle ' + inner

    if '$' in latex:
        s = re.sub(r'\$([^$]+)\$', lambda m: '$' + _pre(m.group(1)) + '$', latex)
    else:
        s = '$' + _pre(latex) + '$'
    s = s.replace(r'\square', r'\text{□}').replace(r'\Box', r'\text{□}')

    fig = Figure(figsize=(12, 4), facecolor='white')
    canvas = FigureCanvasAgg(fig)
    ax = fig.add_subplot(111)
    ax.set_axis_off()
    ax.text(0.5, 0.5, s, fontsize=fontsize, ha='center', va='center',
            transform=ax.transAxes)
    canvas.draw()

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=dpi, facecolor='white')
    buf.seek(0)

    img = Image.open(buf).convert('RGB')
    arr = np.array(img)
    mask = arr.min(axis=2) < 240
    rows, cols = np.any(mask, axis=1), np.any(mask, axis=0)
    if rows.any():
        r0, r1 = np.where(rows)[0][[0, -1]]
        c0, c1 = np.where(cols)[0][[0, -1]]
        p = max(int(fontsize * dpi / 72 * (0.25 if tight else 0.7)), 4 if tight else 30)
        img = img.crop((max(0,c0-p), max(0,r0-p),
                        min(arr.shape[1],c1+p+1), min(arr.shape[0],r1+p+1)))

    buf2 = io.BytesIO()
    img.save(buf2, 'PNG')
    buf2.seek(0)
    return buf2.read(), img.width/dpi*25.4, img.height/dpi*25.4


# ── 한글+수식 혼합 텍스트 렌더링 ────────────────────────────────────

_INLINE_MATH_CHARS = set('√∛∞<>≤≥≠±×÷πθΔΣ∫∂∇∑∏')

def _replace_root_paren(text: str, sym: str, cmd: str) -> str:
    """√(...) / ∛(...) 패턴을 중첩 괄호 지원으로 처리."""
    result, i = [], 0
    while i < len(text):
        if text[i] == sym and i + 1 < len(text) and text[i + 1] == '(':
            depth, j = 0, i + 1
            while j < len(text):
                if text[j] == '(':   depth += 1
                elif text[j] == ')':
                    depth -= 1
                    if depth == 0: break
                j += 1
            inner = text[i + 2:j]
            if j + 1 < len(text) and text[j + 1] in '²³':
                exp = 2 if text[j + 1] == '²' else 3
                result.append(f'${cmd}{{{inner}}}^{{{exp}}}$')
                i = j + 2
            else:
                result.append(f'${cmd}{{{inner}}}$')
                i = j + 1
        else:
            result.append(text[i]); i += 1
    return ''.join(result)


def _text_to_mpl(text: str) -> str:
    """유니코드 수식 기호를 matplotlib mathtext용 $...$로 변환."""
    text = _replace_root_paren(text, '√', r'\sqrt')
    text = _replace_root_paren(text, '∛', r'\sqrt[3]')
    text = re.sub(r'√(-?\d+(?:\.\d+)?)', lambda m: f'$\\sqrt{{{m.group(1)}}}$', text)
    text = re.sub(r'∛(-?\d+(?:\.\d+)?)', lambda m: f'$\\sqrt[3]{{{m.group(1)}}}$', text)
    text = re.sub(r'√([a-zA-Z])', lambda m: f'$\\sqrt{{{m.group(1)}}}$', text)
    text = re.sub(r'∛([a-zA-Z])', lambda m: f'$\\sqrt[3]{{{m.group(1)}}}$', text)
    text = text.replace('√', r'$\surd$').replace('∛', r'$\sqrt[3]{}$')
    text = text.replace('∞', r'$\infty$')
    _SYM_MAP = [
        ('<',  '$<$'),   ('>',  '$>$'),
        ('≤',  r'$\leq$'),  ('≥', r'$\geq$'),
        ('≠',  r'$\neq$'),  ('±', r'$\pm$'),
        ('×',  r'$\times$'), ('÷', r'$\div$'),
        ('π',  r'$\pi$'),   ('θ', r'$\theta$'),
        ('Δ',  r'$\Delta$'), ('Σ', r'$\Sigma$'),
        ('∑',  r'$\sum$'),  ('∏', r'$\prod$'),
        ('∫',  r'$\int$'),  ('∂', r'$\partial$'),
        ('∇',  r'$\nabla$'),
        ('→',  r'$\rightarrow$'), ('←', r'$\leftarrow$'),
        ('↑',  r'$\uparrow$'),    ('↓', r'$\downarrow$'),
    ]
    for ch, sub in _SYM_MAP:
        text = text.replace(ch, sub)
    text = re.sub(r'([a-zA-Z0-9\)])²', lambda m: f'${m.group(1)}^{{2}}$', text)
    text = re.sub(r'([a-zA-Z0-9\)])³', lambda m: f'${m.group(1)}^{{3}}$', text)
    text = text.replace('²', r'$^{2}$').replace('³', r'$^{3}$')
    for _ in range(4):
        merged = re.sub(r'\$([^$]*)\$\$([^$]*)\$', r'$\1\2$', text)
        if merged == text:
            break
        text = merged
    return text


def _render_mixed_text_png(text: str, fontsize: int = 11, dpi: int = 200,
                           preprocess: bool = True) -> tuple:
    """한글+수식 혼합 텍스트를 matplotlib PNG로 렌더링."""
    from PIL import Image
    import numpy as np

    mpl_text = _text_to_mpl(text) if preprocess else text

    n_lines = mpl_text.count('\n') + 1
    fig_h = max(1.5, n_lines * 1.1)
    fig = Figure(figsize=(17, fig_h), facecolor='white')
    FigureCanvasAgg(fig)
    ax = fig.add_subplot(111)
    ax.set_axis_off()
    ax.text(0.01, 0.5, mpl_text, fontsize=fontsize, ha='left', va='center',
            transform=ax.transAxes, fontproperties=_KR_PROP,
            linespacing=1.6)
    fig.canvas.draw()

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=dpi, facecolor='white',
                bbox_inches='tight', pad_inches=0.06)
    buf.seek(0)
    img = Image.open(buf).convert('RGB')

    arr = np.array(img)
    mask = arr.min(axis=2) < 245
    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)
    if rows.any() and cols.any():
        r0, r1 = np.where(rows)[0][[0, -1]]
        c0, c1 = np.where(cols)[0][[0, -1]]
        pad_px = max(int(dpi * 0.04), 4)
        img = img.crop((
            max(0, c0 - pad_px), max(0, r0 - pad_px),
            min(arr.shape[1], c1 + pad_px + 1), min(arr.shape[0], r1 + pad_px + 1),
        ))

    buf2 = io.BytesIO()
    img.save(buf2, 'PNG')
    buf2.seek(0)
    return buf2.read(), img.width / dpi * 25.4, img.height / dpi * 25.4


# ── 기본 문제 구조 ──────────────────────────────────────────────────

def new_problem() -> dict:
    return {
        "type":    "선택형",
        "score":   3,
        "text":    "",
        "latex":   "",
        "choices": ["", "", "", "", ""],
        "answer":  "",
    }


# ── PDF 레이아웃 상수 ────────────────────────────────────────────────
_PAGE_W   = 210
_L_MARGIN = 14
_R_MARGIN = 14
_COL_GAP  = 7
_COL_W    = (_PAGE_W - _L_MARGIN - _R_MARGIN - _COL_GAP) // 2  # 87mm

CIRCLE = ['①', '②', '③', '④', '⑤']


# ── PDF 생성 ────────────────────────────────────────────────────────

class ExamPDF(FPDF):
    def __init__(self, title: str, subtitle: str, total_score: int = 0):
        super().__init__(format='A4')
        self._title       = title
        self._subtitle    = subtitle
        self._total_score = total_score
        self.set_margins(_L_MARGIN, 22, _R_MARGIN)
        self.set_auto_page_break(False)

        self._krf = 'Helvetica'
        if _MYEONGJO_PATH:
            self.add_font('KR', fname=_MYEONGJO_PATH)
            self._krf = 'KR'
        elif _GOTHIC_PATH:
            self.add_font('KR', fname=_GOTHIC_PATH)
            self._krf = 'KR'

        self._col   = 0
        self._top_y = 35.0

    # ── 컬럼 헬퍼 ─────────────────────────────────────────────────────

    def _col_lx(self) -> float:
        return _L_MARGIN + self._col * (_COL_W + _COL_GAP)

    def _apply_col(self):
        lx = self._col_lx()
        self.set_left_margin(lx)
        self.set_right_margin(_PAGE_W - lx - _COL_W)
        self.set_x(lx)

    def _need_space(self, needed_h: float):
        """필요한 높이가 현재 컬럼에 없으면 다음 컬럼 또는 새 페이지로 이동."""
        page_bottom = self.h - 18
        if self.get_y() + needed_h <= page_bottom:
            return
        if self._col == 0:
            self._col = 1
            self._apply_col()
            self.set_y(self._top_y)
            return
        self.add_page()

    # ── 헤더 / 푸터 ────────────────────────────────────────────────────

    def header(self):
        self.set_left_margin(_L_MARGIN)
        self.set_right_margin(_R_MARGIN)

        if self.page_no() == 1:
            self._draw_full_header()
        else:
            self._draw_mini_header()

        self._col   = 0
        self._top_y = self.get_y()
        self._apply_col()

    def _draw_full_header(self):
        """1페이지: 제목 + 학생 정보 (밑줄만, 박스 없음)."""
        # 상단 이중선
        self.set_draw_color(0, 0, 0)
        self.set_line_width(1.2)
        self.line(_L_MARGIN, 11, _PAGE_W - _R_MARGIN, 11)
        self.set_line_width(0.25)
        self.line(_L_MARGIN, 13.5, _PAGE_W - _R_MARGIN, 13.5)

        # 제목
        self.set_y(16)
        self.set_font(self._krf, size=16)
        self.cell(0, 9, self._title, align='C', new_x='LMARGIN', new_y='NEXT')
        if self._subtitle:
            self.set_font(self._krf, size=8)
            self.cell(0, 5, self._subtitle, align='C', new_x='LMARGIN', new_y='NEXT')
        self.ln(3)

        # 중간 구분선 (얇게)
        self.set_line_width(0.25)
        self.line(_L_MARGIN, self.get_y(), _PAGE_W - _R_MARGIN, self.get_y())
        self.ln(3.5)

        # 학생 정보 행 — 박스 없이 레이블 + 밑줄
        y_info   = self.get_y()
        baseline = y_info + 6.5
        self.set_font(self._krf, size=9)
        self.set_line_width(0.3)

        cx = float(_L_MARGIN)
        for label, ul_w in [('학년', 15.0), ('반', 13.0), ('번호', 15.0), ('이름', 32.0)]:
            self.set_xy(cx, y_info)
            lw = self.get_string_width(label) + 1.5
            self.cell(lw, 7, label)
            x0 = self.get_x()
            self.line(x0, baseline, x0 + ul_w, baseline)
            cx = x0 + ul_w + 5.0

        # 총점 — 오른쪽 끝, 밑줄
        score_label = f'총점  ({self._total_score}점)'
        sl_w  = self.get_string_width(score_label) + 1.5
        ul_w  = 18.0
        x_sl  = float(_PAGE_W - _R_MARGIN) - sl_w - ul_w - 2.0
        self.set_xy(x_sl, y_info)
        self.cell(sl_w, 7, score_label)
        x0 = self.get_x()
        self.line(x0, baseline, x0 + ul_w, baseline)

        self.set_y(y_info + 8.5)
        self.set_line_width(0.25)
        self.line(_L_MARGIN, self.get_y(), _PAGE_W - _R_MARGIN, self.get_y())
        self.ln(5)

    def _draw_mini_header(self):
        """2페이지 이후: 제목만 작게."""
        self.set_y(13)
        self.set_font(self._krf, size=9)
        self.cell(0, 6, self._title, align='C', new_x='LMARGIN', new_y='NEXT')
        self.set_line_width(0.4)
        self.line(_L_MARGIN, self.get_y(), _PAGE_W - _R_MARGIN, self.get_y())
        self.ln(3)

    def footer(self):
        """컬럼 구분선 + 페이지 번호."""
        sep_x = _L_MARGIN + _COL_W + _COL_GAP / 2
        top_y = getattr(self, '_top_y', 35.0)
        self.set_draw_color(160, 160, 160)
        self.set_line_width(0.25)
        self.line(sep_x, top_y, sep_x, self.h - 18)
        self.set_draw_color(0, 0, 0)
        self.set_left_margin(_L_MARGIN)
        self.set_right_margin(_R_MARGIN)
        self.set_y(self.h - 13)
        self.set_font(self._krf, size=9)
        self.cell(0, 8, f'- {self.page_no()} -', align='C')

    def _min_height_needed(self, prob: dict) -> float:
        has_latex = bool(prob.get('latex', '').strip())
        has_fig   = bool(prob.get('figure') or prob.get('figure_spec'))
        box  = 42 if has_latex else 0
        fig  = 72 if has_fig   else 0
        if prob['type'] == '선택형':
            return 14 + box + fig + (0 if has_fig else 42)
        else:
            return 14 + box + fig + 25

    def add_problem(self, num: int, prob: dict):
        self._need_space(self._min_height_needed(prob))

        score_str = f"({prob['score']}점)"
        text = prob.get('text', '').strip()
        latex = prob.get('latex', '').strip()

        _MATH_INLINE = set('→←↑↓²³')
        _text_has_plain_math = (
            any(c in text for c in _MATH_INLINE) or
            bool(re.search(r'lim\s*\(', text, re.IGNORECASE))
        )
        _inline_done = False
        if _text_has_plain_math and latex and '$' not in text and '\\' not in text:
            m = re.search(r'[가-힣]', text)
            suffix = text[m.start():].strip() if m else ''
            raw = latex.strip()
            if raw.startswith('$') and raw.endswith('$'):
                raw = raw[1:-1].strip()
            raw = raw.replace(r'\frac', r'\dfrac')
            inline = (f"{num}. ${raw}$ {suffix}  {score_str}"
                      if suffix else f"{num}. ${raw}$  {score_str}")
            try:
                img_b, w_mm, h_mm = _render_mixed_text_png(inline, fontsize=13, preprocess=False)
                disp_w = min(w_mm, float(_COL_W))
                disp_h = h_mm * (disp_w / w_mm) if w_mm > 0 else h_mm
                self.image(io.BytesIO(img_b), x=self.l_margin, y=self.get_y(),
                           w=disp_w, h=disp_h)
                self.set_y(self.get_y() + disp_h + 1)
                _inline_done = True
            except Exception:
                pass

        if not _inline_done:
            header = f"{num}. {text}  {score_str}" if text else f"{num}.  {score_str}"
            _has_latex_in_header = '$' in text or '\\' in text or any(c in text for c in _MATH_INLINE)
            if _has_latex_in_header:
                try:
                    img_b, w_mm, h_mm = _render_mixed_text_png(header, fontsize=11)
                    disp_w = min(w_mm, float(_COL_W))
                    disp_h = h_mm * (disp_w / w_mm) if w_mm > 0 else h_mm
                    self.image(io.BytesIO(img_b), x=self.l_margin, y=self.get_y(),
                               w=disp_w, h=disp_h)
                    self.set_y(self.get_y() + disp_h + 1)
                except Exception:
                    self.set_font(self._krf, size=11)
                    self.multi_cell(0, 7, header, align='L', new_x='LMARGIN', new_y='NEXT')
            else:
                self.set_font(self._krf, size=11)
                self.multi_cell(0, 7, header, align='L', new_x='LMARGIN', new_y='NEXT')

        if not _inline_done and latex:
            self._add_math_box(latex)

        _fig = prob.get('figure')
        _spec = prob.get('figure_spec')
        if not _fig and _spec:
            try:
                _fig = render_figure_spec(_spec)
            except Exception:
                pass
        if _fig:
            self._add_figure(_fig)

        if prob['type'] == '선택형':
            self._add_choices(prob.get('choices', []))
        else:
            self.ln(45)

        self.ln(3)
        self.set_x(self.l_margin)

    @staticmethod
    def _unicode_to_latex(s: str) -> str:
        """$...$ 내부용: 유니코드 수식 기호 → LaTeX 명령 변환."""
        def _root_math(text, sym, cmd):
            result, i = [], 0
            while i < len(text):
                if text[i] == sym and i + 1 < len(text) and text[i + 1] == '(':
                    depth, j = 0, i + 1
                    while j < len(text):
                        if text[j] == '(':   depth += 1
                        elif text[j] == ')':
                            depth -= 1
                            if depth == 0: break
                        j += 1
                    inner = text[i + 2:j]
                    if j + 1 < len(text) and text[j + 1] in '²³':
                        exp = 2 if text[j + 1] == '²' else 3
                        result.append(f'{cmd}{{{inner}}}^{{{exp}}}')
                        i = j + 2
                    else:
                        result.append(f'{cmd}{{{inner}}}')
                        i = j + 1
                else:
                    result.append(text[i]); i += 1
            return ''.join(result)
        s = _root_math(s, '√', r'\sqrt')
        s = _root_math(s, '∛', r'\sqrt[3]')
        s = re.sub(r'√(-?\d+(?:\.\d+)?)', lambda m: r'\sqrt{' + m.group(1) + '}', s)
        s = re.sub(r'∛(-?\d+(?:\.\d+)?)', lambda m: r'\sqrt[3]{' + m.group(1) + '}', s)
        s = re.sub(r'√([a-zA-Z])', lambda m: r'\sqrt{' + m.group(1) + '}', s)
        s = re.sub(r'∛([a-zA-Z])', lambda m: r'\sqrt[3]{' + m.group(1) + '}', s)
        s = s.replace('√', r'\surd').replace('∛', r'\sqrt[3]{}')
        for ch, cmd in [('≤', r'\leq'), ('≥', r'\geq'), ('≠', r'\neq'),
                        ('±', r'\pm'), ('×', r'\times'), ('÷', r'\div'),
                        ('∞', r'\infty'), ('π', r'\pi'), ('θ', r'\theta'),
                        ('²', '^{2}'), ('³', '^{3}')]:
            s = s.replace(ch, cmd)
        return s

    @staticmethod
    def _circle_latex_to_mixed(latex: str) -> str:
        """$① \sqrt{...}\n② ...$ 형태를 mixed-text $...$ 형식으로 변환."""
        s = latex.strip()
        if s.startswith('$') and s.endswith('$'):
            s = s[1:-1].strip()
        lines = s.split('\n')
        result = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line[0] in '①②③④⑤':
                circle, rest = line[0], line[1:].strip()
                rest = ExamPDF._unicode_to_latex(rest)
                result.append(f'{circle} ${rest}$')
            else:
                result.append(f'${ExamPDF._unicode_to_latex(line)}$')
        return '\n'.join(result)

    def _add_math_box(self, latex: str):
        if any(c in latex for c in '①②③④⑤'):
            mixed = self._circle_latex_to_mixed(latex)
            try:
                img_b, w_mm, h_mm = _render_mixed_text_png(
                    mixed, fontsize=12, dpi=200, preprocess=False)
            except Exception:
                self.set_font(self._krf, size=9)
                self.cell(0, 6, f"[수식 오류: {latex[:40]}]",
                          new_x='LMARGIN', new_y='NEXT')
                return
        elif _has_korean(latex):
            try:
                img_b, w_mm, h_mm = _render_mixed_text_png(
                    _latex_kr_to_mixed(latex), fontsize=12, dpi=200, preprocess=False)
            except Exception:
                self.set_font(self._krf, size=9)
                self.cell(0, 6, f"[수식 오류: {latex[:40]}]", new_x='LMARGIN', new_y='NEXT')
                return
        else:
            try:
                img_b, w_mm, h_mm = render_math_png(latex, fontsize=15)
            except Exception:
                self.set_font(self._krf, size=9)
                self.cell(0, 6, f"[수식 오류: {latex[:40]}]", new_x='LMARGIN', new_y='NEXT')
                return

        pad   = 3
        col_w = float(_COL_W)
        box_w = min(w_mm + pad * 2, col_w * 0.92)
        img_w = min(w_mm, box_w - pad * 2)
        img_h = h_mm * (img_w / w_mm) if w_mm > 0 else h_mm
        box_h = img_h + pad * 2

        x_box = self.l_margin + (col_w - box_w) / 2
        y_box = self.get_y()

        self.set_draw_color(0)
        self.set_line_width(0.4)
        self.rect(x_box, y_box, box_w, box_h)
        self.image(io.BytesIO(img_b),
                   x=x_box + pad + (box_w - pad*2 - img_w) / 2,
                   y=y_box + pad,
                   w=img_w, h=img_h)
        self.set_y(y_box + box_h + 2)
        self.set_x(self.l_margin)

    def _add_figure(self, fig_bytes: bytes):
        """도형 PNG를 중앙 정렬로 삽입."""
        from PIL import Image as PILImage
        try:
            img = PILImage.open(io.BytesIO(fig_bytes))
            dpi = 180
            w_mm = img.width  / dpi * 25.4
            h_mm = img.height / dpi * 25.4
            max_w = float(_COL_W) * 0.85
            max_h = 63.0
            scale = min(
                max_w / w_mm if w_mm > max_w else 1.0,
                max_h / h_mm if h_mm > max_h else 1.0,
            )
            w_mm *= scale
            h_mm *= scale
            self._need_space(h_mm + 4)
            x = self.l_margin + (float(_COL_W) - w_mm) / 2
            self.image(io.BytesIO(fig_bytes), x=x, y=self.get_y(), w=w_mm, h=h_mm)
            self.set_y(self.get_y() + h_mm + 3)
        except Exception:
            pass

    def _add_choices(self, choices: list):
        PLAIN_H  = 7.5
        MATH_MAX = 10.0

        rendered: dict = {}
        for i in range(min(5, len(choices))):
            ch = choices[i].strip()
            if ch and '$' in ch:
                try:
                    if _has_korean(ch):
                        img_b, w_mm, h_mm = _render_mixed_text_png(
                            ch, fontsize=11, dpi=200, preprocess=False)
                    else:
                        img_b, w_mm, h_mm = render_math_png(ch, fontsize=12, dpi=200, tight=True)
                    rendered[i] = (img_b, w_mm, h_mm)
                except Exception:
                    pass

        for i, cn in enumerate(CIRCLE):
            ch = choices[i].strip() if i < len(choices) else ''
            if not ch:
                continue
            if ch and ch[0] in '①②③④⑤':
                ch = ch[1:].strip()

            self.set_x(self.l_margin + 4)

            if i in rendered:
                img_b, w_mm, h_mm = rendered[i]
                disp_h = min(h_mm, MATH_MAX)
                scale  = disp_h / h_mm if h_mm > 0 else 1
                disp_w = w_mm * scale
                max_w  = self.l_margin + _COL_W - (self.l_margin + 10)
                if disp_w > max_w:
                    disp_w = max_w
                    disp_h = h_mm * (disp_w / w_mm)
                row_h = max(disp_h + 1.5, PLAIN_H)

                self.set_font(self._krf, size=11)
                self.cell(6, row_h, cn)
                cur_x, cur_y = self.get_x(), self.get_y()
                self.image(io.BytesIO(img_b),
                           x=cur_x, y=cur_y + (row_h - disp_h) / 2,
                           w=disp_w, h=disp_h)
                self.set_y(cur_y + row_h)
            else:
                self.set_font(self._krf, size=11)
                self.cell(0, PLAIN_H, f"{cn} {ch}", align='L', new_x='LMARGIN', new_y='NEXT')

    def add_answer_page(self, problems: list):
        self.add_page()
        self.set_font(self._krf, size=13)
        self.cell(0, 10, '[ 정  답 ]', align='C', new_x='LMARGIN', new_y='NEXT')
        self.ln(4)
        self.set_font(self._krf, size=11)
        for i, p in enumerate(problems):
            ans = p.get('answer', '').strip() or '─'
            self.cell(45, 9, f"{i+1}번:  {ans}")
            if (i + 1) % 4 == 0:
                self.ln()
        self.ln()


# ── 도형 렌더링 ─────────────────────────────────────────────────────

def render_figure_spec(spec: dict) -> bytes:
    """figure_spec dict → PNG bytes (고품질 matplotlib 렌더링)."""
    import numpy as np

    has_geom = bool(spec.get('elements'))
    has_func = bool(spec.get('functions'))

    if has_func and not has_geom:
        fig, ax = plt.subplots(figsize=(3.5, 3.0))
        fig.patch.set_facecolor('white')
        _figspec_functions(ax, spec)
    else:
        fig, ax = plt.subplots(figsize=(3.0, 2.8))
        fig.patch.set_facecolor('white')
        ax.set_aspect('equal')
        ax.set_axis_off()
        _figspec_geometry(ax, spec)
        if has_func:
            _figspec_functions(ax, spec)

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=180,
                bbox_inches='tight', pad_inches=0.08, facecolor='white')
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def _figspec_geometry(ax, spec):
    """도형 요소 렌더링 (좌표축 없음)."""
    import numpy as np

    vertex_pos = {}

    def _outer_offset(pos, all_pos, scale=0.26):
        others = [p for p in all_pos if p != pos]
        if not others:
            return (0.0, scale)
        cx = sum(p[0] for p in others) / len(others)
        cy = sum(p[1] for p in others) / len(others)
        dx, dy = pos[0] - cx, pos[1] - cy
        n = (dx**2 + dy**2) ** 0.5 or 1
        return dx / n * scale, dy / n * scale

    for el in spec.get('elements', []):
        shape = el.get('shape', '')

        if shape == 'triangle':
            verts = el['vertices']
            pts = {k: tuple(v) for k, v in verts.items()}
            keys = list(pts.keys())
            xs = [pts[k][0] for k in keys] + [pts[keys[0]][0]]
            ys = [pts[k][1] for k in keys] + [pts[keys[0]][1]]
            ax.plot(xs, ys, 'k-', linewidth=1.8, solid_capstyle='round', zorder=2)
            for k, p in pts.items():
                vertex_pos[k] = p
            if el.get('labels', True):
                all_p = list(pts.values())
                for k, p in pts.items():
                    ox, oy = _outer_offset(p, all_p, 0.28)
                    ax.text(p[0]+ox, p[1]+oy, k, fontsize=12,
                            ha='center', va='center', fontweight='bold')

        elif shape == 'circle':
            cx, cy = el['center']
            r = el['radius']
            ax.add_patch(plt.Circle((cx, cy), r,
                                    fill=False, color='k', linewidth=1.8, zorder=2))
            lbl = el.get('label', '')
            if lbl:
                ax.plot(cx, cy, 'k.', markersize=4)
                ax.text(cx + r*0.07, cy + r*0.09, lbl, fontsize=11, fontweight='bold')
                vertex_pos[lbl] = (cx, cy)

        elif shape == 'segment':
            s, e = tuple(el['start']), tuple(el['end'])
            ax.plot([s[0], e[0]], [s[1], e[1]], 'k-', linewidth=1.8,
                    solid_capstyle='round', zorder=2)
            lbl = el.get('label', '')
            if lbl:
                mx, my = (s[0]+e[0])/2, (s[1]+e[1])/2
                dx, dy = e[0]-s[0], e[1]-s[1]
                n = (dx**2+dy**2)**0.5 or 1
                ax.text(mx - dy/n*0.2, my + dx/n*0.2, lbl,
                        fontsize=10, ha='center', va='center')

        elif shape == 'point':
            px, py = el['pos']
            lbl = el.get('label', '')
            ax.plot(px, py, 'ko', markersize=5, zorder=5)
            if lbl:
                ox, oy = _outer_offset((px, py), list(vertex_pos.values()), 0.22)
                ax.text(px+ox, py+oy, lbl, fontsize=11,
                        fontweight='bold', ha='center', va='center')
                vertex_pos[lbl] = (px, py)

        elif shape == 'right_angle':
            vname = el.get('vertex', '')
            if vname in vertex_pos:
                vx, vy = vertex_pos[vname]
                sq = 0.18
                neighbors = []
                for el2 in spec.get('elements', []):
                    if el2.get('shape') == 'triangle' and vname in el2['vertices']:
                        vd = el2['vertices']
                        ks = list(vd.keys())
                        i = ks.index(vname)
                        neighbors = [np.array(vd[ks[(i-1)%3]]),
                                     np.array(vd[ks[(i+1)%3]])]
                        break
                v = np.array([vx, vy])
                if len(neighbors) == 2:
                    d1 = neighbors[0] - v; d1 = d1 / (np.linalg.norm(d1) or 1) * sq
                    d2 = neighbors[1] - v; d2 = d2 / (np.linalg.norm(d2) or 1) * sq
                    corners = [v, v+d1, v+d1+d2, v+d2]
                else:
                    corners = [[vx,vy],[vx+sq,vy],[vx+sq,vy+sq],[vx,vy+sq]]
                from matplotlib.patches import Polygon as MplPoly
                ax.add_patch(MplPoly(corners, closed=True,
                                     fill=False, edgecolor='k', linewidth=1.2, zorder=3))

        elif shape == 'angle_mark':
            vname = el.get('vertex', '')
            deg   = el.get('degree', 0)
            if vname in vertex_pos:
                vx, vy = vertex_pos[vname]
                v = np.array([vx, vy])
                a1, a2 = 0.0, float(deg)
                for el2 in spec.get('elements', []):
                    if el2.get('shape') == 'triangle' and vname in el2['vertices']:
                        vd = el2['vertices']
                        ks = list(vd.keys())
                        i = ks.index(vname)
                        n1 = np.array(vd[ks[(i-1)%3]]) - v
                        n2 = np.array(vd[ks[(i+1)%3]]) - v
                        a1 = float(np.degrees(np.arctan2(n1[1], n1[0])))
                        a2 = float(np.degrees(np.arctan2(n2[1], n2[0])))
                        if a2 < a1: a1, a2 = a2, a1
                        if a2 - a1 > 180: a1 += 360
                        break
                from matplotlib.patches import Arc
                ax.add_patch(Arc((vx, vy), 0.4, 0.4, angle=0,
                                 theta1=min(a1,a2), theta2=max(a1,a2),
                                 color='#444', linewidth=1.2, zorder=3))
                mid = np.radians((a1+a2)/2)
                ax.text(vx + 0.32*np.cos(mid), vy + 0.32*np.sin(mid),
                        f'{deg}°', fontsize=8.5, ha='center', va='center', color='#444')

    ax.autoscale_view()
    ax.margins(0.22)


def _figspec_functions(ax, spec):
    """함수 그래프 렌더링."""
    import numpy as np

    xrange_ = spec.get('xrange', [-5, 5])
    yrange_ = spec.get('yrange', None)
    marked_x = spec.get('marked_x', [])
    marked_y = spec.get('marked_y', [])

    xmin, xmax = xrange_
    margin = (xmax - xmin) * 0.1

    ax.spines['left'].set_position('zero')
    ax.spines['bottom'].set_position('zero')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    for sp in ['left', 'bottom']:
        ax.spines[sp].set_linewidth(1.3)

    ax.set_xlim(xmin - margin, xmax + margin)
    ylim_set = False
    if yrange_:
        ax.set_ylim(yrange_[0], yrange_[1])
        ylim_set = True

    ax.plot(1, 0, '>k', transform=ax.get_yaxis_transform(),
            clip_on=False, markersize=5)
    ax.plot(0, 1, '^k', transform=ax.get_xaxis_transform(),
            clip_on=False, markersize=5)

    ylim = ax.get_ylim()
    ax.text(xmax + margin*0.95, -0.02*(ylim[1]-ylim[0]),
            'x', fontsize=12, ha='center', va='top')
    ax.text(0.02*(xmax-xmin), ylim[1],
            'y', fontsize=12, ha='left', va='bottom')
    ax.text(-0.02*(xmax-xmin), -0.02*(ylim[1]-ylim[0]),
            'O', fontsize=10, ha='right', va='top')

    ax.set_xticks(marked_x)
    ax.set_xticklabels([str(v) for v in marked_x], fontsize=9)
    ax.set_yticks(marked_y)
    ax.set_yticklabels([str(v) for v in marked_y], fontsize=9)
    ax.tick_params(length=4, width=1)

    xs = np.linspace(xmin, xmax, 1500)
    colors = ['#1565C0', '#C62828', '#2E7D32', '#6A1B9A']
    ys_list = []
    funcs = spec.get('functions', [])

    for idx, fn in enumerate(funcs):
        expr  = fn['expr']
        lbl   = fn.get('label', '')
        color = colors[idx % len(colors)]
        try:
            ys = eval(expr, {'x': xs, 'np': np, '__builtins__': {}})
            ys = np.where(np.abs(ys) > 1e5, np.nan, np.array(ys, dtype=float))
            ax.plot(xs, ys, color=color, linewidth=2.0, zorder=3)
            if lbl:
                for xi, yi in zip(xs[::-1], ys[::-1]):
                    if not np.isnan(yi):
                        ax.text(xi, yi, f' {lbl}', fontsize=10,
                                color=color, va='center')
                        break
            ys_list.append((xs, ys))
        except Exception:
            pass

    if len(ys_list) >= 2:
        y1s, y2s = ys_list[0][1], ys_list[1][1]
        diff = y1s - y2s
        for sc in np.where(np.diff(np.sign(diff)))[0]:
            if diff[sc+1] == diff[sc]: continue
            ix = xs[sc] - diff[sc]*(xs[sc+1]-xs[sc])/(diff[sc+1]-diff[sc])
            try:
                iy = float(eval(funcs[0]['expr'],
                                {'x': ix, 'np': np, '__builtins__': {}}))
                ax.plot(ix, iy, 'ko', markersize=5, zorder=5)
            except Exception:
                pass

    if not ylim_set:
        ax.relim(); ax.autoscale_view()


# ── 공개 API ────────────────────────────────────────────────────────

def export_to_pdf(exam_info: dict, problems: list, filepath: str,
                  with_answers: bool = False):
    """PDF를 파일로 저장."""
    total_score = sum(p.get('score', 0) for p in problems)
    pdf = ExamPDF(
        title=exam_info.get('title', '수학 시험지'),
        subtitle=exam_info.get('subtitle', ''),
        total_score=total_score,
    )
    pdf.add_page()
    for i, prob in enumerate(problems):
        pdf.add_problem(i + 1, prob)
    if with_answers:
        pdf.add_answer_page(problems)
    pdf.output(filepath)


def export_to_pdf_bytes(exam_info: dict, problems: list,
                        with_answers: bool = False) -> bytes:
    """PDF를 bytes로 반환 (FastAPI StreamingResponse 용)."""
    total_score = sum(p.get('score', 0) for p in problems)
    pdf = ExamPDF(
        title=exam_info.get('title', '수학 시험지'),
        subtitle=exam_info.get('subtitle', ''),
        total_score=total_score,
    )
    pdf.add_page()
    for i, prob in enumerate(problems):
        pdf.add_problem(i + 1, prob)
    if with_answers:
        pdf.add_answer_page(problems)
    return bytes(pdf.output())
