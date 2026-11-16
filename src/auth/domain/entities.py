from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class TokenPayload:
    """JWT 안에 들어있는 정보"""
    user_id: UUID   # sub: 토큰 주인
    jti: str        # 토큰 고유 ID (로그아웃 블랙리스트에 사용)
    exp: datetime   # 만료 시각
