import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from board.domain.enums import Role
from board.domain.service import PasswordHasher
from common.exception import BadRequestException, ValidationException

"""
[게시글/댓글 규칙]
1. 비회원으로 글 또는 댓글 작성 시 비밀번호(6자리 이상)를 등록해야 하며,
   수정/삭제 시 작성할 때 등록한 비밀번호를 검증한다.
2. 회원 글/댓글은 직접 작성한 회원만 수정/삭제 가능하며, 관리자는 상관없이 가능하다.
3. 게시글/댓글은 소프트 삭제한다. (deleted_at 기록)
4. 첨부파일은 회원 게시글에만 올릴 수 있으며, 작성자 본인 또는 관리자만 업로드/삭제할 수 있다.
5. 첨부파일은 허용된 확장자만 업로드할 수 있다.
"""

TITLE_MAX_LENGTH = 200
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".pdf", ".txt", ".zip"}


# ==================== 값 객체 (Value Object) ====================
@dataclass(frozen=True)
class BoardInfo:
    """게시글이 속한 게시판 정보"""
    board_id: str
    board_name: str


@dataclass(frozen=True)
class Author:
    """작성자 정보 (회원이면 author_id 가 있고, 비회원이면 None)"""
    author_name: str
    author_id: uuid.UUID | None = None

    def __post_init__(self):
        name = (self.author_name or "").strip()
        if not (1 <= len(name) <= 20):
            raise ValidationException(
                "작성자 정보 유효성 검사에 실패했습니다.",
                field_errors={"author_name": ["작성자 이름은 1자 이상 20자 이하여야 합니다."]},
            )

    @property
    def is_guest(self) -> bool:
        return self.author_id is None

    @classmethod
    def member(cls, user_id: uuid.UUID, username: str) -> "Author":
        return cls(author_id=user_id, author_name=username.strip())

    @classmethod
    def guest(cls, guest_name: str) -> "Author":
        return cls(author_id=None, author_name=guest_name.strip())

    def is_owner(self, user_id: uuid.UUID | None) -> bool:
        """로그인 사용자가 작성자 본인인지 (비회원 글은 항상 False)"""
        if self.is_guest or user_id is None:
            return False
        return self.author_id == user_id


@dataclass(frozen=True)
class GuestPassword:
    """비회원 비밀번호 (해시 문자열만 보관)"""
    hashed_value: str

    @classmethod
    def create(cls, raw_password: str, hasher: PasswordHasher) -> "GuestPassword":
        if not raw_password or len(raw_password) < 6:
            raise ValidationException(
                "비회원 비밀번호 유효성 검사에 실패했습니다.",
                field_errors={"guest_password": ["비회원 비밀번호는 6자리 이상이어야 합니다."]},
            )
        return cls(hashed_value=hasher.hash(raw_password))

    def verify(self, raw_password: str | None, hasher: PasswordHasher) -> bool:
        if not raw_password:
            return False
        return hasher.verify(raw_password, self.hashed_value)


def _can_modify_or_delete(
    author: Author,
    guest_password: GuestPassword | None,
    requester_id: uuid.UUID | None,
    user_role: Role | None,
    raw_guest_password: str | None,
    hasher: PasswordHasher,
) -> bool:
    """수정/삭제 권한 확인 (관리자 -> 회원 본인 -> 비회원 비밀번호 일치 순)"""
    if user_role == Role.ADMIN:
        return True
    if not author.is_guest:
        return author.is_owner(requester_id)
    return guest_password is not None and guest_password.verify(raw_guest_password, hasher)


def _make_guest_password(author: Author, raw_guest_password: str | None, hasher: PasswordHasher) -> GuestPassword | None:
    if not author.is_guest:
        return None
    if not raw_guest_password:
        raise ValidationException(
            "비회원은 비밀번호를 입력해야 합니다.",
            field_errors={"guest_password": ["비회원 비밀번호는 필수입니다."]},
        )
    return GuestPassword.create(raw_guest_password, hasher)


# ==================== 엔티티 ====================
@dataclass
class Attachment:
    """첨부파일"""
    post_id: int
    original_name: str       # 사용자가 올린 원래 파일명 (다운로드 시 표시)
    stored_name: str         # 서버 디스크 저장 파일명 (uuid - 중복/경로조작 방지)
    content_type: str | None
    size: int
    attachment_id: int | None = None
    created_at: datetime | None = None

    @staticmethod
    def extract_extension(filename: str) -> str:
        """파일명에서 확장자를 꺼내고, 허용된 확장자인지 검사"""
        name = os.path.basename(filename or "")
        extension = os.path.splitext(name)[1].lower()
        if not name or extension not in ALLOWED_EXTENSIONS:
            raise ValidationException(
                "허용되지 않는 파일 형식입니다.",
                error_code="INVALID_FILE_TYPE",
                field_errors={"file": [f"허용 확장자: {', '.join(sorted(ALLOWED_EXTENSIONS))}"]},
            )
        return extension


@dataclass
class Post:
    """게시글"""
    board_info: BoardInfo
    title: str
    content: str
    author: Author
    guest_password: GuestPassword | None = None
    post_id: int | None = None

    created_at: datetime | None = None
    modified_at: datetime | None = None
    deleted_at: datetime | None = None
    attachments: list[Attachment] = field(default_factory=list)

    def __post_init__(self):
        self._validate(self.title, self.content)
        if self.author.is_guest and self.guest_password is None:
            raise ValidationException(
                "게시글 유효성 검사에 실패했습니다.",
                field_errors={"guest_password": ["비회원 작성 시 비밀번호 등록은 필수입니다."]},
            )

    @classmethod
    def create(
        cls,
        board_info: BoardInfo,
        title: str,
        content: str,
        author: Author,
        raw_guest_password: str | None,
        hasher: PasswordHasher,
    ) -> "Post":
        return cls(
            board_info=board_info,
            title=title.strip(),
            content=content.strip(),
            author=author,
            guest_password=_make_guest_password(author, raw_guest_password, hasher),
        )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def can_modify_or_delete(
        self, requester_id: uuid.UUID | None, user_role: Role | None, raw_guest_password: str | None, hasher: PasswordHasher
    ) -> bool:
        return _can_modify_or_delete(self.author, self.guest_password, requester_id, user_role, raw_guest_password, hasher)

    def can_manage_attachments(self, requester_id: uuid.UUID | None, user_role: Role | None) -> bool:
        """첨부파일 업로드/삭제 권한: 관리자 또는 회원 작성자 본인"""
        return user_role == Role.ADMIN or self.author.is_owner(requester_id)

    def update_content(self, title: str, content: str) -> None:
        if self.is_deleted:
            raise BadRequestException("삭제된 게시글은 수정할 수 없습니다.", error_code="POST_DELETED")
        title, content = title.strip(), content.strip()
        self._validate(title, content)
        self.title, self.content = title, content
        self.modified_at = datetime.now(timezone.utc)

    def delete(self) -> None:
        if self.is_deleted:
            raise BadRequestException("이미 삭제된 게시글입니다.", error_code="POST_DELETED")
        self.deleted_at = datetime.now(timezone.utc)

    @staticmethod
    def _validate(title: str, content: str) -> None:
        field_errors: dict[str, list[str]] = {}
        if not title or not title.strip():
            field_errors["title"] = ["제목은 필수 입력값입니다."]
        elif len(title) > TITLE_MAX_LENGTH:
            field_errors["title"] = [f"제목은 {TITLE_MAX_LENGTH}자 이하여야 합니다."]
        if not content or not content.strip():
            field_errors["content"] = ["내용은 필수 입력값입니다."]
        if field_errors:
            raise ValidationException("게시글 유효성 검사에 실패했습니다.", field_errors=field_errors)


@dataclass
class Comment:
    """댓글"""
    post_id: int
    content: str
    author: Author
    guest_password: GuestPassword | None = None
    comment_id: int | None = None

    created_at: datetime | None = None
    modified_at: datetime | None = None
    deleted_at: datetime | None = None

    def __post_init__(self):
        if not self.content or not self.content.strip():
            raise ValidationException("댓글 유효성 검사에 실패했습니다.", field_errors={"content": ["댓글 내용은 필수 입력값입니다."]})
        if self.author.is_guest and self.guest_password is None:
            raise ValidationException(
                "댓글 유효성 검사에 실패했습니다.",
                field_errors={"guest_password": ["비회원 댓글 작성 시 비밀번호 등록은 필수입니다."]},
            )

    @classmethod
    def create(
        cls, post_id: int, content: str, author: Author, raw_guest_password: str | None, hasher: PasswordHasher
    ) -> "Comment":
        return cls(
            post_id=post_id,
            content=content.strip(),
            author=author,
            guest_password=_make_guest_password(author, raw_guest_password, hasher),
        )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def can_modify_or_delete(
        self, requester_id: uuid.UUID | None, user_role: Role | None, raw_guest_password: str | None, hasher: PasswordHasher
    ) -> bool:
        return _can_modify_or_delete(self.author, self.guest_password, requester_id, user_role, raw_guest_password, hasher)

    def update_content(self, content: str) -> None:
        if self.is_deleted:
            raise BadRequestException("삭제된 댓글은 수정할 수 없습니다.", error_code="COMMENT_DELETED")
        if not content or not content.strip():
            raise ValidationException("댓글 수정 유효성 검사에 실패했습니다.", field_errors={"content": ["댓글 내용은 공백일 수 없습니다."]})
        self.content = content.strip()
        self.modified_at = datetime.now(timezone.utc)

    def delete(self) -> None:
        if self.is_deleted:
            raise BadRequestException("이미 삭제된 댓글입니다.", error_code="COMMENT_DELETED")
        self.deleted_at = datetime.now(timezone.utc)
