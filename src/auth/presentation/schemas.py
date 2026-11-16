from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr = Field(description="이메일", examples=["user@example.com"])
    password: str = Field(min_length=1, description="비밀번호", examples=["P@ssw0rd!"])


class TokenResponse(BaseModel):
    access_token: str = Field(description="Authorization 헤더에 'Bearer <토큰>' 형태로 넣을 JWT")
    token_type: str = Field(default="bearer", description="토큰 타입", examples=["bearer"])
    expires_in: int = Field(description="토큰 유효기간(초)", examples=[3600])
