from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from auth.domain.entities import TokenPayload


class TokenProvider(ABC):
    @abstractmethod
    def create_access_token(self, user_id: UUID) -> tuple[str, str, datetime, int]:
        """(token, jti, expired_at, expires_in_seconds) 반환"""

    @abstractmethod
    def decode_token(self, token: str) -> TokenPayload:
        """토큰 서명/만료 검증 후 페이로드 반환"""


class UserCredentialVerifier(ABC):
    """
    로그인 정보 확인 인터페이스
    - auth 는 "이메일/비밀번호가 맞으면 user_id 를 달라"는 것만 알고,
      회원을 어떻게 찾고 비밀번호를 어떻게 비교하는지는 모른다 (user 모듈과의 결합도 감소)
    """

    @abstractmethod
    async def verify_credentials(self, email: str, plain_password: str) -> UUID | None:
        """로그인 성공 시 user_id, 실패 시 None"""
