from typing import Annotated
from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from board.application.service import AttachmentService, BoardService, CommentService, PostService
from board.domain.enums import Role
from board.domain.post import Author
from board.infrastructure.file_storage import LocalFileStorage
from board.infrastructure.security import BcryptPasswordHasher
from board.infrastructure.sqlalchemy.attachment_repository import SqlAlchemyAttachmentRepository
from board.infrastructure.sqlalchemy.board_repository import SqlAlchemyBoardRepository
from board.infrastructure.sqlalchemy.comment_repository import SqlAlchemyCommentRepository
from board.infrastructure.sqlalchemy.post_repository import SqlAlchemyPostRepository
from board.presentation.dependencies import (
    get_current_author,
    get_current_role,
    provide_attachment_service,
    provide_board_service,
    provide_comment_service,
    provide_post_service,
    require_admin_role,
)
from common.cache import InMemoryTTLCache
from common.config import settings
from common.database import get_db
from common.exception import ForbiddenException, UnauthorizedException
from user.domain.user import User
from user.presentation.dependencies import get_optional_user

# 앱 전체에서 1개만 있으면 되는 객체 (싱글턴)
_password_hasher = BcryptPasswordHasher()
_cache = InMemoryTTLCache(default_ttl=settings.CACHE_TTL_SECONDS)
_file_storage = LocalFileStorage(base_dir=settings.UPLOAD_DIR)


# ---------- 서비스 생성 ----------
# 같은 요청 안에서 get_db 는 한 번만 실행되므로, 아래 저장소들은 모두 "같은 세션(=같은 트랜잭션)"을 쓴다
def create_board_service(session: AsyncSession = Depends(get_db)) -> BoardService:
    return BoardService(board_repo=SqlAlchemyBoardRepository(session), cache=_cache)


def create_post_service(session: AsyncSession = Depends(get_db)) -> PostService:
    return PostService(
        post_repo=SqlAlchemyPostRepository(session),
        board_repo=SqlAlchemyBoardRepository(session),
        password_hasher=_password_hasher,
        cache=_cache,
    )


def create_comment_service(session: AsyncSession = Depends(get_db)) -> CommentService:
    return CommentService(
        comment_repo=SqlAlchemyCommentRepository(session),
        post_repo=SqlAlchemyPostRepository(session),
        board_repo=SqlAlchemyBoardRepository(session),
        password_hasher=_password_hasher,
        cache=_cache,
    )


def create_attachment_service(session: AsyncSession = Depends(get_db)) -> AttachmentService:
    return AttachmentService(
        attachment_repo=SqlAlchemyAttachmentRepository(session),
        post_repo=SqlAlchemyPostRepository(session),
        board_repo=SqlAlchemyBoardRepository(session),
        file_storage=_file_storage,
        cache=_cache,
        max_upload_bytes=settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024,
    )


# ---------- 요청자 정보 (회원 -> 게시판 도메인 언어로 변환) ----------
OptionalUserDep = Annotated[User | None, Depends(get_optional_user)]


async def _get_current_role(user: OptionalUserDep) -> Role | None:
    return Role(user.role) if user else None


async def _get_current_author(user: OptionalUserDep) -> Author | None:
    return Author.member(user_id=user.id, username=user.name) if user else None


async def _require_admin_role(role: Annotated[Role | None, Depends(_get_current_role)]) -> Role:
    if role is None:
        raise UnauthorizedException("로그인이 필요합니다.", error_code="TOKEN_MISSING")
    if role != Role.ADMIN:
        raise ForbiddenException("관리자 권한이 필요합니다.", error_code="ADMIN_PERMISSION_DENIED")
    return role


def wire_board_dependencies(app: FastAPI) -> None:
    app.dependency_overrides.update(
        {
            provide_board_service: create_board_service,
            provide_post_service: create_post_service,
            provide_comment_service: create_comment_service,
            provide_attachment_service: create_attachment_service,
            get_current_role: _get_current_role,
            get_current_author: _get_current_author,
            require_admin_role: _require_admin_role,
        }
    )
