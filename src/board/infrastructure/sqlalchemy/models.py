import uuid
from datetime import datetime
from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.models import Base, DateTimeBase

"""
[테이블 관계]
boards 1 ── N posts        (게시판 하나에 여러 게시글)
users  1 ── N posts        (회원이 쓴 글 / 비회원 글은 author_id = NULL)
posts  1 ── N comments     (게시글 하나에 여러 댓글)
posts  1 ── N attachments  (게시글 하나에 여러 첨부파일)

[lazy 옵션]
joined   : 처음 조회할 때 LEFT JOIN 으로 같이 가져온다 (N:1, 예: 게시글 -> 게시판 이름)
selectin : 본 쿼리 후 "WHERE post_id IN (...)" 쿼리 1번으로 자식들을 한꺼번에 가져온다 (1:N)
-> 둘 다 게시글 10개를 조회할 때 쿼리가 10번 더 나가는 N+1 문제를 막는다
"""


class BoardModel(Base, DateTimeBase):
    """게시판 설정 테이블"""
    __tablename__ = "boards"

    board_id: Mapped[str] = mapped_column("id", String(30), primary_key=True)
    board_name: Mapped[str] = mapped_column(String(100), nullable=False)
    page_size: Mapped[int] = mapped_column(Integer, default=20, nullable=False)

    # 게시판 권한 (ALL / USER / ADMIN)
    edit_role: Mapped[str] = mapped_column(String(20), default="ALL", nullable=False)
    view_role: Mapped[str] = mapped_column(String(20), default="ALL", nullable=False)
    list_role: Mapped[str] = mapped_column(String(20), default="ALL", nullable=False)
    comment_list_role: Mapped[str] = mapped_column(String(20), default="ALL", nullable=False)
    comment_edit_role: Mapped[str] = mapped_column(String(20), default="ALL", nullable=False)


class PostModel(Base, DateTimeBase):
    """게시글 테이블"""
    __tablename__ = "posts"
    __table_args__ = (
        # 목록 조회 조건(board_id = ? AND deleted_at IS NULL)에 맞춘 복합 인덱스
        Index("ix_posts_board_id_deleted_at", "board_id", "deleted_at"),
        Index("ix_posts_author_id", "author_id"),
    )

    post_id: Mapped[int] = mapped_column("id", BigInteger, primary_key=True, autoincrement=True)
    board_id: Mapped[str] = mapped_column(String(30), ForeignKey("boards.id"), nullable=False)

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # 작성자 이름을 글에 같이 저장 -> 목록 조회 때 users 테이블을 JOIN 하지 않아도 된다
    author_name: Mapped[str] = mapped_column(String(50), nullable=False)
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    guest_password: Mapped[str | None] = mapped_column(String(255), nullable=True)  # 비회원 비밀번호 해시

    board: Mapped[BoardModel] = relationship(lazy="joined")
    attachments: Mapped[list["AttachmentModel"]] = relationship(
        back_populates="post", lazy="selectin", order_by="AttachmentModel.attachment_id"
    )


class CommentModel(Base, DateTimeBase):
    """댓글 테이블"""
    __tablename__ = "comments"
    __table_args__ = (Index("ix_comments_post_id_deleted_at", "post_id", "deleted_at"),)

    comment_id: Mapped[int] = mapped_column("id", BigInteger, primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("posts.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    author_name: Mapped[str] = mapped_column(String(50), nullable=False)
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    guest_password: Mapped[str | None] = mapped_column(String(255), nullable=True)


class AttachmentModel(Base):
    """첨부파일 테이블 (파일 자체는 디스크에, 여기엔 파일 정보만 저장)"""
    __tablename__ = "attachments"

    attachment_id: Mapped[int] = mapped_column("id", BigInteger, primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    post: Mapped[PostModel] = relationship(back_populates="attachments", lazy="raise")
