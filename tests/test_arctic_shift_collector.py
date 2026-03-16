from reddit_sentiment.collectors.arctic_shift.client import ArcticShiftCollector


def test_extract_items_supports_data_list_payload() -> None:
    payload = {"data": [{"id": "abc"}, {"id": "def"}]}
    items = ArcticShiftCollector._extract_items(payload)
    assert items == [{"id": "abc"}, {"id": "def"}]


def test_normalize_post_maps_expected_fields() -> None:
    post = ArcticShiftCollector._normalize_post(
        {
            "id": "post123",
            "subreddit": "hungary",
            "title": "Big Mac megint dragabb lett",
            "selftext": "Szerintem mar nem eri meg.",
            "author": "user_1",
            "score": 12,
            "created_utc": 1710000000,
            "permalink": "/r/hungary/comments/post123/example/",
        }
    )
    assert post is not None
    assert post.reddit_post_id == "post123"
    assert post.subreddit == "hungary"
    assert post.author_name == "user_1"
    assert post.permalink == "https://reddit.com/r/hungary/comments/post123/example/"


def test_normalize_comment_uses_parent_post_id() -> None:
    comment = ArcticShiftCollector._normalize_comment(
        {
            "id": "comment123",
            "subreddit": "hungary",
            "body": "A Big Mac szerintem mar nem jo.",
            "author": "user_2",
            "score": 4,
            "created_utc": "1710000123",
            "permalink": "/r/hungary/comments/post123/example/comment123/",
        },
        post_id="post123",
        subreddit="hungary",
    )
    assert comment is not None
    assert comment.reddit_post_id == "post123"
    assert comment.reddit_comment_id == "comment123"
    assert comment.subreddit == "hungary"


def test_normalize_permalink_builds_fallback_permalink() -> None:
    permalink = ArcticShiftCollector._normalize_permalink(None, "post999", "askhungary")
    assert permalink == "https://reddit.com/r/askhungary/comments/post999"
