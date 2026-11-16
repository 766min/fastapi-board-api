from datetime import datetime
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.domain.repository import TokenBlacklistRepository
from auth.infrastructure.models import TokenBlacklistModel


class SqlAlchemyTokenBlacklistRepository(TokenBlacklistRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, jti: str, expired_at: datetime) -> None:
        self.session.add(TokenBlacklistModel(jti=jti, expired_at=expired_at))
        await self.session.flush()

    async def is_blacklisted(self, jti: str) -> bool:
        result = await self.session.scalar(select(TokenBlacklistModel.jti).where(TokenBlacklistModel.jti == jti))
        return result is not None

    async def cleanup_expired(self, current_time: datetime) -> int:
        result = await self.session.execute(delete(TokenBlacklistModel).where(TokenBlacklistModel.expired_at <= current_time))
        await self.session.flush()
        return result.rowcount
