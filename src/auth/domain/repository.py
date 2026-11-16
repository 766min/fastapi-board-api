from abc import ABC, abstractmethod
from datetime import datetime


class TokenBlacklistRepository(ABC):
    @abstractmethod
    async def add(self, jti: str, expired_at: datetime) -> None:
        """로그아웃한 토큰의 jti 를 블랙리스트에 등록"""

    @abstractmethod
    async def is_blacklisted(self, jti: str) -> bool:
        """블랙리스트에 등록된 토큰인지 확인"""

    @abstractmethod
    async def cleanup_expired(self, current_time: datetime) -> int:
        """이미 만료된 토큰은 블랙리스트에 둘 필요가 없으므로 정리"""
