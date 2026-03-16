from __future__ import annotations

import re
import unicodedata

from reddit_sentiment.core.enums import MatchType


def simplify_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.lower())
    without_accents = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", without_accents).strip()


class SearchService:
    def __init__(self, term: str) -> None:
        self.raw_term = term
        self.normalized_term = simplify_text(term)
        self.term_tokens = [token for token in self.normalized_term.split(" ") if token]

    def match_text(
        self,
        text: str,
        source_type: str,
    ) -> tuple[bool, MatchType | None, list[str], float]:
        normalized_text = simplify_text(text)
        if not normalized_text:
            return False, None, [], 0.0
        normalized_words = set(re.findall(r"\w+", normalized_text))

        if self.normalized_term in normalized_text:
            match_type = {
                "title": MatchType.title_phrase,
                "body": MatchType.body_phrase,
                "comment": MatchType.comment_phrase,
            }[source_type]
            return True, match_type, [self.raw_term], 1.0

        if len(self.term_tokens) > 1 and all(
            token in normalized_words for token in self.term_tokens
        ):
            match_type = {
                "title": MatchType.title_tokens,
                "body": MatchType.body_tokens,
                "comment": MatchType.comment_tokens,
            }[source_type]
            return True, match_type, self.term_tokens, 0.8

        return False, None, [], 0.0
