from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from common.config import settings
from common.logger import get_logger

logger = get_logger(__name__)

# 커넥션 풀 설정 및 비동기 엔진 생성
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.POOL_SIZE,
    max_overflow=settings.MAX_OVERFLOW,
    pool_timeout=30.0,
    pool_recycle=1800,
    pool_pre_ping=True,
    echo=settings.SQL_ECHO,
)

# 비동기 세션 팩토리
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    요청 1건 = 세션 1개 = 트랜잭션 1개
    - 저장소(repository)는 flush() 로 SQL 만 보내고 확정(commit)하지 않는다
    - 요청이 에러 없이 끝나면 여기서 한 번에 commit, 에러가 나면 전부 rollback
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def close_db() -> None:
    logger.info("데이터베이스 엔진 연결 풀을 종료합니다.")
    await engine.dispose()
