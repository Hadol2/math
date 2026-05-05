import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from math_maker import export_to_pdf, _LATEX_OK
print("LaTeX OK:", _LATEX_OK)

problems = [
    {
        "type":    "선택형",
        "score":   3,
        "text":    "다음 수열의 합을 구하시오. (단, n ≥ 1)",
        "latex":   r"$\sum_{k=1}^{n} \frac{k}{k+1}$",
        "choices": [
            r"$\frac{n}{n+1}$",
            r"$\frac{n^2}{n+1}$",
            r"$n - \ln(n+1)$",
            r"$\frac{n(n+2)}{2(n+1)}$",
            r"$\frac{n^2+n-1}{n+1}$",
        ],
        "answer":  "②",
    },
    {
        "type":    "서술형",
        "score":   4,
        "text":    "√((x+1)(x-1)) = 4 를 만족하는 양수 x를 구하시오.",
        "latex":   "",
        "choices": ["", "", "", "", ""],
        "answer":  r"x = \sqrt{17}",
    },
    {
        "type":    "선택형",
        "score":   3,
        "text":    "다음 극한값을 구하시오.",
        "latex":   r"$\lim_{x \to 0} \frac{\sin x}{x}$",
        "choices": ["0", "1", r"$\infty$", r"$\frac{1}{2}$", "정의되지 않는다"],
        "answer":  "②",
    },
    {
        "type":    "선택형",
        "score":   4,
        "text":    "다음 중 옳은 것을 모두 고르면? (단, a > 0, b > 0)",
        "latex":   "① √(a²+b²) ≥ a+b\n② √(ab) ≤ (a+b)/2\n③ a ≠ b 이면 √(a²+b²) > √(2ab)",
        "choices": ["①", "②", "③", "①③", "②③"],
        "answer":  "⑤",
    },
]

exam_info = {"title": "수학 예시 시험지", "subtitle": "고등학교 2학년"}
out = os.path.join(os.path.dirname(__file__), "예시시험지_LaTeX.pdf")
export_to_pdf(exam_info, problems, out, with_answers=True)
print("저장:", out)
