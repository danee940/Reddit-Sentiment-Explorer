import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from reddit_sentiment.api.routes.query_routes import router as query_router
from reddit_sentiment.api.routes.subreddit_routes import router as subreddit_router
from reddit_sentiment.core.logging import configure_logging
from reddit_sentiment.db.init import initialize_database

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Application startup")
    await initialize_database()
    logger.info("Application ready")
    yield
    logger.info("Application shutdown")


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="Reddit Sentiment API", lifespan=lifespan)
    app.include_router(query_router)
    app.include_router(subreddit_router)
    return app


app = create_app()
