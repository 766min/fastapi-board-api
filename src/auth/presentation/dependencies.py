from typing import Annotated
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from auth.application.service import AuthService
from common.exception import UnauthorizedException

# auto_error=False : 토큰이 없을 때 FastAPI 기본 에러 대신 우리 공통 에러 형식으로 응답하기 위해
#                    (비회원 허용 API 에서는 토큰이 없어도 통과시켜야 하므로 필수)
bearer_scheme = HTTPBearer(auto_error=False, description="로그인 API 로 발급받은 access_token 을 입력하세요.")

BearerCredentials = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]


def provide_auth_service() -> AuthService:
    """FastAPI Depends 자리표시자 (실제 객체는 wiring/auth.py 에서 연결)"""
    raise NotImplementedError("AuthService 의존성이 주입되지 않았습니다.")


async def get_token(credentials: BearerCredentials) -> str:
    """Authorization: Bearer <토큰> 헤더에서 토큰 문자열만 꺼낸다 (없으면 401)"""
    if credentials is None:
        raise UnauthorizedException("로그인이 필요합니다.", error_code="TOKEN_MISSING")
    return credentials.credentials
