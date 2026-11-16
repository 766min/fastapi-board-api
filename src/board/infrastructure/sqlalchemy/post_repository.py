from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from board.domain.enums import PostSearchType
from board.domain.post import Post
from board.domain.repository.post_repository import PostRepository
from board.infrastructure.sqlalchemy.mappers import PostMapper
from board.infrastructure.sqlalchemy.models import PostModel
from user.infrastructure.models import UserModel


class SqlAlchemyPostRepository(PostRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _apply_search(self, stmt: Select, search_type: PostSearchType, keyword: str | None) -> Select:
        """검색 조건을 쿼리에 붙인다 (keyword 가 없으면 그대로)"""
        if not keyword:
            return stmt

        # autoescape=True : 검색어에 들어있는 % _ 를 와일드카드가 아닌 일반 글자로 취급
        title = PostModel.title.icontains(keyword, autoescape=True)
        content = PostModel.content.icontains(keyword, autoescape=True)
        author_name = PostModel.author_name.icontains(keyword, autoescape=True)
        author_email = UserModel.email.icontains(keyword, autoescape=True)

        # 이메일은 users 테이블에 있으므로 필요할 때만 JOIN (비회원 글도 나와야 하므로 OUTER JOIN)
        if search_type in (PostSearchType.ALL, PostSearchType.AUTHOR_EMAIL):
            stmt = stmt.outerjoin(UserModel, PostModel.author_id == UserModel.id)

        condition = {
            PostSearchType.TITLE: title,
            PostSearchType.CONTENT: content,
            PostSearchType.TITLE_CONTENT: or_(title, content),
            PostSearchType.AUTHOR_NAME: author_name,
            PostSearchType.AUTHOR_EMAIL: author_email,
            PostSearchType.ALL: or_(title, content, author_name, author_email),
        }[search_type]
        return stmt.where(condition)

    async def find_by_id(self, post_id: int) -> Post | None:
        stmt = select(PostModel).where(PostModel.post_id == post_id, PostModel.deleted_at.is_(None))
        model = await self.session.scalar(stmt)
        return PostMapper.to_domain(model) if model else None

    async def find_by_board_id(
        self, board_id: str, limit: int, offset: int, search_type: PostSearchType, keyword: str | None
    ) -> list[Post]:
        stmt = select(PostModel).where(PostModel.board_id == board_id, PostModel.deleted_at.is_(None))
        stmt = self._apply_search(stmt, search_type, keyword)
        stmt = stmt.order_by(PostModel.post_id.desc()).offset(offset).limit(limit)
        models = await self.session.scalars(stmt)
        return [PostMapper.to_domain(m) for m in models]

    async def count_by_board_id(self, board_id: str, search_type: PostSearchType, keyword: str | None) -> int:
        stmt = select(func.count(PostModel.post_id)).where(PostModel.board_id == board_id, PostModel.deleted_at.is_(None))
        stmt = self._apply_search(stmt, search_type, keyword)
        return await self.session.scalar(stmt) or 0

    async def save(self, post: Post) -> Post:
        if post.post_id:  # 수정 / 소프트 삭제
            model = await self.session.get(PostModel, post.post_id)
            model.title = post.title
            model.content = post.content
            model.modified_at = post.modified_at
            model.deleted_at = post.deleted_at
        else:  # 등록
            model = PostMapper.to_model(post)
            self.session.add(model)

        await self.session.flush()
        # 게시판(joined)·첨부파일(selectin)까지 DB 최신 상태로 다시 읽어온다
        stmt = select(PostModel).where(PostModel.post_id == model.post_id).execution_options(populate_existing=True)
        model = await self.session.scalar(stmt)
        return PostMapper.to_domain(model)
