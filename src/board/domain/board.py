import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

from board.domain.enums import Role
from common.exception import BadRequestException, ValidationException

"""
[게시판 설정 규칙]
1. 게시판은 무한대로 생성 가능하다. 게시판 설정 하나가 게시판 하나가 된다. (예: freetalk, qna)
2. 게시판은 비회원, 회원, 관리자 모두 사용 가능하며, 역할별로 이용 제한을 설정할 수 있다.
3. 권한 종류
    - edit_role         : 글 쓰기/수정/삭제
    - view_role         : 글 상세 열람
    - list_role         : 글 목록 열람
    - comment_list_role : 댓글 목록 열람
    - comment_edit_role : 댓글 쓰기/수정/삭제
4. 게시글 목록 노출 개수(page_size)는 설정 가능하며 기본값은 20이다.
5. 게시판 ID는 영문 소문자로 시작, 영문 소문자/숫자/하이픈/언더스코어 허용 (2~30자)
6. 게시판 설정은 소프트 삭제를 하며 삭제된 게시판은 수정할 수 없다.
7. 게시판 생성/수정/삭제는 관리자만 가능하다.
"""

BOARD_ID_REGEX = re.compile(r"^[a-z][a-z0-9_-]{1,29}$")


@dataclass(frozen=True)
class Authority:
    """게시판 세부 권한 설정 (값 객체)"""

    edit_role: Role = Role.ALL
    view_role: Role = Role.ALL
    list_role: Role = Role.ALL
    comment_list_role: Role = Role.ALL
    comment_edit_role: Role = Role.ALL

    def can_edit(self, user_role: Role | None) -> bool:
        return self._check(user_role, self.edit_role)

    def can_view(self, user_role: Role | None) -> bool:
        return self._check(user_role, self.view_role)

    def can_list(self, user_role: Role | None) -> bool:
        return self._check(user_role, self.list_role)

    def can_view_comments(self, user_role: Role | None) -> bool:
        return self._check(user_role, self.comment_list_role)

    def can_edit_comments(self, user_role: Role | None) -> bool:
        return self._check(user_role, self.comment_edit_role)

    @staticmethod
    def _check(user_role: Role | None, required: Role) -> bool:
        if user_role is None:  # 비회원
            return required == Role.ALL
        return Role(user_role).satisfies(required)


@dataclass
class Board:
    """게시판 설정 엔티티"""

    board_id: str    # freetalk, qna
    board_name: str  # 자유게시판, 질문과 답변
    authority: Authority = field(default_factory=Authority)
    page_size: int = 20

    created_at: datetime | None = None
    modified_at: datetime | None = None
    deleted_at: datetime | None = None

    def __post_init__(self):
        field_errors: dict[str, list[str]] = {}

        normalized_id = (self.board_id or "").strip().lower()
        if not BOARD_ID_REGEX.match(normalized_id):
            field_errors["board_id"] = [
                "영문 소문자로 시작해야 하며, 2~30자의 영문 소문자, 숫자, 특수문자(-, _)만 사용할 수 있습니다."
            ]
        else:
            self.board_id = normalized_id

        if not self.board_name or not self.board_name.strip():
            field_errors["board_name"] = ["게시판 이름은 공백일 수 없습니다."]

        if self.page_size < 1:
            field_errors["page_size"] = ["게시글 목록 노출 개수는 1 이상이어야 합니다."]

        if field_errors:
            raise ValidationException("게시판 설정 유효성 검사에 실패했습니다.", field_errors=field_errors)

    @classmethod
    def create(cls, board_id: str, board_name: str, authority: Authority | None = None, page_size: int = 20) -> "Board":
        return cls(board_id=board_id, board_name=board_name.strip(), authority=authority or Authority(), page_size=page_size)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def update_config(self, board_name: str, page_size: int, authority: Authority | None = None) -> None:
        if self.is_deleted:
            raise BadRequestException("삭제된 게시판 설정은 수정할 수 없습니다.", error_code="BOARD_DELETED")

        field_errors: dict[str, list[str]] = {}
        if not board_name or not board_name.strip():
            field_errors["board_name"] = ["게시판 이름은 공백일 수 없습니다."]
        if page_size < 1:
            field_errors["page_size"] = ["게시글 목록 노출 개수는 1 이상이어야 합니다."]
        if field_errors:
            raise ValidationException("게시판 설정 수정 유효성 검사에 실패했습니다.", field_errors=field_errors)

        self.board_name = board_name.strip()
        self.page_size = page_size
        if authority is not None:
            self.authority = authority
        self.modified_at = datetime.now(timezone.utc)

    def delete(self) -> None:
        if self.is_deleted:
            raise BadRequestException("이미 삭제된 게시판입니다.", error_code="BOARD_DELETED")
        self.deleted_at = datetime.now(timezone.utc)
