FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV OLLAMA_HOST=127.0.0.1:11434
ENV OLLAMA_MODELS=/var/data/ollama

RUN apt-get update && apt-get install -y curl ca-certificates zstd \
    && curl -fsSL https://ollama.com/install.sh | sh \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .
RUN chmod +x /app/start.sh

CMD ["/app/start.sh"]
