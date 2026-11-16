from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from board.domain.board import Board
from board.domain.repository.board_repository import BoardRepository
from board.infrastructure.sqlalchemy.mappers import BoardMapper
from board.infrastructure.sqlalchemy.models import BoardModel


class SqlAlchemyBoardRepository(BoardRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_by_id(self, board_id: str) -> Board | None:
        stmt = select(BoardModel).where(BoardModel.board_id == board_id, BoardModel.deleted_at.is_(None))
        model = await self.session.scalar(stmt)
        return BoardMapper.to_domain(model) if model else None

    async def find_all(self, include_deleted: bool = False) -> list[Board]:
        stmt = select(BoardModel).order_by(BoardModel.created_at)
        if not include_deleted:
            stmt = stmt.where(BoardModel.deleted_at.is_(None))
        models = await self.session.scalars(stmt)
        return [BoardMapper.to_domain(m) for m in models]

    async def exists_by_id(self, board_id: str) -> bool:
        # 삭제된 게시판의 ID 도 "사용 중"으로 본다 (기본키라서 같은 ID 로 다시 만들 수 없음)
        return await self.session.get(BoardModel, board_id) is not None

    async def save(self, board: Board) -> Board:
        model = await self.session.get(BoardModel, board.board_id)
        if model:  # 수정
            model.board_name = board.board_name
            model.page_size = board.page_size
            model.edit_role = board.authority.edit_role.value
            model.view_role = board.authority.view_role.value
            model.list_role = board.authority.list_role.value
            model.comment_list_role = board.authority.comment_list_role.value
            model.comment_edit_role = board.authority.comment_edit_role.value
            model.deleted_at = board.deleted_at
        else:  # 등록
            model = BoardMapper.to_model(board)
            self.session.add(model)

        await self.session.flush()
        await self.session.refresh(model)
        return BoardMapper.to_domain(model)
