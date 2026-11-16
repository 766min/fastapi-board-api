from typing import Annotated
from fastapi import Depends

from board.application.service import AttachmentService, BoardService, CommentService, PostService
from board.domain.enums import Role
from board.domain.post import Author
from common.exception import ValidationException

"""
FastAPI Depends 자리표시자 모음 (실제 구현은 wiring/board.py 에서 연결)
"""


def provide_board_service() -> BoardService:
    raise NotImplementedError("BoardService 의존성이 주입되지 않았습니다.")


def provide_post_service() -> PostService:
    raise NotImplementedError("PostService 의존성이 주입되지 않았습니다.")


def provide_comment_service() -> CommentService:
    raise NotImplementedError("CommentService 의존성이 주입되지 않았습니다.")


def provide_attachment_service() -> AttachmentService:
    raise NotImplementedError("AttachmentService 의존성이 주입되지 않았습니다.")


async def get_current_role() -> Role | None:
    """요청자의 권한 - 비회원: None / 회원: Role.USER / 관리자: Role.ADMIN"""
    raise NotImplementedError("get_current_role 의존성이 주입되지 않았습니다.")


async def get_current_author() -> Author | None:
    """요청자의 작성자 정보 - 회원: Author.member(...) / 비회원: None"""
    raise NotImplementedError("get_current_author 의존성이 주입되지 않았습니다.")


async def require_admin_role() -> Role:
    """관리자만 통과 (게시판 설정 변경용)"""
    raise NotImplementedError("require_admin_role 의존성이 주입되지 않았습니다.")


# 라우터에서 짧게 쓰기 위한 별칭
CurrentRole = Annotated[Role | None, Depends(get_current_role)]
CurrentAuthor = Annotated[Author | None, Depends(get_current_author)]
AdminRole = Annotated[Role, Depends(require_admin_role)]


def build_author(current_author: Author | None, guest_name: str | None, guest_password: str | None) -> tuple[Author, str | None]:
    """
    글/댓글 작성자를 결정한다.
    - 로그인 회원: 토큰의 회원 정보 사용 (guest_* 값은 무시)
    - 비회원: guest_name, guest_password 필수
    """
    if current_author is not None:
        return current_author, None

    field_errors: dict[str, list[str]] = {}
    if not guest_name:
        field_errors["guest_name"] = ["비회원은 작성자 이름을 입력해야 합니다."]
    if not guest_password:
        field_errors["guest_password"] = ["비회원은 비밀번호(6자 이상)를 입력해야 합니다."]
    if field_errors:
        raise ValidationException("비회원 작성 정보가 부족합니다.", error_code="GUEST_INFO_REQUIRED", field_errors=field_errors)

    return Author.guest(guest_name), guest_password
