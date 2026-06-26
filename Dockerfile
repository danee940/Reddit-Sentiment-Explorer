FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.8.19 /uv /uvx /bin/

COPY pyproject.toml README.md alembic.ini ./
COPY src ./src

RUN uv sync --no-dev

ENV PATH="/app/.venv/bin:$PATH"

CMD ["uvicorn", "reddit_sentiment.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
