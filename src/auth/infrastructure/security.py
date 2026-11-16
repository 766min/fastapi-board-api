import uuid
from datetime import datetime, timedelta, timezone
import jwt

from auth.domain.entities import TokenPayload
from auth.domain.service import TokenProvider
from common.config import settings
from common.exception import UnauthorizedException


class JwtTokenProvider(TokenProvider):
    def __init__(
        self,
        secret_key: str = settings.JWT_SECRET_KEY,
        algorithm: str = settings.JWT_ALGORITHM,
        expire_minutes: int = settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    ):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.expire_minutes = expire_minutes

    def create_access_token(self, user_id: uuid.UUID) -> tuple[str, str, datetime, int]:
        now = datetime.now(timezone.utc)
        expires_delta = timedelta(minutes=self.expire_minutes)
        expired_at = now + expires_delta
        jti = str(uuid.uuid4())

        payload = {"sub": str(user_id), "jti": jti, "iat": now, "exp": expired_at}
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token, jti, expired_at, int(expires_delta.total_seconds())

    def decode_token(self, token: str) -> TokenPayload:
        try:
            # 서명 검증 + exp(만료) 검증을 PyJWT 가 자동으로 해준다
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"require": ["sub", "jti", "exp"]},
            )
            return TokenPayload(
                user_id=uuid.UUID(payload["sub"]),
                jti=payload["jti"],
                exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
            )
        except jwt.ExpiredSignatureError:
            raise UnauthorizedException("토큰이 만료되었습니다. 다시 로그인해주세요.", error_code="TOKEN_EXPIRED")
        except (jwt.PyJWTError, ValueError):
            raise UnauthorizedException("유효하지 않은 토큰입니다.", error_code="INVALID_TOKEN")
