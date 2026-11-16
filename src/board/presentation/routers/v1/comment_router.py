from typing import Annotated
from fastapi import APIRouter, Body, Depends, Path, status

from board.application.service import CommentService
from board.presentation.dependencies import CurrentAuthor, CurrentRole, build_author, provide_comment_service
from board.presentation.schemas import CommentResponse, CreateCommentRequest, GuestPasswordRequest, UpdateCommentRequest
from common.schemas import APIResponse, error_responses

router = APIRouter(prefix="/v1", tags=["Comments"])

CommentServiceDep = Annotated[CommentService, Depends(provide_comment_service)]
PostId = Annotated[int, Path(ge=1, description="게시글 ID")]
CommentId = Annotated[int, Path(ge=1, description="댓글 ID")]


@router.post(
    "/posts/{post_id}/comments",
    response_model=APIResponse[CommentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="댓글 작성 (회원/비회원)",
    responses=error_responses(401, 403, 404, 422),
)
async def write_comment(
    post_id: PostId,
    body: CreateCommentRequest,
    current_author: CurrentAuthor,
    current_role: CurrentRole,
    service: CommentServiceDep,
):
    author, raw_password = build_author(current_author, body.guest_name, body.guest_password)
    comment = await service.write_comment(post_id, body.content, author, raw_password, current_role)
    return APIResponse.ok(data=CommentResponse.from_domain(comment), message="댓글이 등록되었습니다.")


@router.get(
    "/posts/{post_id}/comments",
    response_model=APIResponse[list[CommentResponse]],
    summary="댓글 목록 조회",
    responses=error_responses(403, 404),
)
async def list_comments(post_id: PostId, current_role: CurrentRole, service: CommentServiceDep):
    comments = await service.list_comments(post_id, current_role)
    return APIResponse.ok(data=[CommentResponse.from_domain(c) for c in comments])


@router.put(
    "/comments/{comment_id}",
    response_model=APIResponse[CommentResponse],
    summary="댓글 수정 (작성자/비회원 비밀번호/관리자)",
    responses=error_responses(400, 401, 403, 404, 422),
)
async def update_comment(
    comment_id: CommentId,
    body: UpdateCommentRequest,
    current_author: CurrentAuthor,
    current_role: CurrentRole,
    service: CommentServiceDep,
):
    requester_id = current_author.author_id if current_author else None
    comment = await service.update_comment(comment_id, body.content, requester_id, body.guest_password, current_role)
    return APIResponse.ok(data=CommentResponse.from_domain(comment), message="댓글이 수정되었습니다.")


@router.delete(
    "/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="댓글 삭제 (작성자/비회원 비밀번호/관리자, 소프트 삭제)",
    responses=error_responses(400, 401, 403, 404),
)
async def delete_comment(
    comment_id: CommentId,
    current_author: CurrentAuthor,
    current_role: CurrentRole,
    service: CommentServiceDep,
    body: Annotated[GuestPasswordRequest | None, Body()] = None,
):
    requester_id = current_author.author_id if current_author else None
    guest_password = body.guest_password if body else None
    await service.delete_comment(comment_id, requester_id, guest_password, current_role)
