from langdetect import DetectorFactory, detect_langs

from reddit_sentiment.core.languages import normalize_content_language, normalize_detected_language

DetectorFactory.seed = 0


class LanguageService:
    def detect(self, text: str) -> tuple[str | None, float | None]:
        candidate = text.strip()
        if not candidate:
            return None, None
        try:
            results = detect_langs(candidate)
        except Exception:
            return None, None
        if not results:
            return None, None
        best = results[0]
        return best.lang, float(best.prob)

    def matches_language(
        self,
        text: str,
        target_language: str,
        threshold: float = 0.7,
    ) -> tuple[bool, str | None, float | None]:
        lang, confidence = self.detect(text)
        normalized_target = normalize_content_language(target_language)
        normalized_detected = normalize_detected_language(lang)
        return (
            normalized_detected == normalized_target and (confidence or 0.0) >= threshold,
            normalized_detected,
            confidence,
        )
