from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from reddit_sentiment.core.enums import AggregateType
from reddit_sentiment.core.stop_words import get_stop_words_for_language
from reddit_sentiment.db.models import (
    Aggregate,
    Document,
    Query,
    QueryDocumentMatch,
    QueryRun,
    SentimentResult,
    Subreddit,
)

TOKEN_PATTERN = re.compile(r"\b[\w-]{4,}\b", re.UNICODE)
_EMPTY_CHART_PAYLOAD: dict[str, object] = {
    "overview": {},
    "sentiment_distribution": [],
    "sentiment_timeline": [],
    "volume_timeline": [],
    "subreddit_breakdown": [],
    "sentiment_heatmap": [],
    "rolling_sentiment_timeline": [],
    "phrase_breakdown": [],
    "spike_events": [],
}
PHRASE_TOKEN_PATTERN = re.compile(r"\b[\w-]+\b", re.UNICODE)
SENTIMENT_DISPLAY_ORDER = (
    "very_positive",
    "positive",
    "neutral",
    "negative",
    "very_negative",
)


class AggregationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def build(self, query_run_id: str) -> dict:
        excluded_terms, stop_words = await self._get_query_context(query_run_id)
        stmt = (
            select(QueryDocumentMatch, Document, SentimentResult, Subreddit)
            .join(Document, QueryDocumentMatch.document_id == Document.id)
            .join(SentimentResult, SentimentResult.document_id == Document.id)
            .join(Subreddit, Subreddit.id == Document.subreddit_id)
            .where(QueryDocumentMatch.query_run_id == query_run_id)
            .where(SentimentResult.query_run_id == query_run_id)
        )
        rows = (await self.session.execute(stmt)).all()

        distribution: Counter[str] = Counter()
        daily_sentiment: defaultdict[str, list[int]] = defaultdict(list)
        daily_volume: Counter[str] = Counter()
        subreddit_distribution: defaultdict[str, Counter[str]] = defaultdict(Counter)
        heatmap_scores: defaultdict[tuple[str, str], list[int]] = defaultdict(list)
        phrase_breakdown: defaultdict[str, Counter[str]] = defaultdict(Counter)
        low_confidence_documents = 0

        for _, document, sentiment, subreddit in rows:
            distribution[sentiment.label.value] += 1
            day_key = date.fromtimestamp(document.created_utc.timestamp()).isoformat()
            daily_sentiment[day_key].append(sentiment.score_value)
            daily_volume[day_key] += 1
            subreddit_distribution[subreddit.name][sentiment.label.value] += 1
            heatmap_scores[(day_key, subreddit.name)].append(sentiment.score_value)
            if sentiment.confidence is not None and sentiment.confidence < 0.6:
                low_confidence_documents += 1
            evidence_terms = self._extract_evidence_terms(
                sentiment.evidence_phrases,
                excluded_terms,
                stop_words,
            )
            if not evidence_terms:
                evidence_terms = self._extract_keywords(
                    document.full_text,
                    excluded_terms,
                    stop_words,
                )
            for term in evidence_terms:
                phrase_breakdown[sentiment.label.value][term] += 1

        total_documents = len(rows)
        average_score = 0.0
        if rows:
            average_score = (
                sum(sentiment.score_value for _, _, sentiment, _ in rows)
                / total_documents
            )

        payload = {
            "overview": {
                "total_documents": total_documents,
                "average_score": average_score,
                "low_confidence_documents": low_confidence_documents,
                "high_confidence_documents": max(total_documents - low_confidence_documents, 0),
            },
            "sentiment_distribution": [
                {"label": label, "count": count}
                for label, count in sorted(distribution.items())
            ],
            "sentiment_timeline": [
                {"date": day, "average_score": sum(scores) / len(scores)}
                for day, scores in sorted(daily_sentiment.items())
            ],
            "volume_timeline": [
                {"date": day, "count": count}
                for day, count in sorted(daily_volume.items())
            ],
            "subreddit_breakdown": [
                {"subreddit": subreddit, "distribution": dict(counts)}
                for subreddit, counts in sorted(subreddit_distribution.items())
            ],
            "sentiment_heatmap": [
                {
                    "date": day,
                    "subreddit": subreddit,
                    "average_score": sum(scores) / len(scores),
                    "count": len(scores),
                }
                for (day, subreddit), scores in sorted(heatmap_scores.items())
            ],
            "rolling_sentiment_timeline": self._build_rolling_timeline(daily_sentiment),
            "phrase_breakdown": self._build_phrase_breakdown(phrase_breakdown),
            "spike_events": self._build_spike_events(daily_sentiment, daily_volume),
        }
        await self._replace_aggregates(query_run_id, payload)
        return payload

    async def get_payload(self, query_run_id: str) -> dict:
        stmt = select(Aggregate).where(Aggregate.query_run_id == query_run_id)
        aggregates = (await self.session.scalars(stmt)).all()
        stored = {agg.aggregate_type.value: agg.payload for agg in aggregates}
        return {key: stored.get(key, default) for key, default in _EMPTY_CHART_PAYLOAD.items()}

    async def _replace_aggregates(self, query_run_id: str, payload: dict) -> None:
        await self.session.execute(delete(Aggregate).where(Aggregate.query_run_id == query_run_id))
        for aggregate_type in AggregateType:
            aggregate = Aggregate(
                query_run_id=query_run_id,
                aggregate_type=aggregate_type,
                payload=payload.get(aggregate_type.value, {}),
            )
            self.session.add(aggregate)
        await self.session.flush()

    def _build_rolling_timeline(self, daily_sentiment: dict[str, list[int]]) -> list[dict]:
        items: list[dict] = []
        rolling_window: list[float] = []
        for day, scores in sorted(daily_sentiment.items()):
            rolling_window.append(sum(scores) / len(scores))
            if len(rolling_window) > 3:
                rolling_window.pop(0)
            items.append(
                {
                    "date": day,
                    "average_score": sum(rolling_window) / len(rolling_window),
                }
            )
        return items

    def _build_phrase_breakdown(self, phrase_breakdown: dict[str, Counter]) -> list[dict]:
        items = []
        ordered_labels = [
            label for label in SENTIMENT_DISPLAY_ORDER if label in phrase_breakdown
        ]
        ordered_labels.extend(
            sorted(label for label in phrase_breakdown if label not in SENTIMENT_DISPLAY_ORDER)
        )
        for label in ordered_labels:
            counts = phrase_breakdown[label]
            top_terms = [{"term": term, "count": count} for term, count in counts.most_common(5)]
            if top_terms:
                items.append({"label": label, "terms": top_terms})
        return items

    def _build_spike_events(
        self,
        daily_sentiment: dict[str, list[int]],
        daily_volume: Counter,
    ) -> list[dict]:
        items: list[dict] = []
        previous_average = None
        average_volume = sum(daily_volume.values()) / len(daily_volume) if daily_volume else 0.0
        for day, scores in sorted(daily_sentiment.items()):
            average_score = sum(scores) / len(scores)
            score_change = average_score - previous_average if previous_average is not None else 0.0
            count = daily_volume.get(day, 0)
            if count >= max(average_volume + 1, 2) or abs(score_change) >= 0.75:
                items.append(
                    {
                        "date": day,
                        "count": count,
                        "average_score": average_score,
                        "score_change": score_change,
                    }
                )
            previous_average = average_score
        return items[:5]

    async def _get_query_context(self, query_run_id: str) -> tuple[set[str], set[str]]:
        row = (
            await self.session.execute(
                select(Query.raw_term, QueryRun.language_filter)
                .join(QueryRun, QueryRun.query_id == Query.id)
                .where(QueryRun.id == query_run_id)
            )
        ).one_or_none()
        query_text = row[0] if row else None
        stop_words = get_stop_words_for_language(row[1] if row else None)
        return {
            token
            for token in self._tokenize((query_text or "").casefold())
            if token not in stop_words
        }, stop_words

    def _extract_keywords(
        self,
        text: str,
        excluded_terms: set[str],
        stop_words: set[str],
    ) -> list[str]:
        tokens = [
            token
            for token in self._tokenize((text or "").casefold())
            if token not in stop_words and token not in excluded_terms
        ]
        if not tokens:
            return []

        phrase_counts = Counter(
            f"{left} {right}"
            for left, right in zip(tokens, tokens[1:], strict=False)
            if left != right
        )
        keyword_counts = Counter(tokens)
        ranked_terms: list[str] = []

        for term, _ in phrase_counts.most_common(4):
            ranked_terms.append(term)
        for term, _ in keyword_counts.most_common(8):
            if term not in ranked_terms:
                ranked_terms.append(term)
            if len(ranked_terms) == 8:
                break
        return ranked_terms

    def _extract_evidence_terms(
        self,
        phrases: list[str],
        excluded_terms: set[str],
        stop_words: set[str],
    ) -> list[str]:
        normalized_phrases: list[str] = []
        for phrase in phrases:
            tokens = [
                token
                for token in self._tokenize_phrase(phrase.casefold())
                if token not in excluded_terms and token not in stop_words
            ]
            if not tokens:
                continue
            normalized_phrase = " ".join(tokens[:4])
            if normalized_phrase and normalized_phrase not in normalized_phrases:
                normalized_phrases.append(normalized_phrase)
            if len(normalized_phrases) == 5:
                break
        return normalized_phrases

    def _tokenize(self, text: str) -> list[str]:
        return [token.strip("-_") for token in TOKEN_PATTERN.findall(text) if token.strip("-_")]

    def _tokenize_phrase(self, text: str) -> list[str]:
        return [
            token.strip("-_")
            for token in PHRASE_TOKEN_PATTERN.findall(text)
            if token.strip("-_")
        ]
