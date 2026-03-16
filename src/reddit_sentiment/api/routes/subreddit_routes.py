from fastapi import APIRouter

from reddit_sentiment.api.dependencies import SubredditServiceDep
from reddit_sentiment.api.schemas.query import (
    SubredditValidationItem,
    SubredditValidationRequest,
    SubredditValidationResponse,
)

router = APIRouter()


@router.post("/subreddits/validate", response_model=SubredditValidationResponse)
async def validate_subreddits(
    request: SubredditValidationRequest,
    service: SubredditServiceDep,
) -> SubredditValidationResponse:
    items = await service.validate_subreddits(request.subreddits)
    return SubredditValidationResponse(
        items=[SubredditValidationItem.model_validate(item) for item in items]
    )
