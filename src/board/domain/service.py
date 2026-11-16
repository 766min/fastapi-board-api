from abc import ABC, abstractmethod
from typing import AsyncIterator


class PasswordHasher(ABC):
    """비회원 비밀번호 해싱 인터페이스 (구현은 infrastructure/security.py)"""

    @abstractmethod
    def hash(self, raw_password: str) -> str:
        """평문 비밀번호를 단방향 해시값으로 변환"""

    @abstractmethod
    def verify(self, raw_password: str, hashed_password: str) -> bool:
        """평문 비밀번호가 해시값과 일치하는지 검증"""


class FileStorage(ABC):
    """파일 저장소 인터페이스 - 지금은 로컬 디스크, 나중에 S3 로 바꿔도 서비스 코드는 그대로"""

    @abstractmethod
    async def save(self, chunks: AsyncIterator[bytes], extension: str, max_bytes: int) -> tuple[str, int]:
        """파일 조각(chunk)들을 저장하고 (저장된 파일명, 파일 크기) 반환"""

    @abstractmethod
    def open(self, stored_name: str) -> AsyncIterator[bytes]:
        """저장된 파일을 조각 단위로 읽는 비동기 제너레이터 반환"""

    @abstractmethod
    async def delete(self, stored_name: str) -> None:
        """저장된 파일 삭제 (없으면 무시)"""

    @abstractmethod
    def exists(self, stored_name: str) -> bool:
        """파일 존재 여부"""
