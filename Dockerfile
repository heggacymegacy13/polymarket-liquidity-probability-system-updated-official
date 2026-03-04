FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY polymarket_bot ./polymarket_bot

RUN pip install --upgrade pip && \
    pip install .

COPY scripts ./scripts

CMD ["polymarket-bot", "run-all", "--config-dir", "./config"]

