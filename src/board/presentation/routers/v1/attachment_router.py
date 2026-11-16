from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Path, UploadFile, status
from fastapi.responses import StreamingResponse

from board.application.service import AttachmentService
from board.presentation.dependencies import CurrentAuthor, CurrentRole, provide_attachment_service
from board.presentation.schemas import AttachmentResponse
from common.schemas import APIResponse, error_responses

router = APIRouter(prefix="/v1", tags=["Attachments"])

AttachmentServiceDep = Annotated[AttachmentService, Depends(provide_attachment_service)]
PostId = Annotated[int, Path(ge=1, description="게시글 ID")]
AttachmentId = Annotated[int, Path(ge=1, description="첨부파일 ID")]


@router.post(
    "/posts/{post_id}/attachments",
    response_model=APIResponse[AttachmentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="첨부파일 업로드 (회원 작성자/관리자)",
    description="multipart/form-data 로 파일 1개를 업로드합니다. 허용 확장자: jpg, jpeg, png, gif, pdf, txt, zip",
    responses=error_responses(400, 401, 403, 404, 422),
)
async def upload_attachment(
    post_id: PostId,
    file: Annotated[UploadFile, File(description="업로드할 파일")],
    current_author: CurrentAuthor,
    current_role: CurrentRole,
    service: AttachmentServiceDep,
):
    async def read_chunks():
        while chunk := await file.read(1024 * 1024):  # 1MB 씩 읽기
            yield chunk

    requester_id = current_author.author_id if current_author else None
    try:
        attachment = await service.upload(
            post_id, requester_id, current_role, file.filename or "", file.content_type, read_chunks()
        )
    finally:
        await file.close()
    return APIResponse.ok(data=AttachmentResponse.from_domain(attachment), message="파일이 업로드되었습니다.")


@router.get(
    "/attachments/{attachment_id}",
    response_class=StreamingResponse,
    summary="첨부파일 다운로드",
    responses={200: {"content": {"application/octet-stream": {}}, "description": "파일 데이터"}, **error_responses(403, 404)},
)
async def download_attachment(attachment_id: AttachmentId, current_role: CurrentRole, service: AttachmentServiceDep):
    attachment, stream = await service.get_file(attachment_id, current_role)
    return StreamingResponse(
        stream,
        media_type=attachment.content_type or "application/octet-stream",
        # 한글 파일명이 깨지지 않도록 RFC 5987 방식으로 인코딩
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(attachment.original_name)}"},
    )


@router.delete(
    "/attachments/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="첨부파일 삭제 (회원 작성자/관리자)",
    responses=error_responses(401, 403, 404),
)
async def delete_attachment(
    attachment_id: AttachmentId, current_author: CurrentAuthor, current_role: CurrentRole, service: AttachmentServiceDep
):
    requester_id = current_author.author_id if current_author else None
    await service.delete(attachment_id, requester_id, current_role)
