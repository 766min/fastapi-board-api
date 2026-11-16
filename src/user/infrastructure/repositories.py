import uuid
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from common.exception import ConflictException, NotFoundException
from user.domain.repository import UserRepository
from user.domain.user import User
from user.infrastructure.models import UserModel


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_id(self, user_id: uuid.UUID) -> User | None:
        model = await self.session.get(UserModel, user_id)
        return model.to_user() if model else None

    async def find_by_email(self, email: str) -> User | None:
        model = await self.session.scalar(select(UserModel).where(UserModel.email == email))
        return model.to_user() if model else None

    async def save(self, user: User) -> User:
        if user.id is None:
            # 신규 회원 등록 (INSERT)
            model = UserModel(
                email=user.email,
                name=user.name,
                password_hash=user.password_hash,
                role=user.role,
                resign=user.resign,
            )
            self.session.add(model)
        else:
            # 기존 회원 수정 (UPDATE)
            model = await self.session.get(UserModel, user.id)
            if model is None:
                raise NotFoundException("사용자를 찾을 수 없습니다.", error_code="USER_NOT_FOUND")
            model.name = user.name
            model.password_hash = user.password_hash
            model.resign = user.resign
            model.deleted_at = user.deleted_at

        try:
            await self.session.flush()  # SQL 을 DB 로 보냄 (commit 은 get_db 가 요청 끝에 한 번)
        except IntegrityError:
            # 동시에 같은 이메일로 가입 요청이 들어온 경우 (DB unique 제약 위반)
            raise ConflictException("이미 사용 중인 이메일입니다.", error_code="EMAIL_ALREADY_EXISTS")

        await self.session.refresh(model)  # DB 가 채운 created_at 등을 다시 읽어온다
        return model.to_user()
