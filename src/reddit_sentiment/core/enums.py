from enum import StrEnum


class QueryRunStatus(StrEnum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class DocumentSourceType(StrEnum):
    post = "post"
    comment = "comment"


class SentimentLabel(StrEnum):
    very_negative = "very_negative"
    negative = "negative"
    neutral = "neutral"
    positive = "positive"
    very_positive = "very_positive"


class MatchType(StrEnum):
    title_phrase = "title_phrase"
    body_phrase = "body_phrase"
    comment_phrase = "comment_phrase"
    title_tokens = "title_tokens"
    body_tokens = "body_tokens"
    comment_tokens = "comment_tokens"


class AggregateType(StrEnum):
    overview = "overview"
    sentiment_distribution = "sentiment_distribution"
    sentiment_timeline = "sentiment_timeline"
    volume_timeline = "volume_timeline"
    subreddit_breakdown = "subreddit_breakdown"
    sentiment_heatmap = "sentiment_heatmap"
    rolling_sentiment_timeline = "rolling_sentiment_timeline"
    phrase_breakdown = "phrase_breakdown"
    spike_events = "spike_events"


class ProviderName(StrEnum):
    openai = "openai"
    mock = "mock"
    xlm_roberta = "xlm_roberta"
