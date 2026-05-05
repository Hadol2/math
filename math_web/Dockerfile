FROM python:3.11-slim

# 시스템 패키지: texlive + 한글 폰트 + poppler(pdftoppm)
RUN apt-get update && apt-get install -y --no-install-recommends \
    texlive-latex-base \
    texlive-latex-extra \
    texlive-fonts-recommended \
    texlive-lang-cjk \
    fonts-nanum \
    poppler-utils \
    fontconfig \
    && fc-cache -fv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV MATHMAKER_CACHE=/app/.cache/MathMaker
RUN mkdir -p /app/.cache/MathMaker

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
