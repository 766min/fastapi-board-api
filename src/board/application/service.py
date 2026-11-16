import os
import uuid
from typing import AsyncIterator

from board.domain.board import Authority, Board
from board.domain.enums import PostSearchType, Role
from board.domain.post import Attachment, Author, BoardInfo, Comment, Post
from board.domain.repository.attachment_repository import AttachmentRepository
from board.domain.repository.board_repository import BoardRepository
from board.domain.repository.comment_repository import CommentRepository
from board.domain.repository.post_repository import PostRepository
from board.domain.service import FileStorage, PasswordHasher
from common.cache import Cache
from common.exception import ConflictException, ForbiddenException, NotFoundException


# ==================== 캐시 키 ====================
def _board_key(board_id: str) -> str:
    return f"boards:{board_id}"


def _post_detail_key(post_id: int) -> str:
    return f"posts:detail:{post_id}"


def _post_list_prefix(board_id: str) -> str:
    return f"posts:list:{board_id}:"


# ==================== 여러 서비스가 같이 쓰는 조회 헬퍼 ====================
async def load_active_board(board_repo: BoardRepository, cache: Cache, board_id: str) -> Board:
    """
    게시판 설정 조회 (캐시 사용)
    - 게시판 설정은 글/댓글 API 를 호출할 때마다 권한 확인용으로 읽지만, 거의 바뀌지 않는다 -> 캐싱 효과가 가장 큼
    """
    cached = await cache.get(_board_key(board_id))
    if cached is not None:
        return cached

    board = await board_repo.find_by_id(board_id)
    if board is None:
        raise NotFoundException("해당 게시판을 찾을 수 없거나 삭제되었습니다.", error_code="BOARD_NOT_FOUND")
    await cache.set(_board_key(board_id), board)
    return board


async def load_active_post(post_repo: PostRepository, post_id: int) -> Post:
    """게시글 조회 (DB 최신값) - 수정/삭제/권한 판단에 사용"""
    post = await post_repo.find_by_id(post_id)
    if post is None:
        raise NotFoundException("존재하지 않거나 삭제된 게시글입니다.", error_code="POST_NOT_FOUND")
    return post


# ==================== 게시판 설정 ====================
class BoardService:
    def __init__(self, board_repo: BoardRepository, cache: Cache):
        self._board_repo = board_repo
        self._cache = cache

    async def create_board(self, board_id: str, board_name: str, authority: Authority, page_size: int) -> Board:
        if await self._board_repo.exists_by_id(board_id.strip().lower()):
            raise ConflictException(f"이미 사용 중인 게시판 ID 입니다 ('{board_id}').", error_code="BOARD_ID_ALREADY_EXISTS")

        board = Board.create(board_id=board_id, board_name=board_name, authority=authority, page_size=page_size)
        return await self._board_repo.save(board)

    async def get_board(self, board_id: str) -> Board:
        return await load_active_board(self._board_repo, self._cache, board_id)

    async def get_all_boards(self, include_deleted: bool = False) -> list[Board]:
        return await self._board_repo.find_all(include_deleted=include_deleted)

    async def update_board_config(self, board_id: str, board_name: str, page_size: int, authority: Authority | None) -> Board:
        board = await self._get_board_from_db(board_id)  # 수정은 캐시가 아닌 DB 최신값 기준
        board.update_config(board_name=board_name, page_size=page_size, authority=authority)
        saved = await self._board_repo.save(board)
        await self._invalidate(board_id)
        return saved

    async def delete_board(self, board_id: str) -> None:
        board = await self._get_board_from_db(board_id)
        board.delete()
        await self._board_repo.save(board)
        await self._invalidate(board_id)

    async def _get_board_from_db(self, board_id: str) -> Board:
        board = await self._board_repo.find_by_id(board_id)
        if board is None:
            raise NotFoundException("해당 게시판을 찾을 수 없거나 삭제되었습니다.", error_code="BOARD_NOT_FOUND")
        return board

    async def _invalidate(self, board_id: str) -> None:
        await self._cache.delete(_board_key(board_id))
        await self._cache.delete_prefix(_post_list_prefix(board_id))


# ==================== 게시글 ====================
class PostService:
    def __init__(self, post_repo: PostRepository, board_repo: BoardRepository, password_hasher: PasswordHasher, cache: Cache):
        self._post_repo = post_repo
        self._board_repo = board_repo
        self._hasher = password_hasher
        self._cache = cache

    async def write_post(
        self,
        board_id: str,
        title: str,
        content: str,
        author: Author,
        raw_guest_password: str | None,
        user_role: Role | None,
    ) -> Post:
        board = await load_active_board(self._board_repo, self._cache, board_id)
        if not board.authority.can_edit(user_role):
            raise ForbiddenException("해당 게시판에 글을 작성할 권한이 없습니다.", error_code="BOARD_PERMISSION_DENIED")

        post = Post.create(
            board_info=BoardInfo(board_id=board.board_id, board_name=board.board_name),
            title=title,
            content=content,
            author=author,
            raw_guest_password=raw_guest_password,
            hasher=self._hasher,
        )
        saved = await self._post_repo.save(post)
        await self._cache.delete_prefix(_post_list_prefix(board.board_id))
        return saved

    async def get_post_detail(self, post_id: int, user_role: Role | None) -> Post:
        post = await self._cache.get(_post_detail_key(post_id))
        if post is None:
            post = await load_active_post(self._post_repo, post_id)
            await self._cache.set(_post_detail_key(post_id), post)

        # 캐시에서 꺼냈더라도 권한 확인은 요청마다 반드시 한다
        board = await load_active_board(self._board_repo, self._cache, post.board_info.board_id)
        if not board.authority.can_view(user_role):
            raise ForbiddenException("게시글 상세 열람 권한이 없습니다.", error_code="BOARD_PERMISSION_DENIED")
        return post

    async def list_posts(
        self,
        board_id: str,
        user_role: Role | None,
        page: int,
        page_size: int | None,
        search_type: PostSearchType,
        keyword: str | None,
    ) -> tuple[list[Post], int, int]:
        """(게시글 목록, 전체 개수, 실제 적용된 페이지 크기) 반환"""
        board = await load_active_board(self._board_repo, self._cache, board_id)
        if not board.authority.can_list(user_role):
            raise ForbiddenException("게시글 목록 열람 권한이 없습니다.", error_code="BOARD_PERMISSION_DENIED")

        size = page_size or board.page_size  # 요청에 없으면 게시판 설정값 사용
        keyword = keyword.strip() if keyword else None
        cache_key = f"{_post_list_prefix(board.board_id)}{page}:{size}:{search_type}:{keyword or ''}"
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return cached

        offset = (page - 1) * size
        posts = await self._post_repo.find_by_board_id(board.board_id, size, offset, search_type, keyword)
        total_count = await self._post_repo.count_by_board_id(board.board_id, search_type, keyword)
        result = (posts, total_count, size)
        await self._cache.set(cache_key, result)
        return result

    async def update_post(
        self,
        post_id: int,
        title: str,
        content: str,
        requester_id: uuid.UUID | None,
        guest_password: str | None,
        user_role: Role | None,
    ) -> Post:
        post = await self._get_modifiable_post(post_id, requester_id, guest_password, user_role)
        post.update_content(title=title, content=content)
        saved = await self._post_repo.save(post)
        await self._invalidate(post)
        return saved

    async def delete_post(
        self, post_id: int, requester_id: uuid.UUID | None, guest_password: str | None, user_role: Role | None
    ) -> None:
        post = await self._get_modifiable_post(post_id, requester_id, guest_password, user_role)
        post.delete()
        await self._post_repo.save(post)
        await self._invalidate(post)

    async def _get_modifiable_post(
        self, post_id: int, requester_id: uuid.UUID | None, guest_password: str | None, user_role: Role | None
    ) -> Post:
        post = await load_active_post(self._post_repo, post_id)
        board = await load_active_board(self._board_repo, self._cache, post.board_info.board_id)
        if not board.authority.can_edit(user_role):
            raise ForbiddenException("해당 게시판의 글을 수정/삭제할 권한이 없습니다.", error_code="BOARD_PERMISSION_DENIED")
        if not post.can_modify_or_delete(requester_id, user_role, guest_password, self._hasher):
            raise ForbiddenException("작성자 본인이 아니거나 비밀번호가 일치하지 않습니다.", error_code="POST_PERMISSION_DENIED")
        return post

    async def _invalidate(self, post: Post) -> None:
        await self._cache.delete(_post_detail_key(post.post_id))
        await self._cache.delete_prefix(_post_list_prefix(post.board_info.board_id))


# ==================== 댓글 ====================
class CommentService:
    def __init__(
        self,
        comment_repo: CommentRepository,
        post_repo: PostRepository,
        board_repo: BoardRepository,
        password_hasher: PasswordHasher,
        cache: Cache,
    ):
        self._comment_repo = comment_repo
        self._post_repo = post_repo
        self._board_repo = board_repo
        self._hasher = password_hasher
        self._cache = cache

    async def write_comment(
        self, post_id: int, content: str, author: Author, raw_guest_password: str | None, user_role: Role | None
    ) -> Comment:
        await self._check_board_permission(post_id, user_role, for_edit=True)
        comment = Comment.create(
            post_id=post_id, content=content, author=author, raw_guest_password=raw_guest_password, hasher=self._hasher
        )
        return await self._comment_repo.save(comment)

    async def list_comments(self, post_id: int, user_role: Role | None) -> list[Comment]:
        await self._check_board_permission(post_id, user_role, for_edit=False)
        return await self._comment_repo.find_by_post_id(post_id)

    async def update_comment(
        self, comment_id: int, content: str, requester_id: uuid.UUID | None, guest_password: str | None, user_role: Role | None
    ) -> Comment:
        comment = await self._get_modifiable_comment(comment_id, requester_id, guest_password, user_role)
        comment.update_content(content=content)
        return await self._comment_repo.save(comment)

    async def delete_comment(
        self, comment_id: int, requester_id: uuid.UUID | None, guest_password: str | None, user_role: Role | None
    ) -> None:
        comment = await self._get_modifiable_comment(comment_id, requester_id, guest_password, user_role)
        comment.delete()
        await self._comment_repo.save(comment)

    async def _check_board_permission(self, post_id: int, user_role: Role | None, for_edit: bool) -> None:
        post = await load_active_post(self._post_repo, post_id)
        board = await load_active_board(self._board_repo, self._cache, post.board_info.board_id)
        allowed = board.authority.can_edit_comments(user_role) if for_edit else board.authority.can_view_comments(user_role)
        if not allowed:
            raise ForbiddenException("해당 게시판의 댓글 권한이 없습니다.", error_code="BOARD_PERMISSION_DENIED")

    async def _get_modifiable_comment(
        self, comment_id: int, requester_id: uuid.UUID | None, guest_password: str | None, user_role: Role | None
    ) -> Comment:
        comment = await self._comment_repo.find_by_id(comment_id)
        if comment is None:
            raise NotFoundException("존재하지 않거나 삭제된 댓글입니다.", error_code="COMMENT_NOT_FOUND")
        await self._check_board_permission(comment.post_id, user_role, for_edit=True)
        if not comment.can_modify_or_delete(requester_id, user_role, guest_password, self._hasher):
            raise ForbiddenException("작성자 본인이 아니거나 비밀번호가 일치하지 않습니다.", error_code="COMMENT_PERMISSION_DENIED")
        return comment


# ==================== 첨부파일 ====================
class AttachmentService:
    def __init__(
        self,
        attachment_repo: AttachmentRepository,
        post_repo: PostRepository,
        board_repo: BoardRepository,
        file_storage: FileStorage,
        cache: Cache,
        max_upload_bytes: int,
    ):
        self._attachment_repo = attachment_repo
        self._post_repo = post_repo
        self._board_repo = board_repo
        self._file_storage = file_storage
        self._cache = cache
        self._max_upload_bytes = max_upload_bytes

    async def upload(
        self,
        post_id: int,
        requester_id: uuid.UUID | None,
        user_role: Role | None,
        filename: str,
        content_type: str | None,
        chunks: AsyncIterator[bytes],
    ) -> Attachment:
        post = await load_active_post(self._post_repo, post_id)
        if not post.can_manage_attachments(requester_id, user_role):
            raise ForbiddenException("게시글 작성자(회원) 또는 관리자만 파일을 올릴 수 있습니다.", error_code="ATTACHMENT_PERMISSION_DENIED")
        extension = Attachment.extract_extension(filename)

        stored_name, size = await self._file_storage.save(chunks, extension, self._max_upload_bytes)
        attachment = Attachment(
            post_id=post_id,
            original_name=os.path.basename(filename),
            stored_name=stored_name,
            content_type=content_type,
            size=size,
        )
        try:
            saved = await self._attachment_repo.save(attachment)
        except Exception:
            await self._file_storage.delete(stored_name)  # DB 저장 실패 시 디스크에 남은 파일 정리
            raise

        await self._cache.delete(_post_detail_key(post_id))
        return saved

    async def get_file(self, attachment_id: int, user_role: Role | None) -> tuple[Attachment, AsyncIterator[bytes]]:
        attachment = await self._get_attachment(attachment_id)
        post = await load_active_post(self._post_repo, attachment.post_id)  # 삭제된 글의 파일은 다운로드 불가
        board = await load_active_board(self._board_repo, self._cache, post.board_info.board_id)
        if not board.authority.can_view(user_role):
            raise ForbiddenException("게시글 열람 권한이 없습니다.", error_code="BOARD_PERMISSION_DENIED")
        if not self._file_storage.exists(attachment.stored_name):
            raise NotFoundException("파일이 서버에 존재하지 않습니다.", error_code="FILE_NOT_FOUND")
        return attachment, self._file_storage.open(attachment.stored_name)

    async def delete(self, attachment_id: int, requester_id: uuid.UUID | None, user_role: Role | None) -> None:
        attachment = await self._get_attachment(attachment_id)
        post = await load_active_post(self._post_repo, attachment.post_id)
        if not post.can_manage_attachments(requester_id, user_role):
            raise ForbiddenException("게시글 작성자(회원) 또는 관리자만 파일을 삭제할 수 있습니다.", error_code="ATTACHMENT_PERMISSION_DENIED")
        await self._attachment_repo.delete(attachment_id)
        await self._file_storage.delete(attachment.stored_name)
        await self._cache.delete(_post_detail_key(attachment.post_id))

    async def _get_attachment(self, attachment_id: int) -> Attachment:
        attachment = await self._attachment_repo.find_by_id(attachment_id)
        if attachment is None:
            raise NotFoundException("첨부파일을 찾을 수 없습니다.", error_code="ATTACHMENT_NOT_FOUND")
        return attachment
