from abc import ABC, abstractmethod

from board.domain.post import Comment


class CommentRepository(ABC):
    @abstractmethod
    async def find_by_id(self, comment_id: int) -> Comment | None:
        """댓글 단건 조회 (삭제된 댓글 제외)"""

    @abstractmethod
    async def find_by_post_id(self, post_id: int) -> list[Comment]:
        """게시글의 댓글 목록 (등록순)"""

    @abstractmethod
    async def save(self, comment: Comment) -> Comment:
        """신규면 INSERT, 기존이면 UPDATE (소프트 삭제 포함)"""
