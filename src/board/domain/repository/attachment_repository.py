from abc import ABC, abstractmethod

from board.domain.post import Attachment


class AttachmentRepository(ABC):
    @abstractmethod
    async def find_by_id(self, attachment_id: int) -> Attachment | None:
        """첨부파일 단건 조회"""

    @abstractmethod
    async def save(self, attachment: Attachment) -> Attachment:
        """첨부파일 정보 등록"""

    @abstractmethod
    async def delete(self, attachment_id: int) -> None:
        """첨부파일 정보 삭제 (실제 파일은 FileStorage 가 삭제)"""
