from abc import ABC, abstractmethod

from board.domain.board import Board


class BoardRepository(ABC):
    @abstractmethod
    async def find_by_id(self, board_id: str) -> Board | None:
        """게시판 단건 조회 (삭제된 게시판 제외)"""

    @abstractmethod
    async def find_all(self, include_deleted: bool = False) -> list[Board]:
        """게시판 목록 조회"""

    @abstractmethod
    async def exists_by_id(self, board_id: str) -> bool:
        """게시판 ID 사용 여부 (삭제된 게시판 포함 - ID 재사용 방지)"""

    @abstractmethod
    async def save(self, board: Board) -> Board:
        """신규면 INSERT, 기존이면 UPDATE"""
