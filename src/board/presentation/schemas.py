import uuid
from datetime import datetime
from pydantic import BaseModel, Field, computed_field, field_validator

from board.domain.board import Authority, Board
from board.domain.enums import PostSearchType, Role
from board.domain.post import TITLE_MAX_LENGTH, Attachment, Author, Comment, Post
from common.schemas import PageResponse

CONTENT_MAX_LENGTH = 10000


def _strip_not_blank(value: str | None) -> str | None:
    """앞뒤 공백 제거 후, 공백만 있는 문자열은 거부 (커스텀 검증)"""
    if value is None:
        return None
    value = value.strip()
    if not value:
        raise ValueError("공백만 입력할 수 없습니다.")
    return value


# ==================== 게시판 설정 ====================
class AuthoritySchema(BaseModel):
    """게시판 권한 세부 설정"""
    edit_role: Role = Field(default=Role.ALL, description="게시글 작성/수정/삭제 권한")
    view_role: Role = Field(default=Role.ALL, description="게시글 상세 열람 권한")
    list_role: Role = Field(default=Role.ALL, description="게시글 목록 열람 권한")
    comment_list_role: Role = Field(default=Role.ALL, description="댓글 목록 열람 권한")
    comment_edit_role: Role = Field(default=Role.ALL, description="댓글 작성/수정/삭제 권한")

    def to_domain(self) -> Authority:
        return Authority(**self.model_dump())

    @classmethod
    def from_domain(cls, authority: Authority) -> "AuthoritySchema":
        return cls(
            edit_role=authority.edit_role,
            view_role=authority.view_role,
            list_role=authority.list_role,
            comment_list_role=authority.comment_list_role,
            comment_edit_role=authority.comment_edit_role,
        )


class CreateBoardRequest(BaseModel):
    board_id: str = Field(
        pattern=r"^[a-z][a-z0-9_-]{1,29}$",
        description="게시판 ID (영문 소문자로 시작, 영문 소문자/숫자/-/_ 2~30자)",
        examples=["notice"],
    )
    board_name: str = Field(min_length=1, max_length=50, description="게시판 이름", examples=["공지사항"])
    authority: AuthoritySchema = Field(default_factory=AuthoritySchema, description="권한 설정")
    page_size: int = Field(default=20, ge=1, le=100, description="목록 한 페이지당 게시글 수")

    _strip = field_validator("board_name")(_strip_not_blank)


class UpdateBoardRequest(BaseModel):
    board_name: str = Field(min_length=1, max_length=50, description="게시판 이름")
    page_size: int = Field(default=20, ge=1, le=100, description="목록 한 페이지당 게시글 수")
    authority: AuthoritySchema | None = Field(default=None, description="변경할 권한 (생략하면 기존 유지)")

    _strip = field_validator("board_name")(_strip_not_blank)


class BoardResponse(BaseModel):
    board_id: str = Field(description="게시판 ID")
    board_name: str = Field(description="게시판 이름")
    authority: AuthoritySchema = Field(description="권한 설정")
    page_size: int = Field(description="목록 한 페이지당 게시글 수")
    created_at: datetime | None = Field(None, description="생성일시")
    modified_at: datetime | None = Field(None, description="수정일시")
    deleted_at: datetime | None = Field(None, description="삭제일시 (삭제된 게시판만)")

    @classmethod
    def from_domain(cls, board: Board) -> "BoardResponse":
        return cls(
            board_id=board.board_id,
            board_name=board.board_name,
            authority=AuthoritySchema.from_domain(board.authority),
            page_size=board.page_size,
            created_at=board.created_at,
            modified_at=board.modified_at,
            deleted_at=board.deleted_at,
        )


# ==================== 게시글 ====================
class CreatePostRequest(BaseModel):
    """게시글 작성 (회원은 title/content 만, 비회원은 guest_name/guest_password 까지)"""
    title: str = Field(min_length=1, max_length=TITLE_MAX_LENGTH, description="제목", examples=["첫 번째 게시글"])
    content: str = Field(min_length=1, max_length=CONTENT_MAX_LENGTH, description="내용", examples=["안녕하세요!"])
    guest_name: str | None = Field(default=None, min_length=1, max_length=20, description="[비회원] 작성자 이름")
    guest_password: str | None = Field(default=None, min_length=6, description="[비회원] 비밀번호 (6자 이상)")

    _strip = field_validator("title", "content", "guest_name")(_strip_not_blank)


class UpdatePostRequest(BaseModel):
    """게시글 수정 (PUT: 제목/내용을 모두 보낸다)"""
    title: str = Field(min_length=1, max_length=TITLE_MAX_LENGTH, description="제목")
    content: str = Field(min_length=1, max_length=CONTENT_MAX_LENGTH, description="내용")
    guest_password: str | None = Field(default=None, description="[비회원 글] 작성 시 등록한 비밀번호")

    _strip = field_validator("title", "content")(_strip_not_blank)


class GuestPasswordRequest(BaseModel):
    """삭제 요청 본문 (비회원 글/댓글일 때만 필요)"""
    guest_password: str | None = Field(default=None, description="[비회원 글/댓글] 작성 시 등록한 비밀번호")


class PostSearchQuery(BaseModel):
    """게시글 목록 쿼리 파라미터"""
    page: int = Field(default=1, ge=1, description="페이지 번호 (1부터)")
    page_size: int | None = Field(default=None, ge=1, le=100, description="페이지 크기 (생략 시 게시판 설정값)")
    search_type: PostSearchType = Field(default=PostSearchType.ALL, description="검색 대상")
    keyword: str | None = Field(default=None, min_length=1, max_length=50, description="검색어")


class AuthorResponse(BaseModel):
    author_id: uuid.UUID | None = Field(None, description="회원 ID (비회원은 null)")
    author_name: str = Field(description="작성자 이름")
    is_guest: bool = Field(description="비회원 작성 여부")

    @classmethod
    def from_domain(cls, author: Author) -> "AuthorResponse":
        return cls(author_id=author.author_id, author_name=author.author_name, is_guest=author.is_guest)


class AttachmentResponse(BaseModel):
    attachment_id: int = Field(description="첨부파일 ID")
    post_id: int = Field(description="게시글 ID")
    original_name: str = Field(description="원본 파일명")
    content_type: str | None = Field(None, description="파일 MIME 타입")
    size: int = Field(description="파일 크기(byte)")
    created_at: datetime | None = Field(None, description="업로드 일시")

    @computed_field(description="다운로드 URL")
    @property
    def download_url(self) -> str:
        return f"/v1/attachments/{self.attachment_id}"

    @classmethod
    def from_domain(cls, attachment: Attachment) -> "AttachmentResponse":
        return cls(
            attachment_id=attachment.attachment_id,
            post_id=attachment.post_id,
            original_name=attachment.original_name,
            content_type=attachment.content_type,
            size=attachment.size,
            created_at=attachment.created_at,
        )


class PostListItemResponse(BaseModel):
    """목록용 - 내용(content)은 빼서 응답 크기를 줄인다"""
    post_id: int = Field(description="게시글 ID")
    board_id: str = Field(description="게시판 ID")
    board_name: str = Field(description="게시판 이름")
    title: str = Field(description="제목")
    author: AuthorResponse = Field(description="작성자")
    attachment_count: int = Field(description="첨부파일 개수")
    created_at: datetime | None = Field(None, description="작성일시")
    modified_at: datetime | None = Field(None, description="수정일시")

    @classmethod
    def from_domain(cls, post: Post) -> "PostListItemResponse":
        return cls(
            post_id=post.post_id,
            board_id=post.board_info.board_id,
            board_name=post.board_info.board_name,
            title=post.title,
            author=AuthorResponse.from_domain(post.author),
            attachment_count=len(post.attachments),
            created_at=post.created_at,
            modified_at=post.modified_at,
        )


class PostDetailResponse(PostListItemResponse):
    content: str = Field(description="내용")
    attachments: list[AttachmentResponse] = Field(default_factory=list, description="첨부파일 목록")

    @classmethod
    def from_domain(cls, post: Post) -> "PostDetailResponse":
        base = PostListItemResponse.from_domain(post).model_dump()
        return cls(
            **base,
            content=post.content,
            attachments=[AttachmentResponse.from_domain(a) for a in post.attachments],
        )


class PostPageResponse(PageResponse[PostListItemResponse]):
    """게시글 목록 응답 = 공통 페이지 응답 + 적용된 검색 조건"""
    search_type: PostSearchType = Field(description="적용된 검색 대상")
    keyword: str | None = Field(default=None, description="적용된 검색어")


# ==================== 댓글 ====================
class CreateCommentRequest(BaseModel):
    content: str = Field(min_length=1, max_length=1000, description="댓글 내용", examples=["좋은 글이네요!"])
    guest_name: str | None = Field(default=None, min_length=1, max_length=20, description="[비회원] 작성자 이름")
    guest_password: str | None = Field(default=None, min_length=6, description="[비회원] 비밀번호 (6자 이상)")

    _strip = field_validator("content", "guest_name")(_strip_not_blank)


class UpdateCommentRequest(BaseModel):
    content: str = Field(min_length=1, max_length=1000, description="수정할 댓글 내용")
    guest_password: str | None = Field(default=None, description="[비회원 댓글] 작성 시 등록한 비밀번호")

    _strip = field_validator("content")(_strip_not_blank)


class CommentResponse(BaseModel):
    comment_id: int = Field(description="댓글 ID")
    post_id: int = Field(description="게시글 ID")
    content: str = Field(description="댓글 내용")
    author: AuthorResponse = Field(description="작성자")
    created_at: datetime | None = Field(None, description="작성일시")
    modified_at: datetime | None = Field(None, description="수정일시")

    @classmethod
    def from_domain(cls, comment: Comment) -> "CommentResponse":
        return cls(
            comment_id=comment.comment_id,
            post_id=comment.post_id,
            content=comment.content,
            author=AuthorResponse.from_domain(comment.author),
            created_at=comment.created_at,
            modified_at=comment.modified_at,
        )
