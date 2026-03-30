# Reddit Sentiment Explorer

A query-driven platform for analyzing sentiment of user-entered terms across Reddit communities. Enter a term, pick subreddits and a content language, and the app collects matching Reddit content, runs sentiment classification, and displays charts in a dashboard.

Stack: `Arctic Shift` (data), `OpenAI` or `mock` (sentiment), `FastAPI` (API), `Plotly Dash` (dashboard), `PostgreSQL` (storage), `Docker Compose` (orchestration).

## Architecture

Four services:

- `api` — FastAPI, exposes query, chart, and document endpoints (`http://localhost:8000`)
- `dashboard` — Plotly Dash search and analytics UI (`http://localhost:8050`)
- `worker` — background query execution pipeline
- `db` — PostgreSQL (`localhost:5432`)

Flow: user submits a term → API creates or reuses a query run → worker fetches posts/comments via Arctic Shift → language-filtered documents are stored → sentiment is generated → aggregates are returned to the dashboard.

The API and worker run Alembic migrations on startup with a startup lock to prevent races.

## Requirements

- Docker Desktop or Docker Engine + Docker Compose
- Python `3.12` for local execution (`pyenv` recommended if your system Python is older)

## Environment Variables

Copy `.env.example` to `.env`. Key variables:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `ARCTIC_SHIFT_BASE_URL` | Arctic Shift API base URL |
| `LLM_PROVIDER` | `mock` or `openai` |
| `LLM_API_KEY` | API key for OpenAI |
| `LLM_MODEL` | Model name, e.g. `gpt-4o-mini` |
| `DEFAULT_SUBREDDITS` | Comma-separated default subreddit list |
| `INTEGRATION_DATABASE_URL` | PostgreSQL URL for integration tests (dedicated database) |

Use `LLM_PROVIDER=mock` for development without LLM cost.

## Run With Docker

```bash
docker compose up --build -d   # start
docker compose logs -f         # follow logs
docker compose down            # stop
```

## Run Locally

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip && pip install -e ".[dev]"
./scripts/start-local-dev.sh        # logs to logs/*.log
./scripts/start-local-dev.sh true   # stream logs to terminal
```

The script starts `db` in Docker and runs the API, dashboard, and worker locally. To restart only the dashboard during UI work: `./scripts/restart-dashboard.sh`.

## How To Use The App

1. Open `http://localhost:8050`
2. Enter a search term and review the subreddit list
3. Submit the query and wait for the run to complete
4. Inspect sentiment charts, heatmap, subreddit breakdown, phrase drivers, and matched documents

API shortcut:

```bash
curl -X POST http://localhost:8000/queries \
  -H "Content-Type: application/json" \
  -d '{"term":"Big Mac","subreddits":["hungary","askhungary","budapest"],"content_language":"hu"}'
```

## Testing

```bash
python -m pytest
```

Optional API integration tests against PostgreSQL (they truncate application tables; use a dedicated database). Set `INTEGRATION_DATABASE_URL` in `.env`, then run:

```bash
./scripts/run-integration-tests.sh
```

The script starts Docker Compose’s `db` service, creates the test database if needed, and runs `pytest tests/integration`. CI sets `INTEGRATION_DATABASE_URL` as a workflow environment variable and runs the same suite against a Postgres service container.

## Troubleshooting

If local Python commands pick up the wrong database, unset or override `DATABASE_URL`:

```bash
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_sentiment python -m uvicorn ...
```
