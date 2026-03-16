from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from reddit_sentiment.core.enums import QueryRunStatus, SentimentLabel
from reddit_sentiment.core.languages import DEFAULT_CONTENT_LANGUAGE, normalize_content_language


class QueryCreateRequest(BaseModel):
    term: str = Field(min_length=1, max_length=255)
    subreddits: list[str] | None = None
    content_language: str = Field(default=DEFAULT_CONTENT_LANGUAGE, min_length=2, max_length=20)

    @field_validator("content_language", mode="before")
    @classmethod
    def normalize_selected_language(cls, value: str | None) -> str:
        return normalize_content_language(value)


class QueryResponse(BaseModel):
    query_id: str
    query_run_id: str
    status: QueryRunStatus
    is_cached: bool


class QueryRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    query_id: str
    status: QueryRunStatus
    started_at: datetime
    finished_at: datetime | None
    data_fresh_until: datetime | None
    error_message: str | None
    language_filter: str


class ChartPayload(BaseModel):
    overview: dict
    sentiment_distribution: list[dict]
    sentiment_timeline: list[dict]
    volume_timeline: list[dict]
    subreddit_breakdown: list[dict]
    sentiment_heatmap: list[dict] = Field(default_factory=list)
    rolling_sentiment_timeline: list[dict] = Field(default_factory=list)
    phrase_breakdown: list[dict] = Field(default_factory=list)
    spike_events: list[dict] = Field(default_factory=list)


class DocumentResponse(BaseModel):
    document_id: str
    source_type: str
    subreddit: str
    created_utc: datetime
    score: int
    snippet: str
    content: str
    sentiment_label: SentimentLabel | None
    sentiment_score: int | None
    sentiment_confidence: float | None = None
    sentiment_rationale: str | None = None
    sentiment_evidence_phrases: list[str] = Field(default_factory=list)
    permalink: str | None = None


class DocumentsResponse(BaseModel):
    items: list[DocumentResponse]


class SubredditValidationRequest(BaseModel):
    subreddits: list[str] = Field(default_factory=list)


class SubredditValidationItem(BaseModel):
    name: str
    exists: bool | None


class SubredditValidationResponse(BaseModel):
    items: list[SubredditValidationItem]
