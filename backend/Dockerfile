FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi \
    greenlet \
    uvicorn[standard] \
    pydantic-settings \
    sqlmodel \
    aiosqlite

COPY backend/app ./app

CMD ["python", "-m", "app.run"]
