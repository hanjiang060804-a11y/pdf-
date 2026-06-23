# 墨流 2.0 云 API — 生产镜像
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PDF_TRA_CONFIG=/data/config.json \
    PDF_TRA_UPLOAD_DIR=/data/uploads \
    PDF_TRA_PORT=8787

WORKDIR /app

# poppler: pdfinfo / pdftotext（pdf2zh 依赖）
RUN apt-get update \
    && apt-get install -y --no-install-recommends poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pdf_tra ./pdf_tra
COPY prompts ./prompts
COPY config.example.json ./config.example.json

RUN mkdir -p /data/uploads

EXPOSE 8787

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8787/health')" || exit 1

CMD ["python", "-m", "pdf_tra.cloud"]
