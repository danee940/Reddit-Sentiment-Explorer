from __future__ import annotations

import re
import unicodedata
from typing import ClassVar

from reddit_sentiment.core.enums import SentimentLabel
from reddit_sentiment.core.languages import normalize_content_language
from reddit_sentiment.sentiment.providers.base import MOCK_PROVIDER_VERSION, SentimentPrediction

_TOKEN_RE = re.compile(r"[\w']+", re.UNICODE)


def _fold_for_match(text: str) -> str:
    lowered = text.lower()
    normalized = unicodedata.normalize("NFD", lowered)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


class MockSentimentProvider:
    TOKEN_MAP: ClassVar[dict[str, dict[str, tuple[str, ...]]]] = {
        "en": {
            "negative": (
                "awful",
                "bad",
                "disappointing",
                "expensive",
                "hate",
                "horrible",
                "poor",
                "terrible",
                "worst",
            ),
            "positive": (
                "amazing",
                "brilliant",
                "excellent",
                "fantastic",
                "good",
                "great",
                "love",
                "perfect",
            ),
        },
        "hu": {
            "negative": (
                "borzasztó",
                "csalódás",
                "drága",
                "gyűlöl",
                "kétségbeejtő",
                "rossz",
                "szörnyű",
                "utál",
            ),
            "positive": (
                "csodálatos",
                "jó",
                "kiváló",
                "nagyszerű",
                "remek",
                "szeretem",
                "tökéletes",
                "fantasztikus",
            ),
        },
        "ro": {
            "negative": (
                "dezamagitor",
                "groaznic",
                "horibil",
                "oribil",
                "rau",
                "scump",
                "urasc",
                "prost",
            ),
            "positive": (
                "bun",
                "excelent",
                "extraordinar",
                "fantastic",
                "iubesc",
                "minunat",
                "perfect",
                "super",
            ),
        },
    }
    RATIONALES = {
        "en": {
            SentimentLabel.very_positive: (
                "The mock heuristic classified the text as strongly positive."
            ),
            SentimentLabel.positive: "The mock heuristic detected positive wording.",
            SentimentLabel.very_negative: (
                "The mock heuristic classified the text as strongly negative."
            ),
            SentimentLabel.negative: "The mock heuristic detected negative wording.",
            SentimentLabel.neutral: "The mock heuristic found no strong signal.",
        },
        "hu": {
            SentimentLabel.very_positive: (
                "A mock heurisztika kifejezetten pozitívnak minősítette a szöveget."
            ),
            SentimentLabel.positive: "A mock heurisztika pozitív megfogalmazást érzékelt.",
            SentimentLabel.very_negative: (
                "A mock heurisztika kifejezetten negatívnak minősítette a szöveget."
            ),
            SentimentLabel.negative: "A mock heurisztika negatív megfogalmazást érzékelt.",
            SentimentLabel.neutral: "A mock heurisztika nem talált erős érzelmi jelzést.",
        },
        "ro": {
            SentimentLabel.very_positive: (
                "Euristica mock a clasificat textul ca fiind puternic pozitiv."
            ),
            SentimentLabel.positive: "Euristica mock a detectat formulare pozitiva.",
            SentimentLabel.very_negative: (
                "Euristica mock a clasificat textul ca fiind puternic negativ."
            ),
            SentimentLabel.negative: "Euristica mock a detectat formulare negativa.",
            SentimentLabel.neutral: "Euristica mock nu a gasit un semnal emotional puternic.",
        },
    }

    def _lexicon_for_language(self, language_code: str) -> tuple[frozenset[str], frozenset[str]]:
        token_set = self.TOKEN_MAP.get(language_code, self.TOKEN_MAP["en"])
        positive = frozenset(_fold_for_match(t) for t in token_set["positive"])
        negative = frozenset(_fold_for_match(t) for t in token_set["negative"])
        return positive, negative

    def _scan_tokens(
        self,
        text: str,
        positive_lex: frozenset[str],
        negative_lex: frozenset[str],
    ) -> tuple[int, int, list[str]]:
        positive_hits = 0
        negative_hits = 0
        evidence: list[str] = []
        seen_lower: set[str] = set()
        for match in _TOKEN_RE.finditer(text):
            surface = match.group()
            folded = _fold_for_match(surface)
            if folded in positive_lex:
                positive_hits += 1
                key = surface.lower()
                if key not in seen_lower and len(evidence) < 3:
                    evidence.append(surface)
                    seen_lower.add(key)
            elif folded in negative_lex:
                negative_hits += 1
                key = surface.lower()
                if key not in seen_lower and len(evidence) < 3:
                    evidence.append(surface)
                    seen_lower.add(key)
        return positive_hits, negative_hits, evidence

    def _label_from_net(
        self, net: int
    ) -> tuple[SentimentLabel, int, float]:
        if net >= 2:
            return SentimentLabel.very_positive, 2, 0.62
        if net == 1:
            return SentimentLabel.positive, 1, 0.55
        if net <= -2:
            return SentimentLabel.very_negative, -2, 0.62
        if net == -1:
            return SentimentLabel.negative, -1, 0.55
        return SentimentLabel.neutral, 0, 0.5

    async def classify(self, text: str, content_language: str) -> SentimentPrediction:
        language_code = normalize_content_language(content_language)
        rationale_map = self.RATIONALES.get(language_code, self.RATIONALES["en"])
        positive_lex, negative_lex = self._lexicon_for_language(language_code)
        positive_hits, negative_hits, evidence_phrases = self._scan_tokens(
            text, positive_lex, negative_lex
        )
        net = positive_hits - negative_hits
        label, score_value, confidence = self._label_from_net(net)
        return SentimentPrediction(
            label=label,
            score_value=score_value,
            confidence=confidence,
            rationale=rationale_map[label],
            evidence_phrases=evidence_phrases,
            provider_name="mock",
            provider_version=MOCK_PROVIDER_VERSION,
        )
