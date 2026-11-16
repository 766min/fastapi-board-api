import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from user.domain.user import PASSWORD_REGEX

PASSWORD_RULE_MESSAGE = "비밀번호는 8자 이상이며 영문, 숫자, 특수문자(@$!%*#?&)를 포함해야 합니다."


def _check_password_rule(value: str) -> str:
    if not PASSWORD_REGEX.match(value):
        raise ValueError(PASSWORD_RULE_MESSAGE)
    return value


class SignUpUserRequest(BaseModel):
    email: EmailStr = Field(description="로그인에 사용할 이메일", examples=["user@example.com"])
    name: str = Field(min_length=2, max_length=20, description="이름 (2~20자)", examples=["홍길동"])
    password: str = Field(description=PASSWORD_RULE_MESSAGE, examples=["P@ssw0rd!"])

    # 커스텀 검증: 비밀번호 규칙을 Pydantic 단계에서 먼저 걸러 422 로 응답
    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return _check_password_rule(value)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("이름은 공백을 제외하고 2자 이상이어야 합니다.")
        return value


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(min_length=1, description="현재 비밀번호")
    new_password: str = Field(description=PASSWORD_RULE_MESSAGE)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return _check_password_rule(value)


class UserResponse(BaseModel):
    """응답에는 password_hash 같은 민감 정보를 절대 넣지 않는다"""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(description="회원 ID")
    email: str = Field(description="이메일")
    name: str = Field(description="이름")
    role: str = Field(description="권한 (USER, ADMIN)")
    created_at: datetime | None = Field(None, description="가입일시")
