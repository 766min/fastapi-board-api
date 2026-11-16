from typing import Annotated
from fastapi import APIRouter, Depends, status

from auth.application.service import AuthService
from auth.presentation.dependencies import get_token, provide_auth_service
from auth.presentation.schemas import LoginRequest, TokenResponse
from common.schemas import APIResponse, error_responses

router = APIRouter(prefix="/v1/auth", tags=["Auth"])

AuthServiceDep = Annotated[AuthService, Depends(provide_auth_service)]


@router.post(
    "/login",
    response_model=APIResponse[TokenResponse],
    summary="로그인",
    description="이메일/비밀번호를 확인하고 JWT 액세스 토큰(HS512)을 발급합니다.",
    responses=error_responses(401, 422),
)
async def login(body: LoginRequest, auth_service: AuthServiceDep):
    token, token_type, expires_in = await auth_service.login(body.email, body.password)
    data = TokenResponse(access_token=token, token_type=token_type, expires_in=expires_in)
    return APIResponse.ok(data=data, message="로그인되었습니다.")


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="로그아웃",
    description="현재 토큰의 jti 를 블랙리스트에 등록해 즉시 사용할 수 없게 만듭니다.",
    responses=error_responses(401),
)
async def logout(token: Annotated[str, Depends(get_token)], auth_service: AuthServiceDep):
    await auth_service.logout(token)
