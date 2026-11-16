import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from common.exception import BadRequestException, ForbiddenException, ValidationException
from user.domain.service import PasswordHasher

"""
[회원 규칙]
1. 비밀번호는 8자리 이상이며, 영문/숫자/특수문자(@$!%*#?&)를 각각 1개 이상 포함한다.
2. 이메일은 유효한 형식이어야 하며 로그인에 사용되므로 중복될 수 없다.
3. 이름은 2자 ~ 20자.
4. 탈퇴는 소프트 삭제: deleted_at 에 탈퇴 일시를 기록하고 resign=True 로 바꾼다.
5. 탈퇴는 본인 또는 관리자만 가능하다.
"""

EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")
PASSWORD_REGEX = re.compile(r"^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!%*#?&]{8,}$")

UserRole = Literal["USER", "ADMIN"]


@dataclass
class User:
    email: str
    name: str
    password_hash: str
    role: UserRole = "USER"
    resign: bool = False  # 탈퇴 여부

    id: uuid.UUID | None = None
    created_at: datetime | None = None
    modified_at: datetime | None = None
    deleted_at: datetime | None = None

    @property
    def is_admin(self) -> bool:
        return self.role == "ADMIN"

    @classmethod
    def create(cls, email: str, name: str, raw_password: str, hasher: PasswordHasher) -> "User":
        """신규 회원 생성 - 규칙 검증 후 비밀번호를 해싱해서 보관"""
        cls._validate_email(email)
        cls._validate_name(name)
        cls._validate_password(raw_password)
        return cls(email=email, name=name, password_hash=hasher.hash(raw_password))

    def change_password(self, old_password: str, new_password: str, hasher: PasswordHasher) -> None:
        self._ensure_active()
        if not hasher.verify(old_password, self.password_hash):
            raise BadRequestException("기존 비밀번호가 일치하지 않습니다.", error_code="INVALID_OLD_PASSWORD")
        if old_password == new_password:
            raise BadRequestException("새 비밀번호는 기존 비밀번호와 달라야 합니다.", error_code="SAME_PASSWORD")
        self._validate_password(new_password)
        self.password_hash = hasher.hash(new_password)
        self.modified_at = datetime.now(timezone.utc)

    def withdraw(self, requester: "User") -> None:
        """회원 탈퇴 (소프트 삭제)"""
        self._ensure_active()
        if not (self.id == requester.id or requester.is_admin):
            raise ForbiddenException("탈퇴 처리는 본인 또는 관리자만 가능합니다.", error_code="WITHDRAW_PERMISSION_DENIED")
        now = datetime.now(timezone.utc)
        self.resign = True
        self.deleted_at = now
        self.modified_at = now

    def _ensure_active(self) -> None:
        if self.resign:
            raise ForbiddenException("탈퇴한 회원입니다.", error_code="USER_ALREADY_WITHDRAWN")

    @staticmethod
    def _validate_email(email: str) -> None:
        if not EMAIL_REGEX.match(email):
            raise ValidationException("유효하지 않은 이메일 형식입니다.", field_errors={"email": ["올바른 이메일 형식을 입력하세요."]})

    @staticmethod
    def _validate_name(name: str) -> None:
        if not (2 <= len(name) <= 20):
            raise ValidationException("이름은 2자 이상 20자 이하여야 합니다.", field_errors={"name": ["이름은 2자 이상 20자 이하여야 합니다."]})

    @staticmethod
    def _validate_password(raw_password: str) -> None:
        if not PASSWORD_REGEX.match(raw_password):
            raise ValidationException(
                "비밀번호 규칙을 만족하지 않습니다.",
                field_errors={"password": ["비밀번호는 8자 이상이며 영문, 숫자, 특수문자(@$!%*#?&)를 포함해야 합니다."]},
            )
