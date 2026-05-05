#!/usr/bin/env python3
"""시험지 도형 렌더러 — matplotlib으로 PNG 반환."""

import io, re, os, sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import font_manager as fm
import numpy as np

# ── 폰트 (math_maker와 동일 방식) ────────────────────────────────────
_GOTHIC_PATH   = None
_MYEONGJO_PATH = None
for _f in fm.fontManager.ttflist:
    if _f.name == 'Nanum Gothic'   and _GOTHIC_PATH   is None: _GOTHIC_PATH   = _f.fname
    if _f.name == 'Nanum Myeongjo' and _MYEONGJO_PATH is None: _MYEONGJO_PATH = _f.fname

_KR_PROP = fm.FontProperties(fname=_MYEONGJO_PATH or _GOTHIC_PATH) \
           if (_MYEONGJO_PATH or _GOTHIC_PATH) else fm.FontProperties()


def _label(ax, x, y, text, **kw):
    """수식 또는 한글 라벨 출력 (fontproperties 자동 적용)."""
    kw.setdefault('fontsize', 10)
    kw.setdefault('ha', 'center')
    kw.setdefault('va', 'center')
    ax.text(x, y, text, fontproperties=_KR_PROP, **kw)


def _dim_arrow(ax, x0, y0, x1, y1, text, offset_x=0, offset_y=0, rot=0):
    """치수선(양방향 화살표) + 라벨."""
    ax.annotate('', xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle='<->', color='#444', lw=0.9,
                                shrinkA=0, shrinkB=0))
    mx, my = (x0+x1)/2 + offset_x, (y0+y1)/2 + offset_y
    _label(ax, mx, my, text, fontsize=9.5, rotation=rot,
           color='#222', bbox=dict(fc='white', ec='none', pad=1))


def _to_png(fig, dpi=150) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=dpi, bbox_inches='tight',
                pad_inches=0.15, facecolor='white')
    plt.close(fig)
    buf.seek(0)
    return buf.read()


# ══════════════════════════════════════════════════════════════════════
# 1. 빗금 직사각형 (큰 사각형 − 작은 사각형)
# ══════════════════════════════════════════════════════════════════════

def draw_hatched_rect(large_w: str, large_h: str,
                      small_w: str, small_h: str) -> bytes:
    """큰 직사각형에서 작은 직사각형(오른쪽 위)을 뺀 빗금 영역."""
    W, H = 5.0, 3.5   # 큰 사각형 비례 크기
    sw, sh = 1.6, 1.8  # 작은 사각형

    fig, ax = plt.subplots(figsize=(5.5, 4.0))

    # 큰 사각형 (빗금)
    big = mpatches.Rectangle((0, 0), W, H, lw=1.4, ec='black',
                               fc='#e8e8e8', hatch='///')
    ax.add_patch(big)

    # 작은 사각형 (흰색, 오른쪽 위 귀퉁이)
    small = mpatches.Rectangle((W-sw, H-sh), sw, sh, lw=1.4, ec='black', fc='white')
    ax.add_patch(small)

    # 내부 구분선 (L자 경계 강조)
    ax.plot([W-sw, W-sw], [0, H-sh], color='black', lw=1.0, ls='--', alpha=0.4)
    ax.plot([0, W-sw], [H-sh, H-sh], color='black', lw=1.0, ls='--', alpha=0.4)

    # 치수선 — 큰 사각형
    _dim_arrow(ax, 0, -0.4, W, -0.4, large_w, offset_y=-0.22)
    _dim_arrow(ax, -0.4, 0, -0.4, H, large_h, offset_x=-0.45, rot=90)

    # 치수선 — 작은 사각형
    _dim_arrow(ax, W-sw, H+0.35, W, H+0.35, small_w, offset_y=0.2)
    _dim_arrow(ax, W+0.35, H-sh, W+0.35, H, small_h, offset_x=0.4, rot=90)

    ax.set_xlim(-1.3, W+1.5)
    ax.set_ylim(-0.95, H+0.9)
    ax.set_aspect('equal')
    ax.axis('off')

    return _to_png(fig)


# ══════════════════════════════════════════════════════════════════════
# 2. 사다리꼴 + 직사각형
# ══════════════════════════════════════════════════════════════════════

def draw_trapezoid_rect(trap_short: str, trap_long: str,
                        height: str,
                        rect_w: str, rect_h: str,
                        trap_short_val: float = 1.5,
                        trap_long_val: float = 2.8,
                        height_val: float = 1.8,
                        rect_w_val: float = 1.2,
                        rect_h_val: float = 1.8) -> bytes:
    """사다리꼴(위) + 직사각형(아래 왼쪽)을 한 그림에 그림."""
    # 사다리꼴 — 사각형 위에 중앙 정렬
    rx = 0.0                    # 직사각형 왼쪽 x
    ry = 0.0                    # 직사각형 아래 y

    # 직사각형 꼭짓점
    R = np.array([[rx, ry],
                  [rx+rect_w_val, ry],
                  [rx+rect_w_val, ry+rect_h_val],
                  [rx, ry+rect_h_val]])

    # 사다리꼴 꼭짓점: 윗면(short) 중앙 정렬, 아랫면(long)
    long_x0 = rx - (trap_long_val - rect_w_val) / 2  # 아랫면 시작 x
    short_x0 = long_x0 + (trap_long_val - trap_short_val) / 2  # 윗면 시작 x
    trap_y0 = ry + rect_h_val                         # 사다리꼴 아래 y
    trap_y1 = trap_y0 + height_val                    # 사다리꼴 위 y

    T = np.array([[long_x0, trap_y0],
                  [long_x0 + trap_long_val, trap_y0],
                  [short_x0 + trap_short_val, trap_y1],
                  [short_x0, trap_y1]])

    fig, ax = plt.subplots(figsize=(6.0, 5.5))

    # 사다리꼴
    trap_patch = plt.Polygon(T, closed=True, lw=1.4, ec='black', fc='#f0f4ff')
    ax.add_patch(trap_patch)

    # 직사각형
    rect_patch = plt.Polygon(R, closed=True, lw=1.4, ec='black', fc='#fff4e0')
    ax.add_patch(rect_patch)

    # ── 라벨 ──────────────────────────────────────────────────────────

    # 사다리꼴 위 변 (짧은 변)
    _dim_arrow(ax,
               short_x0, trap_y1 + 0.25,
               short_x0 + trap_short_val, trap_y1 + 0.25,
               trap_short, offset_y=0.18)

    # 사다리꼴 아래 변 (긴 변)
    _dim_arrow(ax,
               long_x0, trap_y0 - 0.25,
               long_x0 + trap_long_val, trap_y0 - 0.25,
               trap_long, offset_y=-0.2)

    # 높이 (사다리꼴 왼쪽 외부)
    h_x = long_x0 - 0.45
    ax.annotate('', xy=(h_x, trap_y1), xytext=(h_x, trap_y0),
                arrowprops=dict(arrowstyle='<->', color='#444', lw=0.9,
                                shrinkA=0, shrinkB=0))
    _label(ax, h_x - 0.45, (trap_y0+trap_y1)/2,
           f'높이\n{height}', fontsize=9, ha='right', va='center')

    # 직사각형 가로
    _dim_arrow(ax,
               rx, ry - 0.28,
               rx + rect_w_val, ry - 0.28,
               rect_w, offset_y=-0.2)

    # 직사각형 세로
    _dim_arrow(ax,
               rx + rect_w_val + 0.3, ry,
               rx + rect_w_val + 0.3, ry + rect_h_val,
               rect_h, offset_x=0.45, rot=90)

    # 꼭짓점 라벨 위치 여유
    margin = 0.25
    ax.set_xlim(long_x0 - 1.3, long_x0 + trap_long_val + 1.5)
    ax.set_ylim(ry - 0.85, trap_y1 + 0.85)
    ax.set_aspect('equal')
    ax.axis('off')

    return _to_png(fig)


# ══════════════════════════════════════════════════════════════════════
# 파서: question 문자열에서 도형 파라미터 추출
# ══════════════════════════════════════════════════════════════════════

def _sqrt_label(n: str) -> str:
    """'2' → '√2' 형태 라벨 반환."""
    return f'√{n}'


def parse_hatched_rect(question: str) -> bytes:
    """선택형14 빗금 직사각형 파싱 → PNG."""
    m = re.search(
        r'큰 사각형[:\s]*\(([^)]+)\)\s*[×x]\s*\(([^)]+)\)'
        r'.*?작은 사각형[:\s]*\(([^)]+)\)\s*[×x]\s*\(([^)]+)\)',
        question, re.DOTALL)
    if not m:
        return None
    lw, lh, sw, sh = [s.strip() for s in m.groups()]
    return draw_hatched_rect(lw, lh, sw, sh)


def parse_trapezoid_rect(question: str) -> bytes:
    """서술형8 사다리꼴+직사각형 파싱 → PNG."""
    # 사다리꼴 두 변 (첫 두 개 XX=√N)
    sides = re.findall(r'[A-Z]{2}=√(\d+)', question)
    # 높이
    hm = re.search(r'높이=√(\d+)', question)
    # 직사각형 가로/세로
    rw_m = re.search(r'직사각형 가로=√(\d+)', question)
    rh_m = re.search(r'(?:직사각형 )?세로=√(\d+)', question)

    if len(sides) < 2 or not hm:
        return None

    s1_val = float(sides[0])
    s2_val = float(sides[1])
    h_val  = float(hm.group(1))

    # 직사각형 치수
    if rw_m and rh_m:
        rw_val = float(rw_m.group(1))
        rh_val = float(rh_m.group(1))
    else:
        # set1처럼 CD=√N 하나만 있으면 정사각형으로 처리
        cd_m = re.search(r'CD=√(\d+)', question)
        if cd_m:
            rw_val = rh_val = float(cd_m.group(1))
        else:
            rw_val = rh_val = h_val  # fallback

    # 두 변 중 큰 것이 아랫변(긴 변), 작은 것이 윗변(짧은 변)
    short_val = min(s1_val, s2_val)
    long_val  = max(s1_val, s2_val)
    short_lbl = _sqrt_label(str(int(s1_val)) if s1_val == int(s1_val) else str(s1_val))
    long_lbl  = _sqrt_label(str(int(s2_val)) if s2_val == int(s2_val) else str(s2_val))
    if s1_val > s2_val:
        short_lbl, long_lbl = long_lbl, short_lbl

    h_lbl  = _sqrt_label(str(int(h_val))  if h_val  == int(h_val)  else str(h_val))
    rw_lbl = _sqrt_label(str(int(rw_val)) if rw_val == int(rw_val) else str(rw_val))
    rh_lbl = _sqrt_label(str(int(rh_val)) if rh_val == int(rh_val) else str(rh_val))

    # 그리기 비례 크기 (값의 제곱근을 비례 크기로)
    import math
    sc = 1.2   # 스케일 계수
    return draw_trapezoid_rect(
        trap_short=short_lbl, trap_long=long_lbl,
        height=h_lbl, rect_w=rw_lbl, rect_h=rh_lbl,
        trap_short_val=math.sqrt(short_val) * sc,
        trap_long_val =math.sqrt(long_val)  * sc,
        height_val    =math.sqrt(h_val)     * sc,
        rect_w_val    =math.sqrt(rw_val)    * sc,
        rect_h_val    =math.sqrt(rh_val)    * sc,
    )


def make_figure(question: str) -> bytes:
    """question 문자열을 보고 도형 PNG를 반환. 해당 없으면 None."""
    if '빗금' in question and '큰 사각형' in question:
        return parse_hatched_rect(question)
    if '사다리꼴' in question and '직사각형' in question and '높이' in question:
        return parse_trapezoid_rect(question)
    return None
