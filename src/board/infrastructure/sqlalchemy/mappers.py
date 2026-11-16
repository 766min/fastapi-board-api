from board.domain.board import Authority, Board
from board.domain.enums import Role
from board.domain.post import Attachment, Author, BoardInfo, Comment, GuestPassword, Post
from board.infrastructure.sqlalchemy.models import AttachmentModel, BoardModel, CommentModel, PostModel

"""
도메인 엔티티 <-> ORM 모델 변환기
- 엔티티는 DB 를 모르고, 모델은 비즈니스 규칙을 모른다. 둘 사이 변환을 여기 한 곳에 모은다.
- to_model() 에는 created_at 등을 넘기지 않는다. (None 을 넘기면 DB 기본값 대신 NULL 이 들어가려 한다)
"""


def _guest_password(hashed: str | None) -> GuestPassword | None:
    return GuestPassword(hashed_value=hashed) if hashed else None


class BoardMapper:
    @staticmethod
    def to_domain(model: BoardModel) -> Board:
        return Board(
            board_id=model.board_id,
            board_name=model.board_name,
            authority=Authority(
                edit_role=Role(model.edit_role),
                view_role=Role(model.view_role),
                list_role=Role(model.list_role),
                comment_list_role=Role(model.comment_list_role),
                comment_edit_role=Role(model.comment_edit_role),
            ),
            page_size=model.page_size,
            created_at=model.created_at,
            modified_at=model.modified_at,
            deleted_at=model.deleted_at,
        )

    @staticmethod
    def to_model(domain: Board) -> BoardModel:
        return BoardModel(
            board_id=domain.board_id,
            board_name=domain.board_name,
            page_size=domain.page_size,
            edit_role=domain.authority.edit_role.value,
            view_role=domain.authority.view_role.value,
            list_role=domain.authority.list_role.value,
            comment_list_role=domain.authority.comment_list_role.value,
            comment_edit_role=domain.authority.comment_edit_role.value,
        )


class AttachmentMapper:
    @staticmethod
    def to_domain(model: AttachmentModel) -> Attachment:
        return Attachment(
            attachment_id=model.attachment_id,
            post_id=model.post_id,
            original_name=model.original_name,
            stored_name=model.stored_name,
            content_type=model.content_type,
            size=model.size,
            created_at=model.created_at,
        )

    @staticmethod
    def to_model(domain: Attachment) -> AttachmentModel:
        return AttachmentModel(
            post_id=domain.post_id,
            original_name=domain.original_name,
            stored_name=domain.stored_name,
            content_type=domain.content_type,
            size=domain.size,
        )


class PostMapper:
    @staticmethod
    def to_domain(model: PostModel) -> Post:
        return Post(
            post_id=model.post_id,
            board_info=BoardInfo(board_id=model.board_id, board_name=model.board.board_name),
            title=model.title,
            content=model.content,
            author=Author(author_name=model.author_name, author_id=model.author_id),
            guest_password=_guest_password(model.guest_password),
            created_at=model.created_at,
            modified_at=model.modified_at,
            deleted_at=model.deleted_at,
            attachments=[AttachmentMapper.to_domain(a) for a in model.attachments],
        )

    @staticmethod
    def to_model(domain: Post) -> PostModel:
        return PostModel(
            board_id=domain.board_info.board_id,
            title=domain.title,
            content=domain.content,
            author_name=domain.author.author_name,
            author_id=domain.author.author_id,
            guest_password=domain.guest_password.hashed_value if domain.guest_password else None,
        )


class CommentMapper:
    @staticmethod
    def to_domain(model: CommentModel) -> Comment:
        return Comment(
            comment_id=model.comment_id,
            post_id=model.post_id,
            content=model.content,
            author=Author(author_name=model.author_name, author_id=model.author_id),
            guest_password=_guest_password(model.guest_password),
            created_at=model.created_at,
            modified_at=model.modified_at,
            deleted_at=model.deleted_at,
        )

    @staticmethod
    def to_model(domain: Comment) -> CommentModel:
        return CommentModel(
            post_id=domain.post_id,
            content=domain.content,
            author_name=domain.author.author_name,
            author_id=domain.author.author_id,
            guest_password=domain.guest_password.hashed_value if domain.guest_password else None,
        )
