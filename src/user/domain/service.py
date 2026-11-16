from abc import ABC, abstractmethod


class PasswordHasher(ABC):
    """비밀번호 해싱 인터페이스 (구현은 infrastructure/security.py)"""

    @abstractmethod
    def hash(self, raw_password: str) -> str:
        """평문 비밀번호를 단방향 해시값으로 변환"""

    @abstractmethod
    def verify(self, raw_password: str, hashed_password: str) -> bool:
        """평문 비밀번호가 해시값과 일치하는지 검증"""
