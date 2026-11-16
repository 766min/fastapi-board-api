import os
from dotenv import load_dotenv

load_dotenv()


def _get_list(name: str, default: str) -> list[str]:
    """콤마(,)로 구분된 환경변수를 리스트로 변환"""
    return [value.strip() for value in os.getenv(name, default).split(",") if value.strip()]


class Settings:
    """환경변수를 한 곳에서 관리하는 설정 클래스"""

    # 데이터베이스
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/board"
    )
    SQL_ECHO: bool = os.getenv("SQL_ECHO", "false").lower() == "true"
    POOL_SIZE: int = int(os.getenv("CONNECTION_POOL_SIZE", "10"))
    MAX_OVERFLOW: int = int(os.getenv("CONNECTION_POOL_MAX_SIZE", "20"))

    # JWT
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
    JWT_ALGORITHM: str = "HS512"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

    # CORS
    CORS_ORIGINS: list[str] = _get_list("CORS_ORIGINS", "http://localhost:3000")

    # 파일 업로드
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "storage")
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "5"))

    # 캐시
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "60"))


settings = Settings()

# 비밀키가 없거나 너무 짧으면 서버를 아예 띄우지 않는다 (HS512는 64바이트 이상 권장)
if len(settings.JWT_SECRET_KEY) < 64:
    raise RuntimeError("JWT_SECRET_KEY 환경변수를 64자 이상의 랜덤 문자열로 설정하세요.")
