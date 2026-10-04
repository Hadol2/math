# math

수학 시험 문제 편집기와 변형 모의고사 생성 도구. 수식은 LaTeX(없으면 matplotlib mathtext)로 렌더링하고, 결과는 시험지 형태의 PDF로 내보낸다.

## 구성

| 경로 | 설명 |
|---|---|
| `math_maker.py` | tkinter 기반 문제 편집기 GUI. 문제·수식·도형을 편집하고 JSON 저장/불러오기, PDF 출력 |
| `figure_drawer.py` | 문제용 도형·그래프 그리기 (`make_figure`) |
| `render_variants.py` | `exam_variants.json` → 세트별 PDF (`variant_set{n}.pdf`) |
| `convert_json.py` | `exam_variants.json` → `math_maker.py`용 `set1~5.json` |
| `convert_exam_problems.py` | `exam_problems.json` → `examA.json`, `examB.json` |
| `gen_sample.py` | 샘플 문제로 PDF 출력 테스트 |
| `math_web/` | 웹 버전 (FastAPI). 로그인(JWT), 문제 DB(SQLite), 시험지 PDF/이미지 가져오기, Claude API로 문제 추출·변형 문제 생성 |

## 실행

데스크톱 도구 (Python 3, `matplotlib`, `numpy`, `fpdf2`, `Pillow` 필요. LaTeX가 설치되어 있으면 수식 품질이 좋아짐):

```sh
python math_maker.py          # 편집기 GUI
python render_variants.py     # 변형 문제 PDF 생성
```

웹 버전:

```sh
cd math_web
cp .env.example .env          # ANTHROPIC_API_KEY, SECRET_KEY 설정
pip install -r requirements.txt
uvicorn app.main:app --reload
```

또는 `docker build -t math-web math_web && docker run -p 8000:8000 --env-file math_web/.env math-web`.
