from __future__ import annotations

import asyncio
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import asyncpg  # type: ignore[import-untyped]

from reddit_sentiment.core.config import get_settings  # pyright: ignore[reportMissingImports]
from reddit_sentiment.sentiment.providers.mock import (  # pyright: ignore[reportMissingImports]
    MockSentimentProvider,
)
from reddit_sentiment.sentiment.providers.xlm_roberta import (  # pyright: ignore[reportMissingImports]
    XLMRobertaSentimentProvider,
)

ALL_LABELS = [
    "very_negative",
    "negative",
    "neutral",
    "positive",
    "very_positive",
]


def _asyncpg_dsn() -> str:
    url = get_settings().database_url
    return url.replace("postgresql+asyncpg://", "postgresql://", 1)


async def fetch_run_info(conn: asyncpg.Connection, run_id: str) -> dict[str, str]:
    row = await conn.fetchrow(
        """
        SELECT qr.id, q.raw_term, qr.language_filter, qr.status
        FROM query_runs qr
        JOIN queries q ON qr.query_id = q.id
        WHERE qr.id = $1
        """,
        run_id,
    )
    if row is None:
        print(f"Error: run '{run_id}' not found.", file=sys.stderr)
        sys.exit(1)
    return dict(row)


async def fetch_documents(conn: asyncpg.Connection, run_id: str) -> list[dict[str, str]]:
    rows = await conn.fetch(
        """
        SELECT d.id, d.full_text, sr.label AS llm_label, sr.provider_name
        FROM sentiment_results sr
        JOIN documents d ON sr.document_id = d.id
        WHERE sr.query_run_id = $1
        ORDER BY d.created_utc
        """,
        run_id,
    )
    if not rows:
        print(
            f"Error: no sentiment results for run '{run_id}'.",
            file=sys.stderr,
        )
        sys.exit(1)
    return [dict(row) for row in rows]


def print_distribution(label: str, counter: Counter[str], total: int) -> None:
    print(f"\n{label}:")
    for lbl in ALL_LABELS:
        count = counter.get(lbl, 0)
        pct = (count / total) * 100
        bar = "\u2588" * int(pct / 2)
        print(f"  {lbl:15s}: {count:4d}  ({pct:5.1f}%)  {bar}")


def print_confusion(
    name_a: str,
    name_b: str,
    confusion: Counter[tuple[str, str]],
) -> None:
    print(f"\nConfusion matrix (rows={name_a}, cols={name_b}):")
    header = f"{'':15s}" + "".join(f"{lbl:>15s}" for lbl in ALL_LABELS)
    print(header)
    for row_label in ALL_LABELS:
        row = f"{row_label:15s}"
        for col_label in ALL_LABELS:
            row += f"{confusion.get((row_label, col_label), 0):15d}"
        print(row)


def compute_agreement(
    llm_labels: list[str],
    other_labels: list[str],
) -> tuple[int, float, Counter[tuple[str, str]]]:
    agreements = 0
    confusion: Counter[tuple[str, str]] = Counter()
    for llm_l, other_l in zip(llm_labels, other_labels, strict=True):
        if llm_l == other_l:
            agreements += 1
        confusion[(llm_l, other_l)] += 1
    total = len(llm_labels)
    pct = (agreements / total) * 100 if total else 0.0
    return agreements, pct, confusion


async def run_comparison(run_id: str) -> None:
    conn = await asyncpg.connect(_asyncpg_dsn())
    try:
        run_info = await fetch_run_info(conn, run_id)
        docs = await fetch_documents(conn, run_id)
    finally:
        await conn.close()

    language = run_info["language_filter"] or "en"
    total = len(docs)
    llm_provider = docs[0]["provider_name"] if docs else "llm"

    mock_provider = MockSentimentProvider()
    xlm_provider = XLMRobertaSentimentProvider()

    llm_label_list: list[str] = []
    mock_label_list: list[str] = []
    xlm_label_list: list[str] = []

    llm_dist: Counter[str] = Counter()
    mock_dist: Counter[str] = Counter()
    xlm_dist: Counter[str] = Counter()

    print(f"\nClassifying {total} documents with XLM-RoBERTa (model loads on first call)...")

    for i, doc in enumerate(docs, 1):
        llm_label = doc["llm_label"]
        llm_label_list.append(llm_label)
        llm_dist[llm_label] += 1

        mock_pred = await mock_provider.classify(doc["full_text"], language)
        mock_label = mock_pred.label.value
        mock_label_list.append(mock_label)
        mock_dist[mock_label] += 1

        xlm_pred = await xlm_provider.classify(doc["full_text"], language)
        xlm_label = xlm_pred.label.value
        xlm_label_list.append(xlm_label)
        xlm_dist[xlm_label] += 1

        if i % 25 == 0 or i == total:
            print(f"  {i}/{total} classified")

    mock_agree, mock_agree_pct, mock_confusion = compute_agreement(llm_label_list, mock_label_list)
    xlm_agree, xlm_agree_pct, xlm_confusion = compute_agreement(llm_label_list, xlm_label_list)
    mock_xlm_agree, mock_xlm_agree_pct, mock_xlm_confusion = compute_agreement(
        mock_label_list, xlm_label_list
    )

    print(f"\n{'=' * 65}")
    print(f'Three-way provider comparison — query: "{run_info["raw_term"]}"')
    print(f"Run: {run_id}")
    print(f"Language: {language}  |  Documents: {total}")
    print(f"{'=' * 65}")

    print_distribution(f"{llm_provider} (LLM)", llm_dist, total)
    print_distribution("Mock (heuristic)", mock_dist, total)
    print_distribution("XLM-RoBERTa", xlm_dist, total)

    print("\n--- Agreement rates ---")
    print(f"  {llm_provider} vs Mock       : {mock_agree}/{total} = {mock_agree_pct:.1f}%")
    print(f"  {llm_provider} vs XLM-RoBERTa: {xlm_agree}/{total} = {xlm_agree_pct:.1f}%")
    print(f"  Mock vs XLM-RoBERTa    : {mock_xlm_agree}/{total} = {mock_xlm_agree_pct:.1f}%")

    print_confusion(llm_provider, "Mock", mock_confusion)
    print_confusion(llm_provider, "XLM-RoBERTa", xlm_confusion)
    print_confusion("Mock", "XLM-RoBERTa", mock_xlm_confusion)

    results = {
        "run_id": run_id,
        "query_term": run_info["raw_term"],
        "language": language,
        "llm_provider": llm_provider,
        "total": total,
        "distributions": {
            llm_provider: dict(llm_dist),
            "mock": dict(mock_dist),
            "xlm_roberta": dict(xlm_dist),
        },
        "agreement": {
            f"{llm_provider}_vs_mock": {
                "count": mock_agree,
                "pct": round(mock_agree_pct, 1),
            },
            f"{llm_provider}_vs_xlm_roberta": {
                "count": xlm_agree,
                "pct": round(xlm_agree_pct, 1),
            },
            "mock_vs_xlm_roberta": {
                "count": mock_xlm_agree,
                "pct": round(mock_xlm_agree_pct, 1),
            },
        },
    }
    out_path = Path(__file__).resolve().parent / "all_providers_comparison.json"
    out_path.write_text(json.dumps(results, indent=2))
    print(f"\nResults written to {out_path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(
            f"Usage: python {Path(__file__).name} <query_run_id>",
            file=sys.stderr,
        )
        sys.exit(1)
    asyncio.run(run_comparison(sys.argv[1]))
