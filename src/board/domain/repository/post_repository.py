from abc import ABC, abstractmethod

from board.domain.enums import PostSearchType
from board.domain.post import Post


class PostRepository(ABC):
    @abstractmethod
    async def find_by_id(self, post_id: int) -> Post | None:
        """게시글 단건 조회 (삭제된 글 제외, 첨부파일 포함)"""

    @abstractmethod
    async def find_by_board_id(
        self, board_id: str, limit: int, offset: int, search_type: PostSearchType, keyword: str | None
    ) -> list[Post]:
        """특정 게시판의 게시글 목록을 최신순으로 페이징 조회"""

    @abstractmethod
    async def count_by_board_id(self, board_id: str, search_type: PostSearchType, keyword: str | None) -> int:
        """특정 게시판의 (검색 조건에 맞는) 게시글 수"""

    @abstractmethod
    async def save(self, post: Post) -> Post:
        """신규면 INSERT, 기존이면 UPDATE (소프트 삭제 포함)"""
