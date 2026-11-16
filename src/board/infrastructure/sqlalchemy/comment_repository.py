from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from board.domain.post import Comment
from board.domain.repository.comment_repository import CommentRepository
from board.infrastructure.sqlalchemy.mappers import CommentMapper
from board.infrastructure.sqlalchemy.models import CommentModel


class SqlAlchemyCommentRepository(CommentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_by_id(self, comment_id: int) -> Comment | None:
        stmt = select(CommentModel).where(CommentModel.comment_id == comment_id, CommentModel.deleted_at.is_(None))
        model = await self.session.scalar(stmt)
        return CommentMapper.to_domain(model) if model else None

    async def find_by_post_id(self, post_id: int) -> list[Comment]:
        stmt = (
            select(CommentModel)
            .where(CommentModel.post_id == post_id, CommentModel.deleted_at.is_(None))
            .order_by(CommentModel.comment_id.asc())
        )
        models = await self.session.scalars(stmt)
        return [CommentMapper.to_domain(m) for m in models]

    async def save(self, comment: Comment) -> Comment:
        if comment.comment_id:  # 수정 / 소프트 삭제
            model = await self.session.get(CommentModel, comment.comment_id)
            model.content = comment.content
            model.modified_at = comment.modified_at
            model.deleted_at = comment.deleted_at
        else:  # 등록
            model = CommentMapper.to_model(comment)
            self.session.add(model)

        await self.session.flush()
        await self.session.refresh(model)
        return CommentMapper.to_domain(model)
