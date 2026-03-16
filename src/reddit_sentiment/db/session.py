from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from reddit_sentiment.core.config import get_settings


@lru_cache
def get_engine() -> AsyncEngine:
    settings = get_settings()
    return create_async_engine(settings.database_url, future=True)


@lru_cache
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False, class_=AsyncSession)


def create_session() -> AsyncSession:
    return get_session_factory()()


class _LazyEngineProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_engine(), name)


engine = _LazyEngineProxy()


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with create_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
