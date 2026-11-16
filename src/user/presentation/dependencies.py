from typing import Annotated
from fastapi import Depends

from user.application.service import UserService
from user.domain.repository import UserRepository
from user.domain.user import User

"""
FastAPI Depends 자리표시자 모음
- 라우터는 이 "빈 자리"만 알고, 실제 구현은 wiring/user.py 가 dependency_overrides 로 끼워 넣는다
"""


def provide_user_service() -> UserService:
    raise NotImplementedError("UserService 의존성이 주입되지 않았습니다.")


def provide_user_repository() -> UserRepository:
    raise NotImplementedError("UserRepository 의존성이 주입되지 않았습니다.")


async def get_current_user() -> User:
    """로그인 필수 - 토큰이 없거나 잘못되면 401"""
    raise NotImplementedError("get_current_user 의존성이 주입되지 않았습니다.")


async def get_optional_user() -> User | None:
    """로그인 선택 - 토큰이 없으면 None(비회원), 토큰이 잘못되면 401"""
    raise NotImplementedError("get_optional_user 의존성이 주입되지 않았습니다.")


async def require_admin() -> User:
    """관리자만 통과"""
    raise NotImplementedError("require_admin 의존성이 주입되지 않았습니다.")


# 라우터에서 짧게 쓰기 위한 별칭
CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]
AdminUser = Annotated[User, Depends(require_admin)]
