from enum import StrEnum


class Role(StrEnum):
    """게시판 권한 등급 (숫자가 클수록 상위 권한)"""

    ALL = "ALL"      # 비회원 포함 모두
    USER = "USER"    # 회원 + 관리자
    ADMIN = "ADMIN"  # 관리자만

    @property
    def level(self) -> int:
        return {Role.ALL: 0, Role.USER: 1, Role.ADMIN: 2}[self]

    def satisfies(self, required_role: "Role | str") -> bool:
        """현재 역할이 요구 권한 이상인지 확인 (예: ADMIN 은 USER 권한도 만족)"""
        return self.level >= Role(required_role).level


class PostSearchType(StrEnum):
    """게시글 검색 대상"""

    ALL = "ALL"                      # 제목 + 내용 + 작성자 이름 + 작성자 이메일
    TITLE = "TITLE"
    CONTENT = "CONTENT"
    TITLE_CONTENT = "TITLE_CONTENT"
    AUTHOR_NAME = "AUTHOR_NAME"
    AUTHOR_EMAIL = "AUTHOR_EMAIL"
