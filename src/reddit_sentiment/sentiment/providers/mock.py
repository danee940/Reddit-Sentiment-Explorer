from __future__ import annotations

from reddit_sentiment.core.enums import SentimentLabel
from reddit_sentiment.core.languages import normalize_content_language
from reddit_sentiment.sentiment.providers.base import MOCK_PROVIDER_VERSION, SentimentPrediction


class MockSentimentProvider:
    TOKEN_MAP = {
        "en": {
            "negative": ("bad", "awful", "hate", "terrible", "expensive"),
            "positive": ("good", "love", "great", "excellent", "amazing"),
        },
        "hu": {
            "negative": ("rossz", "drága", "gyűlöl", "utál", "szörnyű"),
            "positive": ("jó", "szeretem", "finom", "kiváló", "remek"),
        },
        "ru": {
            "negative": ("плохо", "ужасно", "ненавижу", "дорого", "отстой"),
            "positive": ("хорошо", "люблю", "отлично", "прекрасно", "супер"),
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
        "ru": {
            SentimentLabel.very_positive: (
                "Тестовая эвристика определила текст как явно позитивный."
            ),
            SentimentLabel.positive: "Тестовая эвристика обнаружила позитивную формулировку.",
            SentimentLabel.very_negative: (
                "Тестовая эвристика определила текст как явно негативный."
            ),
            SentimentLabel.negative: "Тестовая эвристика обнаружила негативную формулировку.",
            SentimentLabel.neutral: "Тестовая эвристика не нашла сильного эмоционального сигнала.",
        },
    }

    async def classify(self, text: str, content_language: str) -> SentimentPrediction:
        normalized = text.lower()
        language_code = normalize_content_language(content_language)
        token_set = self.TOKEN_MAP.get(language_code, self.TOKEN_MAP["en"])
        rationale_map = self.RATIONALES.get(language_code, self.RATIONALES["en"])
        negative_tokens = token_set["negative"]
        positive_tokens = token_set["positive"]
        evidence_phrases = [
            token
            for token in positive_tokens + negative_tokens
            if token in normalized
        ][:3]

        negative_hits = sum(token in normalized for token in negative_tokens)
        positive_hits = sum(token in normalized for token in positive_tokens)

        if positive_hits >= 2:
            return SentimentPrediction(
                label=SentimentLabel.very_positive,
                score_value=2,
                confidence=0.6,
                rationale=rationale_map[SentimentLabel.very_positive],
                evidence_phrases=evidence_phrases,
                provider_name="mock",
                provider_version=MOCK_PROVIDER_VERSION,
            )
        if positive_hits == 1:
            return SentimentPrediction(
                label=SentimentLabel.positive,
                score_value=1,
                confidence=0.55,
                rationale=rationale_map[SentimentLabel.positive],
                evidence_phrases=evidence_phrases,
                provider_name="mock",
                provider_version=MOCK_PROVIDER_VERSION,
            )
        if negative_hits >= 2:
            return SentimentPrediction(
                label=SentimentLabel.very_negative,
                score_value=-2,
                confidence=0.6,
                rationale=rationale_map[SentimentLabel.very_negative],
                evidence_phrases=evidence_phrases,
                provider_name="mock",
                provider_version=MOCK_PROVIDER_VERSION,
            )
        if negative_hits == 1:
            return SentimentPrediction(
                label=SentimentLabel.negative,
                score_value=-1,
                confidence=0.55,
                rationale=rationale_map[SentimentLabel.negative],
                evidence_phrases=evidence_phrases,
                provider_name="mock",
                provider_version=MOCK_PROVIDER_VERSION,
            )
        return SentimentPrediction(
            label=SentimentLabel.neutral,
            score_value=0,
            confidence=0.5,
            rationale=rationale_map[SentimentLabel.neutral],
            evidence_phrases=evidence_phrases,
            provider_name="mock",
            provider_version=MOCK_PROVIDER_VERSION,
        )
