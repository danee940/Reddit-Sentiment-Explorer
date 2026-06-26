# Reddit Sentiment Explorer

A query-driven platform for analyzing sentiment of user-entered terms across Reddit communities. Enter a term, pick subreddits and a content language, and the app collects matching Reddit content, runs sentiment classification, and displays charts in a dashboard.

Stack: `Arctic Shift` (data), `OpenAI`, `mock`, or local XLM-RoBERTa (`SENTIMENT_PROVIDER=xlm_roberta`, multilingual Transformers model) for sentiment, `FastAPI` (API), `Plotly Dash` (dashboard), `PostgreSQL` (storage), `Docker Compose` (orchestration).

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
- `uv` for local dependency management and project commands

## Environment Variables

Copy `.env.example` to `.env`. Key variables:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `ARCTIC_SHIFT_BASE_URL` | Arctic Shift API base URL |
| `ARCTIC_SHIFT_CONCURRENCY` | Max concurrent Arctic Shift requests during collection |
| `SENTIMENT_PROVIDER` | `mock`, `openai`, or `xlm_roberta` |
| `LLM_API_KEY` | API key for OpenAI |
| `LLM_MODEL` | Model name, e.g. `gpt-4o-mini` |
| `SENTIMENT_CONCURRENCY` | Max concurrent sentiment classification calls |
| `DEFAULT_SUBREDDITS` | Comma-separated default subreddit list |
| `INTEGRATION_DATABASE_URL` | PostgreSQL URL for integration tests (dedicated database) |

Use `SENTIMENT_PROVIDER=mock` for development without API cost for classification.

## Run With Docker

```bash
docker compose up --build -d   # start
docker compose logs -f         # follow logs
docker compose down            # stop
```

## Deploy On Railway

The repo ships three Railway config files so each service in a Railway project can point to the same repo but run a different process. Create three services in the same Railway project and set the `Config-as-code` path on each:

| Service   | Config file              | Purpose                          |
| --------- | ------------------------ | -------------------------------- |
| api       | `railway.api.json`       | FastAPI backend (uvicorn)        |
| dashboard | `railway.dashboard.json` | Plotly Dash UI (gunicorn)        |
| worker    | `railway.worker.json`    | Background pipeline runner       |

Add a Postgres plugin to the project and link `DATABASE_URL` from it to all three services. The dashboard also needs `API_BASE_URL` set to the API's private address, for example:

```
API_BASE_URL=http://${{api.RAILWAY_PRIVATE_DOMAIN}}:${{api.PORT}}
```

Generate a public domain on the `api` and `dashboard` services. The `worker` does not need public networking.

## Run Locally

```bash
uv sync --extra dev
source .venv/bin/activate
./scripts/start-local-dev.sh   # background; logs with timestamps in logs/*.log
./scripts/stop-local-dev.sh    # stop API, dashboard, and worker
```

The script starts `db` in Docker and runs the API, dashboard, and worker locally in the background, then returns. To restart only the dashboard during UI work: `./scripts/restart-dashboard.sh`.

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
uv run pytest
```

Optional API integration tests against PostgreSQL (they truncate application tables; use a dedicated database). Set `INTEGRATION_DATABASE_URL` in `.env`, then run:

```bash
uv run ./scripts/run-integration-tests.sh
```

The script starts Docker Compose’s `db` service, creates the test database if needed, and runs `pytest tests/integration`. CI sets `INTEGRATION_DATABASE_URL` as a workflow environment variable and runs the same suite against a Postgres service container.

### Sentiment provider comparison

For any completed query run that already has stored sentiment results (typically from OpenAI), compare **three** ways of labeling the same documents: those stored labels, a fresh **mock** (heuristic) pass, and a fresh **XLM-RoBERTa** pass (`cardiffnlp/twitter-xlm-roberta-base-sentiment-multilingual`). The script prints label distributions, pairwise agreement rates, and confusion matrices, and writes JSON to `scripts/all_providers_comparison.json`.

```bash
uv run python scripts/compare_all_providers.py <query_run_id>
```

The `query_run_id` is the UUID of a completed `query_runs` row (visible in the API or database). The first XLM-RoBERTa classification loads the model into memory and can take a short while.

## Troubleshooting

If local Python commands pick up the wrong database, unset or override `DATABASE_URL`:

```bash
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_sentiment uv run python -m uvicorn ...
```
