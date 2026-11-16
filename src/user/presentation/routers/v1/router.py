from typing import Annotated
from fastapi import APIRouter, Depends, status

from common.schemas import APIResponse, error_responses
from user.application.service import UserService
from user.presentation.dependencies import CurrentUser, provide_user_service
from user.presentation.schemas import ChangePasswordRequest, SignUpUserRequest, UserResponse

router = APIRouter(prefix="/v1/users", tags=["Users"])

UserServiceDep = Annotated[UserService, Depends(provide_user_service)]


@router.post(
    "",
    response_model=APIResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="회원가입",
    description="이메일/이름/비밀번호로 회원가입합니다. 비밀번호는 bcrypt 로 해싱되어 저장됩니다.",
    responses=error_responses(409, 422),
)
async def sign_up(body: SignUpUserRequest, user_service: UserServiceDep):
    user = await user_service.register_user(email=body.email, name=body.name, password=body.password)
    return APIResponse.ok(data=UserResponse.model_validate(user), message="회원가입이 완료되었습니다.")


@router.get("/me", response_model=APIResponse[UserResponse], summary="내 정보 조회", responses=error_responses(401))
async def get_me(current_user: CurrentUser):
    return APIResponse.ok(data=UserResponse.model_validate(current_user))


@router.patch(
    "/me/password",
    response_model=APIResponse[None],
    summary="내 비밀번호 변경",
    description="로그인한 본인의 비밀번호만 변경할 수 있습니다.",
    responses=error_responses(400, 401, 422),
)
async def change_my_password(body: ChangePasswordRequest, current_user: CurrentUser, user_service: UserServiceDep):
    await user_service.change_password(current_user, body.old_password, body.new_password)
    return APIResponse.ok(message="비밀번호가 변경되었습니다.")


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="회원 탈퇴",
    description="소프트 삭제 방식으로 탈퇴합니다. 탈퇴 후에는 로그인할 수 없습니다.",
    responses=error_responses(401, 403),
)
async def withdraw_me(current_user: CurrentUser, user_service: UserServiceDep):
    await user_service.withdraw(target=current_user, requester=current_user)
