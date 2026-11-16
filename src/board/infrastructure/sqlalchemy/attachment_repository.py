from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from board.domain.post import Attachment
from board.domain.repository.attachment_repository import AttachmentRepository
from board.infrastructure.sqlalchemy.mappers import AttachmentMapper
from board.infrastructure.sqlalchemy.models import AttachmentModel


class SqlAlchemyAttachmentRepository(AttachmentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_by_id(self, attachment_id: int) -> Attachment | None:
        model = await self.session.get(AttachmentModel, attachment_id)
        return AttachmentMapper.to_domain(model) if model else None

    async def save(self, attachment: Attachment) -> Attachment:
        model = AttachmentMapper.to_model(attachment)
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return AttachmentMapper.to_domain(model)

    async def delete(self, attachment_id: int) -> None:
        await self.session.execute(delete(AttachmentModel).where(AttachmentModel.attachment_id == attachment_id))
        await self.session.flush()
