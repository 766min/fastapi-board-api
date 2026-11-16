from typing import Annotated
from fastapi import APIRouter, Body, Depends, Path, Response, status

from board.application.service import PostService
from board.presentation.dependencies import CurrentAuthor, CurrentRole, build_author, provide_post_service
from board.presentation.schemas import (
    CreatePostRequest,
    GuestPasswordRequest,
    PostDetailResponse,
    PostListItemResponse,
    PostPageResponse,
    PostSearchQuery,
    UpdatePostRequest,
)
from common.schemas import APIResponse, PageResponse, error_responses

router = APIRouter(prefix="/v1", tags=["Posts"])

PostServiceDep = Annotated[PostService, Depends(provide_post_service)]
BoardId = Annotated[str, Path(min_length=2, max_length=30, description="게시판 ID", examples=["freetalk"])]
PostId = Annotated[int, Path(ge=1, description="게시글 ID")]


@router.post(
    "/boards/{board_id}/posts",
    response_model=APIResponse[PostDetailResponse],
    status_code=status.HTTP_201_CREATED,
    summary="게시글 작성 (회원/비회원)",
    description="로그인했다면 회원 글로, 토큰 없이 guest_name/guest_password 를 보내면 비회원 글로 등록됩니다.",
    responses=error_responses(401, 403, 404, 422),
)
async def write_post(
    board_id: BoardId,
    body: CreatePostRequest,
    current_author: CurrentAuthor,
    current_role: CurrentRole,
    service: PostServiceDep,
    response: Response,
):
    author, raw_password = build_author(current_author, body.guest_name, body.guest_password)
    post = await service.write_post(board_id, body.title, body.content, author, raw_password, current_role)
    response.headers["Location"] = f"/v1/posts/{post.post_id}"  # REST: 새로 만든 리소스 위치
    return APIResponse.ok(data=PostDetailResponse.from_domain(post), message="게시글이 등록되었습니다.")


@router.get(
    "/boards/{board_id}/posts",
    response_model=APIResponse[PostPageResponse],
    summary="게시글 목록 (페이지네이션·검색)",
    responses=error_responses(403, 404, 422),
)
async def list_posts(
    board_id: BoardId,
    query: Annotated[PostSearchQuery, Depends()],
    current_role: CurrentRole,
    service: PostServiceDep,
):
    posts, total_count, page_size = await service.list_posts(
        board_id, current_role, query.page, query.page_size, query.search_type, query.keyword
    )
    data = PostPageResponse(
        items=[PostListItemResponse.from_domain(p) for p in posts],
        total_count=total_count,
        page=query.page,
        page_size=page_size,
        total_pages=PageResponse.calc_total_pages(total_count, page_size),
        search_type=query.search_type,
        keyword=query.keyword,
    )
    return APIResponse.ok(data=data)


@router.get(
    "/posts/{post_id}",
    response_model=APIResponse[PostDetailResponse],
    summary="게시글 상세 조회",
    responses=error_responses(403, 404, 422),
)
async def get_post(post_id: PostId, current_role: CurrentRole, service: PostServiceDep):
    post = await service.get_post_detail(post_id, current_role)
    return APIResponse.ok(data=PostDetailResponse.from_domain(post))


@router.put(
    "/posts/{post_id}",
    response_model=APIResponse[PostDetailResponse],
    summary="게시글 수정 (작성자/비회원 비밀번호/관리자)",
    responses=error_responses(400, 401, 403, 404, 422),
)
async def update_post(
    post_id: PostId, body: UpdatePostRequest, current_author: CurrentAuthor, current_role: CurrentRole, service: PostServiceDep
):
    requester_id = current_author.author_id if current_author else None
    post = await service.update_post(post_id, body.title, body.content, requester_id, body.guest_password, current_role)
    return APIResponse.ok(data=PostDetailResponse.from_domain(post), message="게시글이 수정되었습니다.")


@router.delete(
    "/posts/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="게시글 삭제 (작성자/비회원 비밀번호/관리자, 소프트 삭제)",
    description="비회원 글은 요청 본문에 `{\"guest_password\": \"...\"}` 를 보내야 합니다.",
    responses=error_responses(400, 401, 403, 404),
)
async def delete_post(
    post_id: PostId,
    current_author: CurrentAuthor,
    current_role: CurrentRole,
    service: PostServiceDep,
    body: Annotated[GuestPasswordRequest | None, Body()] = None,
):
    requester_id = current_author.author_id if current_author else None
    guest_password = body.guest_password if body else None
    await service.delete_post(post_id, requester_id, guest_password, current_role)
