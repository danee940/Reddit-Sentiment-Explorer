# Roadmap

Planned work for Reddit Sentiment Explorer, grouped by theme.

Status: `[ ]` planned · `[~]` in progress · `[x]` done

## 2. Batching and parallelism

Today a worker processes one run at a time, and each run goes through its stages strictly in order: collect everything, then match, then classify every document with one provider call each, then aggregate. The goal is to process several runs at once, overlap the stages, and make fewer, larger calls.

- [ ] **Concurrent runs per worker.** Add a `WORKER_CONCURRENCY` setting and let the worker process up to N claimed runs at the same time, each with its own database session. On shutdown, stop claiming new runs and wait for in-flight runs to finish.
- [ ] **Horizontal worker scaling.** Run claiming already uses `SKIP LOCKED`; verify that several worker replicas never process the same run, add an integration test for it, and document scaling the worker on Docker Compose and Railway.
- [ ] **Batch classification interface.** Add `classify_batch(texts, content_language)` to the `SentimentProvider` protocol, with a default that falls back to per-document calls. `SentimentService` groups pending documents into batches of `SENTIMENT_BATCH_SIZE`.
- [ ] **Multi-document OpenAI requests.** Classify several documents per request with a structured JSON array response keyed by document ID. If a batch response is malformed or incomplete, retry only the missing documents individually. Fewer requests means lower latency and cost.
- [ ] **Batched XLM-RoBERTa inference.** Pass a whole batch to the Transformers pipeline in one call instead of starting one thread per document.
- [ ] **Streaming pipeline.** Turn the stages into producer/consumer steps connected by bounded `asyncio.Queue`s, so matching and classification start as soon as the first subreddit's posts arrive. Bounded queues provide backpressure when classification is slower than collection.
- [ ] **Fetch comments per subreddit, not after all posts.** The collector currently waits for posts from every subreddit before requesting any comments. Start comment requests for each subreddit as soon as its posts arrive.
- [ ] **Chunked persistence and resumable runs.** Persist and commit documents and sentiment results in chunks, so a crashed or requeued run resumes from where it stopped instead of starting over.
- [ ] **Shared rate limiter for Arctic Shift.** With several runs in parallel, per-run semaphores multiply the load on the upstream API. Add a process-wide token bucket that respects `429` responses and `Retry-After`.
- [ ] **Parallel comparison runs.** Term comparison (see below) fans out one run per term and processes them concurrently.
- [ ] **Connection pool sizing.** Derive database pool size from worker concurrency, and document the settings that interact (`WORKER_CONCURRENCY`, `ARCTIC_SHIFT_CONCURRENCY`, `SENTIMENT_CONCURRENCY`, `SENTIMENT_BATCH_SIZE`).
- [ ] **Load test.** A script that queues many runs against the mock provider and reports throughput and stage timings, to measure the effect of each change above.

## 3. Query features

- [ ] **Date range filter.** Let users limit a query to a time window. Covers the request schema, cache key, Arctic Shift `after`/`before` parameters, a date picker in the dashboard, and tests.
- [ ] **Term comparison.** Compare 2–4 terms side by side: overlaid sentiment and volume timelines, a per-term distribution, and a subreddit breakdown. Needs a comparison endpoint that runs or reuses one query per term, plus a new dashboard tab.
- [ ] **Search operators.** Support quoted phrases, `OR`, and exclusions (`tesla -stock`) in `SearchService`, with parsing tests and a syntax hint in the UI.
- [ ] **Watchlist with scheduled refresh.** Save queries and have the worker refresh them on a schedule, keeping each run so the dashboard can show how sentiment for a term shifts week over week.

## 4. Dashboard and UX

- [ ] **Live run progress.** Record pipeline stage and counts on `query_runs` (collected N posts, classified M of N documents) and show a progress bar instead of a generic "running" status.
- [ ] **Export.** Download matched documents and chart aggregates as CSV or JSON, via new API endpoints and dashboard buttons.
- [ ] **Matched content filtering and pagination.** Filter by sentiment label, subreddit, and source type; sort by date or score; paginate on the server.
- [ ] **Shareable URLs.** Encode term, subreddits, language, and active tab in the URL so a result view can be bookmarked or shared.
- [ ] **Accessibility pass.** Colorblind-safe sentiment palette, keyboard navigation for tabs and the subreddit picker, ARIA labels, and contrast checks in both themes.

## 5. Platform and operations

- [ ] **Event-driven worker.** Replace the fixed polling interval with Postgres `LISTEN/NOTIFY`, so new runs start immediately; keep polling as a fallback.
- [ ] **Rate limiting on the public API.** Per-client limits on `POST /queries` and `/refresh` to protect the Railway deployment and the Arctic Shift API.
- [ ] **Cost guardrails for the OpenAI provider.** Configurable per-run document cap and a daily token budget; runs over budget fail with a clear message instead of silently spending.
- [ ] **Observability.** Structured JSON logs with request and run IDs, and a `/metrics` endpoint (run durations, queue depth, provider errors).
- [ ] **Run cancellation.** `POST /query-runs/{id}/cancel`, honored by the pipeline between stages, with a cancel button in the dashboard.

## 6. Code quality and testing

- [ ] **Typed chart payloads.** Replace the `list[dict]` fields in `ChartPayload` with Pydantic models shared by the API and dashboard, and remove the defensive dict access in the chart code.
- [ ] **Split large dashboard modules.** Break up `components/layout.py` and `callbacks/results.py` into per-tab modules.
- [ ] **Consolidate test files.** Merge the `*_extra` / `*_extra2` test modules into one module per unit, with shared fixtures in `conftest.py`.
- [ ] **Dashboard end-to-end tests.** Browser tests for the search flow, tab switching, and theme/language toggles, run in CI against the mock provider.
- [ ] **Dependency automation.** Dependabot or Renovate for `uv.lock` and GitHub Actions, plus pre-commit hooks for ruff and mypy.

## 7. Documentation and release

- [ ] **Architecture docs.** A `docs/architecture.md` with a service diagram, the run lifecycle (pending → running → completed/failed), the caching and reuse rules, and the concurrency model.
- [ ] **CONTRIBUTING.md.** Local setup, test commands, commit conventions, and how to add a migration.
- [ ] **README screenshots and demo.** Dashboard screenshots or a short GIF, and a link to the live demo running the mock provider.
- [ ] **v1.0.0 release.** Tag the release, write a changelog, and publish GitHub release notes.

## Later

Ideas not yet scheduled:

- More UI languages beyond English and Hungarian.
- Topic clustering of matched documents to show *why* sentiment moved, not just when.
- Email or webhook alerts when a watched term's sentiment shifts sharply.
