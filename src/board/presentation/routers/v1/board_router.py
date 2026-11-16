from typing import Annotated
from fastapi import APIRouter, Depends, Path, Query, status

from board.application.service import BoardService
from board.presentation.dependencies import AdminRole, provide_board_service
from board.presentation.schemas import BoardResponse, CreateBoardRequest, UpdateBoardRequest
from common.schemas import APIResponse, error_responses

router = APIRouter(prefix="/v1/boards", tags=["Boards"])

BoardServiceDep = Annotated[BoardService, Depends(provide_board_service)]
BoardId = Annotated[str, Path(min_length=2, max_length=30, description="게시판 ID", examples=["freetalk"])]


@router.post(
    "",
    response_model=APIResponse[BoardResponse],
    status_code=status.HTTP_201_CREATED,
    summary="게시판 생성 (관리자)",
    responses=error_responses(401, 403, 409, 422),
)
async def create_board(body: CreateBoardRequest, _: AdminRole, service: BoardServiceDep):
    board = await service.create_board(body.board_id, body.board_name, body.authority.to_domain(), body.page_size)
    return APIResponse.ok(data=BoardResponse.from_domain(board), message="게시판이 생성되었습니다.")


@router.get("", response_model=APIResponse[list[BoardResponse]], summary="게시판 목록 조회")
async def list_boards(
    service: BoardServiceDep,
    include_deleted: Annotated[bool, Query(description="삭제된 게시판 포함 여부")] = False,
):
    boards = await service.get_all_boards(include_deleted=include_deleted)
    return APIResponse.ok(data=[BoardResponse.from_domain(b) for b in boards])


@router.get("/{board_id}", response_model=APIResponse[BoardResponse], summary="게시판 상세 조회", responses=error_responses(404))
async def get_board(board_id: BoardId, service: BoardServiceDep):
    board = await service.get_board(board_id)
    return APIResponse.ok(data=BoardResponse.from_domain(board))


@router.put(
    "/{board_id}",
    response_model=APIResponse[BoardResponse],
    summary="게시판 설정 수정 (관리자)",
    responses=error_responses(400, 401, 403, 404, 422),
)
async def update_board(board_id: BoardId, body: UpdateBoardRequest, _: AdminRole, service: BoardServiceDep):
    authority = body.authority.to_domain() if body.authority else None
    board = await service.update_board_config(board_id, body.board_name, body.page_size, authority)
    return APIResponse.ok(data=BoardResponse.from_domain(board), message="게시판 설정이 수정되었습니다.")


@router.delete(
    "/{board_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="게시판 삭제 (관리자, 소프트 삭제)",
    responses=error_responses(401, 403, 404),
)
async def delete_board(board_id: BoardId, _: AdminRole, service: BoardServiceDep):
    await service.delete_board(board_id)
