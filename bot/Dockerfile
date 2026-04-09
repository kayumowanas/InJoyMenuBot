FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    aiogram \
    httpx \
    pillow \
    pydantic-settings

COPY bot ./bot

WORKDIR /app/bot
CMD ["python", "bot.py"]
