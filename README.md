# Reddit Sentiment Explorer

Reddit Sentiment Explorer is a query-driven platform for analyzing the sentiment of user-entered terms across Reddit communities with a user-selected content language.

## What The App Does

The app lets you enter a term such as `Big Mac`, choose the subreddits to search, pick the Reddit content language to keep, collect matching Reddit content, run sentiment classification, store the results, and show charts in a dashboard.

The current setup uses:

- `Arctic Shift` for Reddit data collection
- `OpenAI` or `mock` for sentiment classification
- `FastAPI` for the backend API
- `Plotly Dash` for the dashboard
- `PostgreSQL` for storage
- `Docker Compose` for running the full stack

## Default Scope

- Default scope comes from `DEFAULT_SUBREDDITS`
- Dashboard users can replace the scope with a custom subreddit list
- Primary data source: `Arctic Shift`
- Matching: case-insensitive phrase match with token fallback for multi-word queries
- Language filter: keep the selected content language only
- Sentiment labels: `very_negative`, `negative`, `neutral`, `positive`, `very_positive`
- Sentiment score mapping: `-2` to `2`
- Runtime model: batch query runs with cached reuse
- Confidence-aware sentiment output with rationale text

## Architecture

The stack is split into four services:

- `api`: FastAPI application exposing query, chart, and document endpoints
- `dashboard`: Plotly Dash application for search and analytics views
- `worker`: background query execution pipeline
- `db`: PostgreSQL storage

High-level flow:

1. User enters a term in the dashboard.
2. The API creates or reuses a query run.
3. The worker fetches matching Reddit content through Arctic Shift.
4. Documents in the selected content language are filtered and stored.
5. Sentiment is generated for matched documents.
6. Aggregates are built and returned to the dashboard.

Startup behavior:

- the API and worker run Alembic migrations on startup
- existing local schemas without `alembic_version` are stamped once for safer upgrades
- startup migration work is serialized with a lock so the API and worker do not race each other

## Ports

When running with Docker Compose, the services are exposed on:

- `API`: `http://localhost:8000`
- `Dashboard`: `http://localhost:8050`
- `PostgreSQL`: `localhost:5432`

## Requirements

For the Docker path:

- Docker Desktop or Docker Engine
- Docker Compose

For local Python execution:

- Python `3.12`
- `pyenv` is recommended if your system Python is older

## Environment Variables

Copy `.env.example` to `.env` and configure the values you need.

Main variables:

- `DATABASE_URL`
- `ARCTIC_SHIFT_BASE_URL`
- `ARCTIC_SHIFT_REQUEST_LIMIT`
- `ARCTIC_SHIFT_COMMENT_LIMIT`
- `LLM_PROVIDER`
- `LLM_API_KEY`
- `LLM_API_BASE_URL`
- `LLM_MODEL`
- `DEFAULT_SUBREDDITS`

`ARCTIC_SHIFT_REQUEST_LIMIT` and `ARCTIC_SHIFT_COMMENT_LIMIT` accept either a number or `auto`.

### Sentiment Provider Modes

Use `mock` for development without LLM cost:

```env
LLM_PROVIDER=mock
```

Use OpenAI for real sentiment classification:

```env
LLM_PROVIDER=openai
LLM_API_KEY=your_api_key
LLM_MODEL=gpt-4o-mini
```

## Run With Docker

Start the full stack:

```bash
docker compose up --build -d
```

Check running services:

```bash
docker compose ps
```

View logs:

```bash
docker compose logs -f
```

Stop the stack:

```bash
docker compose down
```

## Run Locally

Create a virtual environment and install dependencies:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"
```

Recommended local workflow:

```bash
./scripts/start-local-dev.sh
```

Show live logs in the same terminal (API + dashboard + worker):

```bash
./scripts/start-local-dev.sh true
```

This script:

- starts `db` with Docker Compose
- runs the API locally with `uvicorn --reload`
- runs the dashboard locally with `DASHBOARD_DEBUG=1`
- runs the worker locally
- accepts an optional `show_logs` argument (`true` or `false`)

Logging behavior:

- `./scripts/start-local-dev.sh` (default) writes logs to separate files:
  - `logs/api.log`
  - `logs/dashboard.log`
  - `logs/worker.log`
- `./scripts/start-local-dev.sh true` streams all three services into the same terminal with `[api]`, `[dashboard]`, and `[worker]` line prefixes and writes the same output to `logs/*.log`.

If you only want to restart the dashboard during UI work:

```bash
./scripts/restart-dashboard.sh
```

If you want to run the services manually, start PostgreSQL first:

```bash
docker compose up -d db
```

Then run the API:

```bash
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_sentiment \
PYTHONPATH=src \
python -m uvicorn reddit_sentiment.api.main:app --host 0.0.0.0 --port 8000 --reload
```

Run the dashboard in a second terminal:

```bash
API_BASE_URL=http://localhost:8000 \
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_sentiment \
PYTHONPATH=src \
DASHBOARD_DEBUG=1 \
python -m reddit_sentiment.dashboard_runner
```

Run the worker in a third terminal:

```bash
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_sentiment \
PYTHONPATH=src \
python -m reddit_sentiment.worker
```

## Local Dev Workflow

For faster UI iteration, keep only PostgreSQL in Docker and run the rest of the app locally. Prefer the two helper scripts above instead of launching each process manually.

## How To Use The App

1. Open the dashboard at `http://localhost:8050`
2. Enter a search term
3. Review or edit the subreddit list in the dashboard
4. Submit the query
5. Wait for the run to complete
6. Inspect overview metrics, sentiment over time, rolling sentiment trend, volume over time, sentiment heatmap, subreddit breakdown, phrase drivers, spike analysis, and matched documents

You can also call the API directly:

Create a query:

```bash
curl -X POST http://localhost:8000/queries \
  -H "Content-Type: application/json" \
  -d '{"term":"Big Mac","subreddits":["hungary","askhungary","budapest"],"content_language":"hu"}'
```

Health check:

```bash
curl http://localhost:8000/health
```

## Data Collection

The project uses Arctic Shift as the primary Reddit data source.

The collector:

- queries posts per configured subreddit
- fetches comments for returned posts
- normalizes those results into the app's internal post/comment format

Reddit API app credentials are not required for the current ingestion path.

## Testing

Run the test suite locally:

```bash
env -u DATABASE_URL python -m pytest
```

Current tests cover:

- Arctic Shift response normalization
- search normalization and matching
- mock sentiment classification
- sentiment evaluation helpers
- dashboard callback behavior

GitHub Actions CI runs:

- `ruff check .`
- `pytest`

## Troubleshooting

- If local Python commands pick up the wrong database connection, unset inherited `DATABASE_URL` for that command or set it explicitly to `postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_sentiment`.
