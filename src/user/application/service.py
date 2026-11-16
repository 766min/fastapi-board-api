from common.exception import ConflictException
from user.domain.repository import UserRepository
from user.domain.service import PasswordHasher
from user.domain.user import User


class UserService:
    def __init__(self, repository: UserRepository, hasher: PasswordHasher):
        self.repository = repository
        self.hasher = hasher

    async def register_user(self, email: str, name: str, password: str) -> User:
        if await self.repository.find_by_email(email):
            raise ConflictException("이미 사용 중인 이메일입니다.", error_code="EMAIL_ALREADY_EXISTS")

        # 검증 실패(ValidationException)는 그대로 422 로 나가야 하므로 try/except 로 감싸지 않는다
        user = User.create(email=email, name=name, raw_password=password, hasher=self.hasher)
        return await self.repository.save(user)

    async def change_password(self, user: User, old_password: str, new_password: str) -> None:
        user.change_password(old_password=old_password, new_password=new_password, hasher=self.hasher)
        await self.repository.save(user)

    async def withdraw(self, target: User, requester: User) -> None:
        target.withdraw(requester)
        await self.repository.save(target)
