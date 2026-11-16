from typing import Annotated
from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from auth.application.service import AuthService
from auth.presentation.dependencies import BearerCredentials, provide_auth_service
from common.database import get_db
from common.exception import ForbiddenException, UnauthorizedException
from user.application.service import UserService
from user.domain.repository import UserRepository
from user.domain.service import PasswordHasher
from user.domain.user import User
from user.infrastructure.repositories import SqlAlchemyUserRepository
from user.infrastructure.security import BcryptPasswordHasher
from user.presentation.dependencies import (
    get_current_user,
    get_optional_user,
    provide_user_repository,
    provide_user_service,
    require_admin,
)

# 앱 전체에서 1개만 있으면 되는 객체 (싱글턴)
password_hasher: PasswordHasher = BcryptPasswordHasher()


def create_user_repository(session: AsyncSession = Depends(get_db)) -> UserRepository:
    return SqlAlchemyUserRepository(session)


def create_user_service(repository: UserRepository = Depends(create_user_repository)) -> UserService:
    return UserService(repository=repository, hasher=password_hasher)


async def resolve_optional_user(
    credentials: BearerCredentials,
    auth_service: Annotated[AuthService, Depends(provide_auth_service)],  # wiring/auth.py 의 구현으로 바뀌어 들어온다
    user_repo: Annotated[UserRepository, Depends(create_user_repository)],
) -> User | None:
    """[인증] 토큰이 없으면 None(비회원), 위조/만료/로그아웃된 토큰이면 401"""
    if credentials is None:
        return None

    payload = await auth_service.authenticate_token(credentials.credentials)
    user = await user_repo.find_by_id(payload.user_id)
    if user is None:
        raise UnauthorizedException("존재하지 않는 사용자입니다.", error_code="USER_NOT_FOUND")
    if user.resign:
        raise ForbiddenException("탈퇴한 회원은 서비스를 이용할 수 없습니다.", error_code="USER_ALREADY_WITHDRAWN")
    return user


async def resolve_current_user(current_user: Annotated[User | None, Depends(resolve_optional_user)]) -> User:
    """[인증] 로그인 필수"""
    if current_user is None:
        raise UnauthorizedException("로그인이 필요합니다.", error_code="TOKEN_MISSING")
    return current_user


async def resolve_require_admin(current_user: Annotated[User, Depends(resolve_current_user)]) -> User:
    """[인가] 관리자만 통과"""
    if not current_user.is_admin:
        raise ForbiddenException("관리자 권한이 필요합니다.", error_code="ADMIN_PERMISSION_DENIED")
    return current_user


def wire_user_dependencies(app: FastAPI) -> None:
    app.dependency_overrides.update(
        {
            provide_user_repository: create_user_repository,
            provide_user_service: create_user_service,
            get_optional_user: resolve_optional_user,
            get_current_user: resolve_current_user,
            require_admin: resolve_require_admin,
        }
    )
