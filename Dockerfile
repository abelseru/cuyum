FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

COPY app ./app
COPY config ./config
COPY scripts ./scripts
COPY static ./static
COPY templates ./templates
COPY VERSION README.md LICENSE ./
COPY docker-entrypoint.sh ./

RUN chmod +x /app/docker-entrypoint.sh

EXPOSE 5050

HEALTHCHECK \
  --interval=30s \
  --timeout=5s \
  --start-period=30s \
  --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5050/lite', timeout=4)"

ENTRYPOINT ["/app/docker-entrypoint.sh"]
