# 📘 RESTful 게시판 API 과제 가이드

> **튜터님 최신 코드(`yonggyo1125/backend_project_ax1`)의 구조를 바탕으로**, 채점 기준에 필요한 기능(첨부파일·캐싱·미들웨어·에러 응답 통일)과 버그 수정을 더한 버전입니다.
>
> **4계층 구조 · wiring 의존성 주입 · 게시판 설정/권한 · 회원/비회원/관리자 · 소프트 삭제 · JWT(HS512) + 블랙리스트 · 요청 단위 트랜잭션**
>
> 이 문서의 코드는 미리 전부 실행해서 **93개 동작 시나리오**(회원/비회원/관리자 권한, 게시판별 권한, 검색, 페이지네이션, 첨부파일, 캐시 무효화, 로그아웃, 탈퇴, 토큰 만료 등)를 확인했습니다.
> 위에서부터 순서대로 따라 치시면 됩니다. 각 단계 끝의 **✅ 단계 결론**만 읽어도 흐름을 잡을 수 있습니다.

---

## 목차

0. [완성하면 어떤 모습인가요?](#0-완성하면-어떤-모습인가요)
1. [개발 환경 준비](#1-개발-환경-준비)
2. [common — 공통 부품](#2-common--공통-부품)
3. [user — 회원](#3-user--회원)
4. [auth — 로그인/로그아웃(JWT)](#4-auth--로그인로그아웃jwt)
5. [board — 게시판·게시글·댓글·첨부파일](#5-board--게시판게시글댓글첨부파일)
6. [wiring과 main.py — 조립하고 실행하기](#6-wiring과-mainpy--조립하고-실행하기)
7. [Swagger로 직접 테스트하기](#7-swagger로-직접-테스트하기)
8. [튜터님 코드와 달라진 점](#8-튜터님-코드와-달라진-점)
9. [GitHub에 올리기](#9-github에-올리기)
10. [AWS EC2에 배포하기](#10-aws-ec2에-배포하기)
11. [제출 전 체크리스트](#11-제출-전-체크리스트)

---

## 0. 완성하면 어떤 모습인가요?

### 0-1. API 목록

**권한 표기**: 👤 비회원 가능 · 🔑 로그인 필요 · 👑 관리자 · ✍️ 작성자 본인(비회원 글은 비밀번호) 또는 관리자 · 📋 게시판 권한 설정에 따름

| 기능 | 메서드 | URL | 권한 |
|---|---|---|---|
| 회원가입 | POST | `/v1/users` | 👤 |
| 내 정보 | GET | `/v1/users/me` | 🔑 |
| 비밀번호 변경 | PATCH | `/v1/users/me/password` | 🔑 |
| 회원 탈퇴 | DELETE | `/v1/users/me` | 🔑 |
| 로그인 | POST | `/v1/auth/login` | 👤 |
| 로그아웃 | POST | `/v1/auth/logout` | 🔑 |
| 게시판 생성 | POST | `/v1/boards` | 👑 |
| 게시판 목록 | GET | `/v1/boards` | 👤 |
| 게시판 상세 | GET | `/v1/boards/{board_id}` | 👤 |
| 게시판 설정 수정 | PUT | `/v1/boards/{board_id}` | 👑 |
| 게시판 삭제 | DELETE | `/v1/boards/{board_id}` | 👑 |
| 게시글 작성 | POST | `/v1/boards/{board_id}/posts` | 📋 (회원 또는 비회원) |
| 게시글 목록·검색 | GET | `/v1/boards/{board_id}/posts?page=&page_size=&search_type=&keyword=` | 📋 |
| 게시글 상세 | GET | `/v1/posts/{post_id}` | 📋 |
| 게시글 수정 | PUT | `/v1/posts/{post_id}` | 📋 + ✍️ |
| 게시글 삭제 | DELETE | `/v1/posts/{post_id}` | 📋 + ✍️ |
| 댓글 작성 | POST | `/v1/posts/{post_id}/comments` | 📋 (회원 또는 비회원) |
| 댓글 목록 | GET | `/v1/posts/{post_id}/comments` | 📋 |
| 댓글 수정 | PUT | `/v1/comments/{comment_id}` | 📋 + ✍️ |
| 댓글 삭제 | DELETE | `/v1/comments/{comment_id}` | 📋 + ✍️ |
| 첨부파일 업로드 | POST | `/v1/posts/{post_id}/attachments` | 회원 작성자 또는 👑 |
| 첨부파일 다운로드 | GET | `/v1/attachments/{attachment_id}` | 📋 |
| 첨부파일 삭제 | DELETE | `/v1/attachments/{attachment_id}` | 회원 작성자 또는 👑 |
| 서버 상태 | GET | `/health` | 👤 |

**REST 원칙 포인트**
- URL은 **명사(리소스)**, 행동은 **HTTP 메서드**로 표현합니다. (`/createPost` ✕ → `POST /boards/freetalk/posts` ○)
- "어디에 만드는지"가 중요한 생성은 **부모 아래**(`/boards/{id}/posts`), 이미 ID가 있는 리소스는 **짧게**(`/posts/{id}`, `/comments/{id}`) 접근합니다. (튜터님 방식)
- 상태코드: 생성 `201`(+ `Location` 헤더), 삭제 `204`(본문 없음), 검증 실패 `422`, 인증 실패 `401`, 권한 없음 `403`, 없음 `404`, 중복 `409`.
- 수정은 튜터님 코드처럼 `PUT`(제목·내용을 모두 보냄)을 사용합니다.

### 0-2. 모든 응답은 같은 모양입니다

```json
// 성공
{ "success": true,  "code": "OK", "message": "게시글이 등록되었습니다.", "errors": null, "data": { ... }, "responded_at": "..." }

// 실패 (어떤 에러든 이 모양)
{ "success": false, "code": "GUEST_INFO_REQUIRED", "message": "비회원 작성 정보가 부족합니다.",
  "errors": { "guest_password": ["비회원은 비밀번호(6자 이상)를 입력해야 합니다."] }, "data": null, "responded_at": "..." }
```

### 0-3. 채점 기준과 구현 내용 연결표

| 채점 항목 | 이 가이드에서 해당하는 부분 |
|---|---|
| RESTful 엔드포인트 | 위 API 표, 상태코드·`Location` 헤더, 경로/쿼리/본문 매개변수 검증, Swagger 요약·설명·에러 응답 문서화 |
| Pydantic 검증·직렬화 | 요청/응답 스키마 분리, `field_validator` 커스텀 검증, `pattern`, 쿼리 파라미터 모델, 422 에러를 공통 스키마로 변환 |
| SQLAlchemy ORM | boards–posts–comments–attachments 관계, `joined`/`selectin`으로 N+1 방지, 복합 인덱스, 소프트 삭제, 매퍼 분리, 요청 단위 트랜잭션 |
| 인증·인가 | bcrypt 해싱(회원·비회원 비밀번호), JWT 만료(`exp`), jti 블랙리스트 로그아웃, 게시판별 권한(ALL/USER/ADMIN), 작성자/비밀번호/관리자 검사, 탈퇴 회원 차단 |
| 운영 환경 | 비동기 DB·파일 처리, 파일 업로드/스트리밍 다운로드, TTL 캐싱, 로깅·CORS 미들웨어, 전역 예외 처리, `/health`, Docker + EC2 배포 |

### 0-4. 4계층 구조 한눈에 보기

| 비유 | 실제 계층(폴더) | 하는 일 | 이 프로젝트 예시 |
|---|---|---|---|
| 홀 직원 (주문 받고 음식 전달) | **presentation** | HTTP 요청/응답, 입력 형식 검사 | `routers/`, `schemas.py`, `dependencies.py` |
| 주방장 (조리 순서 지휘) | **application** | 여러 부품을 순서대로 불러 하나의 기능 완성 | `PostService.update_post()` |
| 레시피·규칙 | **domain** | "비회원 글은 비밀번호가 맞아야 수정" 같은 핵심 규칙, 인터페이스(ABC) | `Post.can_modify_or_delete()`, `Authority` |
| 창고·주방 설비 | **infrastructure** | DB, 파일, JWT, bcrypt 같은 실제 기술 구현 | `SqlAlchemyPostRepository`, `LocalFileStorage` |
| 식당 매니저 (직원 배치) | **wiring/** | 인터페이스에 실제 구현체를 끼워 넣음 (의존성 주입) | `wire_dependencies()` |

> 의존 방향은 항상 **presentation → application → domain ← infrastructure** 입니다.
> domain은 FastAPI·SQLAlchemy를 전혀 모릅니다. 그래서 DB를 바꿔도 규칙 코드는 그대로 둘 수 있습니다.

### 0-5. 최종 폴더 구조

```
backend-api/
├── pyproject.toml / uv.lock
├── .env / .env.example
├── .gitignore / .dockerignore
├── Dockerfile / docker-compose.yml
├── storage/                    ← 업로드 파일 (자동 생성, Git 제외)
└── src/
    ├── main.py
    ├── wiring/                 ← 의존성 조립 (튜터님 구조)
    │   ├── __init__.py  user.py  auth.py  board.py
    ├── common/
    │   ├── config.py  logger.py  database.py  models.py
    │   ├── exception.py  exception_handlers.py  schemas.py
    │   └── middlewares.py  cache.py
    ├── user/
    │   ├── domain/          user.py  repository.py  service.py
    │   ├── application/     service.py
    │   ├── infrastructure/  models.py  repositories.py  security.py
    │   └── presentation/    schemas.py  dependencies.py  routers/v1/router.py
    ├── auth/
    │   ├── domain/          entities.py  repository.py  service.py
    │   ├── application/     service.py
    │   ├── infrastructure/  models.py  repositories.py  security.py  credentials_verifier.py
    │   └── presentation/    schemas.py  dependencies.py  routers/v1/router.py
    └── board/
        ├── domain/          enums.py  board.py  post.py  service.py
        │   └── repository/  board_repository.py  post_repository.py  comment_repository.py  attachment_repository.py
        ├── application/     service.py
        ├── infrastructure/  security.py  file_storage.py
        │   └── sqlalchemy/  models.py  mappers.py  seed.py
        │                    board_repository.py  post_repository.py  comment_repository.py  attachment_repository.py
        └── presentation/    schemas.py  dependencies.py
            └── routers/v1/  board_router.py  post_router.py  comment_router.py  attachment_router.py
```

`wiring/__init__.py`만 내용이 있고, 나머지 폴더는 수업처럼 `__init__.py` 없이 진행합니다.

---

## 1. 개발 환경 준비

### 1-1. uv 프로젝트 만들기

`backend-api` 폴더에서 실행합니다.

```bash
uv init --bare --python 3.13
```

```bash
uv add fastapi uvicorn asyncpg "sqlalchemy[asyncio]" bcrypt pyjwt "pydantic[email]" python-dotenv aiofiles python-multipart
```

| 패키지 | 용도 |
|---|---|
| fastapi / uvicorn | 웹 프레임워크 / 서버 |
| asyncpg | PostgreSQL 비동기 드라이버 |
| sqlalchemy[asyncio] | ORM (`[asyncio]`가 greenlet까지 같이 설치) |
| bcrypt | 비밀번호 해싱 |
| pyjwt | JWT 발급/검증 |
| pydantic[email] | `EmailStr` 이메일 형식 검증 |
| python-dotenv | `.env` 파일 읽기 |
| aiofiles | 비동기 파일 읽기/쓰기 |
| python-multipart | `UploadFile`(파일 업로드) 처리에 **필수** — 없으면 서버가 시작되지 않습니다 |

### 1-2. 폴더 만들기 (Git Bash 기준)

```bash
mkdir -p src/common src/wiring src/{user,auth}/{domain,application,infrastructure} src/{user,auth}/presentation/routers/v1 src/board/application src/board/domain/repository src/board/infrastructure/sqlalchemy src/board/presentation/routers/v1
```

### 1-3. `.gitignore`

```gitignore
.venv/
__pycache__/
*.pyc
.env
storage/
*.db
```

### 1-4. `.env.example` → 복사해서 `.env` 만들기

```dotenv
# 로컬 실행용 DB 주소 (docker compose 의 db 컨테이너에 접속)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/board

# docker compose 의 PostgreSQL 컨테이너 설정
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=board

# JWT 비밀키: 64자 이상 랜덤 문자열 (아래 명령으로 생성)
JWT_SECRET_KEY=change-me
ACCESS_TOKEN_EXPIRE_MINUTES=60

# 허용할 프론트엔드 주소 (콤마로 구분)
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

UPLOAD_DIR=storage
MAX_UPLOAD_SIZE_MB=5
CACHE_TTL_SECONDS=60
SQL_ECHO=false
LOGGING_MODE=info
```

`.env.example`을 `.env`로 복사한 뒤, 아래 명령으로 만든 문자열을 `JWT_SECRET_KEY`에 넣습니다.

```bash
uv run python -c "import secrets; print(secrets.token_urlsafe(64))"
```

> ⚠️ `.env`는 비밀번호·비밀키가 들어있으므로 **절대 GitHub에 올리지 않습니다.** 견본인 `.env.example`만 올립니다.

### 1-5. `docker-compose.yml` — PostgreSQL 띄우기

로컬에서는 `db`만 띄우고, EC2 배포 때는 `db` + `app` 둘 다 띄웁니다.

```yaml
services:
  db:
    image: postgres:17
    container_name: board-db
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}
      POSTGRES_DB: ${POSTGRES_DB:-board}
    ports:
      - "127.0.0.1:5433:5432"   # 내 컴퓨터(서버) 안에서만 접속 (5432는 다른 수업용 DB가 사용 중이라 5433)
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-board}"]
      interval: 5s
      timeout: 3s
      retries: 10
    restart: unless-stopped

  app:
    build: .
    container_name: board-api
    env_file: .env
    environment:
      # 컨테이너끼리는 localhost 가 아니라 서비스 이름(db)으로 접속한다
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER:-postgres}:${POSTGRES_PASSWORD:-postgres}@db:5432/${POSTGRES_DB:-board}
      UPLOAD_DIR: /app/storage
    ports:
      - "80:8000"               # 외부 80번 포트 -> 컨테이너 8000번
    volumes:
      - uploads:/app/storage    # 컨테이너를 다시 만들어도 업로드 파일 유지
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

volumes:
  pgdata:
  uploads:
```

Docker Desktop을 실행한 뒤 DB만 띄웁니다.

```bash
docker compose up -d db
```

```bash
docker compose ps
```

`board-db`가 `healthy`로 보이면 성공입니다.

### ✅ 1단계 결론
uv로 프로젝트와 패키지를 준비하고, 비밀값은 `.env`에 분리하고, PostgreSQL은 Docker로 띄웠습니다.

---

## 2. common — 공통 부품

### 2-1. `src/common/config.py` — 환경변수 한 곳에서 관리

튜터님 코드는 `os.getenv()`가 파일 곳곳에 있고, JWT 비밀키 기본값이 코드에 들어 있습니다. 한 곳에 모으고, **비밀키가 없으면 서버가 아예 켜지지 않게** 막았습니다.

```python
# src/common/config.py
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
```

### 2-2. `src/common/logger.py`

```python
# src/common/logger.py
import os
import logging
from dotenv import load_dotenv

load_dotenv()

log_mode = os.getenv("LOGGING_MODE", "info").lower()
log_level = logging.DEBUG if log_mode == "debug" else logging.INFO

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d) - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

logging.basicConfig(
    level=log_level,
    format=LOG_FORMAT,
    datefmt=DATE_FORMAT,
    force=True,
)


def get_logger(name: str | None = None) -> logging.Logger:
    return logging.getLogger(name or "app")
```

### 2-3. `src/common/database.py` — 요청 단위 트랜잭션 (튜터님 방식)

튜터님 최신 코드의 핵심 변화입니다.

| 방식 | 저장소(repository) | `get_db()` | 중간에 에러가 나면 |
|---|---|---|---|
| 예전 방식 | 함수마다 `commit()` | 세션만 열고 닫음 | 앞 단계는 이미 저장된 채로 남음 |
| **튜터님 방식** | `flush()`만 (SQL만 보내고 확정 안 함) | 요청이 끝나면 **한 번에 `commit()`** | **전부 `rollback()`** — 반쯤 저장되는 일이 없음 |

> `flush()`를 하면 INSERT가 실행되어 **자동 증가 ID 같은 값은 바로 받을 수 있지만**, `commit()` 전까지는 다른 요청에서 보이지 않습니다.

```python
# src/common/database.py
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from common.config import settings
from common.logger import get_logger

logger = get_logger(__name__)

# 커넥션 풀 설정 및 비동기 엔진 생성
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.POOL_SIZE,
    max_overflow=settings.MAX_OVERFLOW,
    pool_timeout=30.0,
    pool_recycle=1800,
    pool_pre_ping=True,
    echo=settings.SQL_ECHO,
)

# 비동기 세션 팩토리
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    요청 1건 = 세션 1개 = 트랜잭션 1개
    - 저장소(repository)는 flush() 로 SQL 만 보내고 확정(commit)하지 않는다
    - 요청이 에러 없이 끝나면 여기서 한 번에 commit, 에러가 나면 전부 rollback
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def close_db() -> None:
    logger.info("데이터베이스 엔진 연결 풀을 종료합니다.")
    await engine.dispose()
```

### 2-4. `src/common/models.py` — 테이블 공통 부모 + 생성/수정/삭제 시각

> 💡 **튜터님 코드의 함정**: `default=datetime.now(timezone.utc)`는 `now()`가 **서버가 켜질 때 딱 한 번** 실행되어, 모든 행의 생성 시각이 똑같아집니다.
> `server_default=func.now()`로 바꿔서 **DB가 INSERT 순간의 시각**을 넣게 했습니다.

```python
# src/common/models.py
from datetime import datetime
from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """모든 테이블 모델의 부모 클래스"""
    pass


class DateTimeBase:
    """생성/수정/삭제 시각 컬럼을 여러 테이블에서 재사용하기 위한 믹스인"""

    # server_default=func.now() : INSERT 하는 "그 순간"의 시각을 DB 가 넣는다
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # onupdate=func.now() : UPDATE 할 때마다 DB 시각으로 갱신
    modified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )
    # 소프트 삭제: 값이 있으면 "삭제된 데이터"로 취급
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


def init_models() -> None:
    """create_all 전에 모든 모델을 import 해서 Base.metadata 에 등록"""
    import user.infrastructure.models  # noqa: F401
    import auth.infrastructure.models  # noqa: F401
    import board.infrastructure.sqlalchemy.models  # noqa: F401
```

### 2-5. `src/common/exception.py` — 커스텀 예외

비즈니스 규칙을 어기면 이 예외들을 `raise` 합니다. 상태코드와 에러코드를 예외가 들고 있어서, 라우터에서 일일이 `try/except` 할 필요가 없습니다.

```python
# src/common/exception.py
from typing import Generic, TypeVar
from fastapi import status

T = TypeVar("T")


class SharedException(Exception, Generic[T]):
    """모든 애플리케이션 예외의 공통 부모 클래스"""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        error_code: str = "BAD_REQUEST",
        errors: T | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.errors: T | None = errors
        super().__init__(message)


class BadRequestException(SharedException[None]):
    def __init__(self, message: str, error_code: str = "BAD_REQUEST"):
        super().__init__(message, status.HTTP_400_BAD_REQUEST, error_code)


class UnauthorizedException(SharedException[None]):
    def __init__(self, message: str = "인증되지 않은 사용자입니다.", error_code: str = "UNAUTHORIZED"):
        super().__init__(message, status.HTTP_401_UNAUTHORIZED, error_code)


class ForbiddenException(SharedException[None]):
    def __init__(self, message: str = "리소스에 접근할 권한이 없습니다.", error_code: str = "FORBIDDEN"):
        super().__init__(message, status.HTTP_403_FORBIDDEN, error_code)


class NotFoundException(SharedException[None]):
    def __init__(self, message: str = "리소스를 찾을 수 없습니다.", error_code: str = "NOT_FOUND"):
        super().__init__(message, status.HTTP_404_NOT_FOUND, error_code)


class ConflictException(SharedException[None]):
    def __init__(self, message: str = "리소스가 이미 존재합니다.", error_code: str = "CONFLICT"):
        super().__init__(message, status.HTTP_409_CONFLICT, error_code)


class ValidationException(SharedException[dict[str, list[str]]]):
    def __init__(
        self,
        message: str = "유효성 검사에 실패했습니다.",
        error_code: str = "VALIDATION_ERROR",
        field_errors: dict[str, list[str]] | None = None,
    ):
        super().__init__(message, 422, error_code, field_errors or {})
```

### 2-6. `src/common/schemas.py` — 공통 응답 + 페이지네이션

- `APIResponse[T]` : 모든 응답의 겉포장. **튜터님 코드는 회원 API만 감싸고 게시판 API는 감싸지 않아** 응답 모양이 섞여 있었는데, 여기서는 전부 감쌉니다.
- `PageResponse[T]` : 튜터님 필드명(`total_count`, `page_size`)을 그대로 쓰는 목록 응답.
- `error_responses()` : Swagger에 "이 API는 401/403/404가 날 수 있고 모양은 이렇다"를 표시 → **문서화 점수**

```python
# src/common/schemas.py
import math
from datetime import datetime, timezone
from typing import Any, Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """모든 API 가 같은 모양으로 응답하기 위한 공통 응답 스키마"""

    success: bool = Field(description="처리 성공/실패 여부")
    code: str | None = Field(None, description="비즈니스 식별 코드 (성공 시 OK, 실패 시 에러 코드)")
    message: str | None = Field(None, description="성공 또는 실패 설명")
    errors: dict[str, list[str]] | list[str] | Any | None = Field(None, description="실패 시 세부 오류 내용")
    data: T | None = Field(None, description="성공 시 응답 데이터")
    responded_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="응답 날짜시간(UTC)",
    )

    @classmethod
    def ok(cls, data: T | None = None, message: str = "요청이 성공적으로 처리되었습니다.", code: str = "OK") -> "APIResponse[T]":
        return cls(success=True, code=code, message=message, errors=None, data=data)

    @classmethod
    def fail(cls, message: str, code: str = "BAD_REQUEST", errors: Any | None = None) -> "APIResponse[None]":
        return cls(success=False, code=code, message=message, errors=errors, data=None)


class PageResponse(BaseModel, Generic[T]):
    """페이지네이션 목록 응답 (공통)"""

    items: list[T] = Field(description="현재 페이지 데이터 목록")
    total_count: int = Field(description="조건에 맞는 전체 데이터 수")
    page: int = Field(description="현재 페이지 번호 (1부터 시작)")
    page_size: int = Field(description="페이지당 개수")
    total_pages: int = Field(description="전체 페이지 수")

    @staticmethod
    def calc_total_pages(total_count: int, page_size: int) -> int:
        return math.ceil(total_count / page_size) if total_count > 0 else 0


# Swagger 문서에 "실패하면 이런 모양으로 응답한다"를 보여주기 위한 헬퍼
_ERROR_DESCRIPTIONS = {
    400: "잘못된 요청",
    401: "인증 실패 (토큰 없음/만료/로그아웃됨)",
    403: "권한 없음 (게시판 권한/작성자/관리자/비회원 비밀번호 불일치)",
    404: "리소스 없음 (삭제된 데이터 포함)",
    409: "중복된 리소스",
    422: "입력값 검증 실패",
}


def error_responses(*status_codes: int) -> dict[int | str, dict[str, Any]]:
    return {
        code: {"model": APIResponse[None], "description": _ERROR_DESCRIPTIONS.get(code, "오류")}
        for code in status_codes
    }
```

### 2-7. `src/common/exception_handlers.py` — 모든 에러를 같은 모양으로

| 핸들러 | 잡는 에러 | 예시 |
|---|---|---|
| `SharedException` | 우리가 직접 던진 예외 | 권한 없음 403, 게시글 없음 404 |
| `RequestValidationError` | Pydantic 검증 실패 | 제목 누락 422 |
| `StarletteHTTPException` | FastAPI 기본 HTTP 에러 (**튜터님 코드에 없음**) | 없는 URL 404, 허용 안 된 메서드 405 |
| `Exception` | 예상 못 한 모든 에러 | 버그 500 (내용은 로그에만) |

```python
# src/common/exception_handlers.py
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from common.exception import SharedException
from common.logger import get_logger
from common.schemas import APIResponse

logger = get_logger(__name__)

HTTP_ERROR_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
}


def _json(status_code: int, body: APIResponse, headers: dict | None = None) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=body.model_dump(mode="json"), headers=headers)


def register_exception_handlers(app: FastAPI) -> None:
    # 1) 우리가 직접 던지는 비즈니스 예외 (SharedException 및 하위 예외)
    @app.exception_handler(SharedException)
    async def shared_exception_handler(request: Request, exc: SharedException):
        logger.warning("비즈니스 예외 [%s] %s (%s %s)", exc.error_code, exc.message, request.method, request.url.path)
        return _json(exc.status_code, APIResponse.fail(code=exc.error_code, message=exc.message, errors=exc.errors))

    # 2) Pydantic 요청 검증 실패 (422)
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        errors_map: dict[str, list[str]] = {}
        for err in exc.errors():
            # loc 예: ("body", "title") -> "title" / ("query", "page") -> "query.page"
            loc = ".".join(str(item) for item in err["loc"] if item != "body")
            message = err["msg"].removeprefix("Value error, ")  # 커스텀 검증 메시지 앞의 접두어 제거
            errors_map.setdefault(loc or "non_field_errors", []).append(message)

        logger.warning("요청 검증 실패 (%s %s): %s", request.method, request.url.path, errors_map)
        body = APIResponse.fail(code="REQUEST_VALIDATION_ERROR", message="요청 입력값 검증에 실패했습니다.", errors=errors_map)
        return _json(422, body)

    # 3) FastAPI/Starlette 가 던지는 HTTP 예외 (없는 URL 404, 허용 안 된 메서드 405 등)
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        code = HTTP_ERROR_CODES.get(exc.status_code, "HTTP_ERROR")
        return _json(exc.status_code, APIResponse.fail(code=code, message=str(exc.detail)), getattr(exc, "headers", None))

    # 4) 예상하지 못한 서버 내부 오류 (500) - 상세 내용은 로그에만 남기고 응답에는 숨긴다
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("처리되지 않은 서버 오류 (%s %s)", request.method, request.url.path)
        body = APIResponse.fail(code="INTERNAL_SERVER_ERROR", message="서버 내부 오류가 발생했습니다. 관리자에게 문의해주세요.")
        return _json(500, body)
```

### 2-8. `src/common/middlewares.py` — 요청 로깅 + CORS

튜터님 코드는 아직 빈 함수(`pass`)입니다. 미들웨어는 **모든 요청이 라우터 전/후에 거치는 검문소**입니다.

- **요청 로깅**: `[요청ID] GET /v1/boards -> 200 (12.3ms)` 형태로 기록, 응답 헤더에 `X-Request-ID`, `X-Process-Time` 추가
- **CORS**: 다른 주소(예: `localhost:3000`)의 프론트엔드가 브라우저에서 호출할 수 있게 허용 (`.env`의 `CORS_ORIGINS`)

```python
# src/common/middlewares.py
import time
import uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from common.config import settings
from common.logger import get_logger

logger = get_logger("app.access")


def register_middlewares(app: FastAPI) -> None:
    # 1) 요청 로깅 미들웨어: 모든 요청의 메서드/경로/상태코드/처리시간을 기록
    @app.middleware("http")
    async def access_log_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        start = time.perf_counter()

        try:
            response = await call_next(request)  # 실제 라우터 실행
        except Exception:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.error("[%s] %s %s -> 500 (%.1fms)", request_id, request.method, request.url.path, elapsed_ms)
            raise

        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{elapsed_ms:.1f}ms"
        logger.info(
            "[%s] %s %s -> %d (%.1fms)",
            request_id, request.method, request.url.path, response.status_code, elapsed_ms,
        )
        return response

    # 2) CORS 미들웨어: 허용한 출처(프론트엔드 주소)에서만 브라우저 호출 허용
    #    add_middleware 는 "나중에 추가한 것이 가장 바깥"에서 실행되므로 CORS 를 마지막에 추가한다
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Process-Time"],
    )
```

### 2-9. `src/common/cache.py` — 메모리 TTL 캐시

자주 읽고 가끔 바뀌는 데이터를 잠깐(기본 60초) 메모리에 보관해 DB 조회를 줄입니다. 이 프로젝트에서 **가장 효과가 큰 대상은 게시판 설정**입니다. 글·댓글 API를 부를 때마다 권한 확인을 위해 읽지만, 거의 바뀌지 않기 때문입니다.

> 💡 `asyncio`는 한 번에 한 코드만 실행하고, 이 클래스 메서드 안에는 `await`가 없어서 중간에 끼어들 틈이 없습니다. 그래서 Lock 없이도 안전합니다.

```python
# src/common/cache.py
import time
from abc import ABC, abstractmethod
from typing import Any


class Cache(ABC):
    """캐시 인터페이스 - 나중에 Redis 로 바꿔도 서비스 코드는 그대로 둘 수 있다"""

    @abstractmethod
    async def get(self, key: str) -> Any | None: ...

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int | None = None) -> None: ...

    @abstractmethod
    async def delete(self, key: str) -> None: ...

    @abstractmethod
    async def delete_prefix(self, prefix: str) -> None: ...


class InMemoryTTLCache(Cache):
    """서버 메모리(dict)에 저장하는 TTL(유효시간) 캐시. 서버 1대 운영 기준."""

    def __init__(self, default_ttl: int = 60):
        self._store: dict[str, tuple[float, Any]] = {}  # key -> (만료시각, 값)
        self._default_ttl = default_ttl

    async def get(self, key: str) -> Any | None:
        item = self._store.get(key)
        if item is None:
            return None
        expires_at, value = item
        if expires_at < time.monotonic():  # 유효시간이 지났으면 삭제 후 없는 것으로 처리
            self._store.pop(key, None)
            return None
        return value

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        expires_at = time.monotonic() + (ttl or self._default_ttl)
        self._store[key] = (expires_at, value)

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def delete_prefix(self, prefix: str) -> None:
        for key in [k for k in self._store if k.startswith(prefix)]:
            self._store.pop(key, None)
```

### ✅ 2단계 결론
설정·DB·예외·공통 응답·미들웨어·캐시를 먼저 만들었습니다. `get_db()`는 요청 하나를 하나의 트랜잭션으로 묶어, 끝나면 한 번에 commit하고 실패하면 전부 rollback합니다.

---

## 3. user — 회원

작성 순서: **domain → application → infrastructure → presentation** (안쪽부터 바깥으로)

### 3-1. `src/user/domain/service.py` — 비밀번호 해셔 인터페이스

```python
# src/user/domain/service.py
from abc import ABC, abstractmethod


class PasswordHasher(ABC):
    """비밀번호 해싱 인터페이스 (구현은 infrastructure/security.py)"""

    @abstractmethod
    def hash(self, raw_password: str) -> str:
        """평문 비밀번호를 단방향 해시값으로 변환"""

    @abstractmethod
    def verify(self, raw_password: str, hashed_password: str) -> bool:
        """평문 비밀번호가 해시값과 일치하는지 검증"""
```

### 3-2. `src/user/domain/user.py` — 회원 엔티티와 규칙 (탈퇴 포함)

> 💡 튜터님 코드는 `__post_init__`에서 검증해서 **DB에서 불러올 때도 매번 검증**이 돕니다. 여기서는 **새로 만들 때(`create`)만** 검증합니다.

```python
# src/user/domain/user.py
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from common.exception import BadRequestException, ForbiddenException, ValidationException
from user.domain.service import PasswordHasher

"""
[회원 규칙]
1. 비밀번호는 8자리 이상이며, 영문/숫자/특수문자(@$!%*#?&)를 각각 1개 이상 포함한다.
2. 이메일은 유효한 형식이어야 하며 로그인에 사용되므로 중복될 수 없다.
3. 이름은 2자 ~ 20자.
4. 탈퇴는 소프트 삭제: deleted_at 에 탈퇴 일시를 기록하고 resign=True 로 바꾼다.
5. 탈퇴는 본인 또는 관리자만 가능하다.
"""

EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")
PASSWORD_REGEX = re.compile(r"^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!%*#?&]{8,}$")

UserRole = Literal["USER", "ADMIN"]


@dataclass
class User:
    email: str
    name: str
    password_hash: str
    role: UserRole = "USER"
    resign: bool = False  # 탈퇴 여부

    id: uuid.UUID | None = None
    created_at: datetime | None = None
    modified_at: datetime | None = None
    deleted_at: datetime | None = None

    @property
    def is_admin(self) -> bool:
        return self.role == "ADMIN"

    @classmethod
    def create(cls, email: str, name: str, raw_password: str, hasher: PasswordHasher) -> "User":
        """신규 회원 생성 - 규칙 검증 후 비밀번호를 해싱해서 보관"""
        cls._validate_email(email)
        cls._validate_name(name)
        cls._validate_password(raw_password)
        return cls(email=email, name=name, password_hash=hasher.hash(raw_password))

    def change_password(self, old_password: str, new_password: str, hasher: PasswordHasher) -> None:
        self._ensure_active()
        if not hasher.verify(old_password, self.password_hash):
            raise BadRequestException("기존 비밀번호가 일치하지 않습니다.", error_code="INVALID_OLD_PASSWORD")
        if old_password == new_password:
            raise BadRequestException("새 비밀번호는 기존 비밀번호와 달라야 합니다.", error_code="SAME_PASSWORD")
        self._validate_password(new_password)
        self.password_hash = hasher.hash(new_password)
        self.modified_at = datetime.now(timezone.utc)

    def withdraw(self, requester: "User") -> None:
        """회원 탈퇴 (소프트 삭제)"""
        self._ensure_active()
        if not (self.id == requester.id or requester.is_admin):
            raise ForbiddenException("탈퇴 처리는 본인 또는 관리자만 가능합니다.", error_code="WITHDRAW_PERMISSION_DENIED")
        now = datetime.now(timezone.utc)
        self.resign = True
        self.deleted_at = now
        self.modified_at = now

    def _ensure_active(self) -> None:
        if self.resign:
            raise ForbiddenException("탈퇴한 회원입니다.", error_code="USER_ALREADY_WITHDRAWN")

    @staticmethod
    def _validate_email(email: str) -> None:
        if not EMAIL_REGEX.match(email):
            raise ValidationException("유효하지 않은 이메일 형식입니다.", field_errors={"email": ["올바른 이메일 형식을 입력하세요."]})

    @staticmethod
    def _validate_name(name: str) -> None:
        if not (2 <= len(name) <= 20):
            raise ValidationException("이름은 2자 이상 20자 이하여야 합니다.", field_errors={"name": ["이름은 2자 이상 20자 이하여야 합니다."]})

    @staticmethod
    def _validate_password(raw_password: str) -> None:
        if not PASSWORD_REGEX.match(raw_password):
            raise ValidationException(
                "비밀번호 규칙을 만족하지 않습니다.",
                field_errors={"password": ["비밀번호는 8자 이상이며 영문, 숫자, 특수문자(@$!%*#?&)를 포함해야 합니다."]},
            )
```

### 3-3. `src/user/domain/repository.py`

```python
# src/user/domain/repository.py
import uuid
from abc import ABC, abstractmethod

from user.domain.user import User


class UserRepository(ABC):
    @abstractmethod
    async def find_by_id(self, user_id: uuid.UUID) -> User | None:
        """ID 로 회원 조회"""

    @abstractmethod
    async def find_by_email(self, email: str) -> User | None:
        """이메일로 회원 조회"""

    @abstractmethod
    async def save(self, user: User) -> User:
        """신규면 INSERT, 기존이면 UPDATE"""
```

### 3-4. `src/user/application/service.py`

> 💡 **튜터님 코드 버그 1**: 회원가입에서 `except Exception`으로 모든 에러를 `ConflictException()`(409)으로 바꿉니다. 그래서 **비밀번호 규칙 위반도 "리소스가 이미 존재합니다"(409)**로 나갑니다. 여기서는 감싸지 않아서 검증 에러는 422로 나갑니다.
>
> 💡 **튜터님 코드 버그 2**: 비밀번호 변경이 URL의 `user_id`만 받아 **로그인 없이 남의 비밀번호를 바꿀 수 있습니다.** 로그인한 본인(`User`)을 받도록 바꿨습니다.

```python
# src/user/application/service.py
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
```

### 3-5. `src/user/infrastructure/models.py`

```python
# src/user/infrastructure/models.py
import uuid
from sqlalchemy import Boolean, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from common.models import Base, DateTimeBase
from user.domain.user import User


class UserModel(Base, DateTimeBase):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="USER", server_default="USER", nullable=False)
    resign: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)

    def to_user(self) -> User:
        """ORM 모델 -> 도메인 엔티티 변환"""
        return User(
            id=self.id,
            email=self.email,
            name=self.name,
            password_hash=self.password_hash,
            role=self.role,
            resign=self.resign,
            created_at=self.created_at,
            modified_at=self.modified_at,
            deleted_at=self.deleted_at,
        )
```

### 3-6. `src/user/infrastructure/repositories.py`

- `commit()` 대신 `flush()` (2-3 참고)
- 동시에 같은 이메일로 가입하면 DB unique 제약이 막고(`IntegrityError`), 그것을 409로 바꿉니다.

```python
# src/user/infrastructure/repositories.py
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
```

### 3-7. `src/user/infrastructure/security.py` — bcrypt

```python
# src/user/infrastructure/security.py
import bcrypt
from user.domain.service import PasswordHasher


class BcryptPasswordHasher(PasswordHasher):
    def hash(self, raw_password: str) -> str:
        salt = bcrypt.gensalt()  # 매번 다른 salt -> 같은 비밀번호도 해시값이 달라진다
        return bcrypt.hashpw(raw_password.encode("utf-8"), salt).decode("utf-8")

    def verify(self, raw_password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(raw_password.encode("utf-8"), hashed_password.encode("utf-8"))
```

### 3-8. `src/user/presentation/schemas.py`

- `field_validator` = **커스텀 검증** → 비밀번호 규칙을 Pydantic 단계에서 먼저 걸러 422로 응답 (domain에서도 한 번 더 검사하는 이중 방어)
- 응답 스키마에는 `password_hash`를 **아예 넣지 않습니다.**

```python
# src/user/presentation/schemas.py
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from user.domain.user import PASSWORD_REGEX

PASSWORD_RULE_MESSAGE = "비밀번호는 8자 이상이며 영문, 숫자, 특수문자(@$!%*#?&)를 포함해야 합니다."


def _check_password_rule(value: str) -> str:
    if not PASSWORD_REGEX.match(value):
        raise ValueError(PASSWORD_RULE_MESSAGE)
    return value


class SignUpUserRequest(BaseModel):
    email: EmailStr = Field(description="로그인에 사용할 이메일", examples=["user@example.com"])
    name: str = Field(min_length=2, max_length=20, description="이름 (2~20자)", examples=["홍길동"])
    password: str = Field(description=PASSWORD_RULE_MESSAGE, examples=["P@ssw0rd!"])

    # 커스텀 검증: 비밀번호 규칙을 Pydantic 단계에서 먼저 걸러 422 로 응답
    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return _check_password_rule(value)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("이름은 공백을 제외하고 2자 이상이어야 합니다.")
        return value


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(min_length=1, description="현재 비밀번호")
    new_password: str = Field(description=PASSWORD_RULE_MESSAGE)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return _check_password_rule(value)


class UserResponse(BaseModel):
    """응답에는 password_hash 같은 민감 정보를 절대 넣지 않는다"""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(description="회원 ID")
    email: str = Field(description="이메일")
    name: str = Field(description="이름")
    role: str = Field(description="권한 (USER, ADMIN)")
    created_at: datetime | None = Field(None, description="가입일시")
```

### 3-9. `src/user/presentation/dependencies.py` — 자리표시자 (튜터님 구조)

튜터님 구조에서는 `get_current_user`, `get_optional_user`, `require_admin`도 **여기에 빈 자리로만** 두고, 실제 구현은 `wiring/user.py`에 있습니다.

```python
# src/user/presentation/dependencies.py
from typing import Annotated
from fastapi import Depends

from user.application.service import UserService
from user.domain.repository import UserRepository
from user.domain.user import User

"""
FastAPI Depends 자리표시자 모음
- 라우터는 이 "빈 자리"만 알고, 실제 구현은 wiring/user.py 가 dependency_overrides 로 끼워 넣는다
"""


def provide_user_service() -> UserService:
    raise NotImplementedError("UserService 의존성이 주입되지 않았습니다.")


def provide_user_repository() -> UserRepository:
    raise NotImplementedError("UserRepository 의존성이 주입되지 않았습니다.")


async def get_current_user() -> User:
    """로그인 필수 - 토큰이 없거나 잘못되면 401"""
    raise NotImplementedError("get_current_user 의존성이 주입되지 않았습니다.")


async def get_optional_user() -> User | None:
    """로그인 선택 - 토큰이 없으면 None(비회원), 토큰이 잘못되면 401"""
    raise NotImplementedError("get_optional_user 의존성이 주입되지 않았습니다.")


async def require_admin() -> User:
    """관리자만 통과"""
    raise NotImplementedError("require_admin 의존성이 주입되지 않았습니다.")


# 라우터에서 짧게 쓰기 위한 별칭
CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]
AdminUser = Annotated[User, Depends(require_admin)]
```

### 3-10. `src/user/presentation/routers/v1/router.py`

```python
# src/user/presentation/routers/v1/router.py
from typing import Annotated
from fastapi import APIRouter, Depends, status

from common.schemas import APIResponse, error_responses
from user.application.service import UserService
from user.presentation.dependencies import CurrentUser, provide_user_service
from user.presentation.schemas import ChangePasswordRequest, SignUpUserRequest, UserResponse

router = APIRouter(prefix="/v1/users", tags=["Users"])

UserServiceDep = Annotated[UserService, Depends(provide_user_service)]


@router.post(
    "",
    response_model=APIResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="회원가입",
    description="이메일/이름/비밀번호로 회원가입합니다. 비밀번호는 bcrypt 로 해싱되어 저장됩니다.",
    responses=error_responses(409, 422),
)
async def sign_up(body: SignUpUserRequest, user_service: UserServiceDep):
    user = await user_service.register_user(email=body.email, name=body.name, password=body.password)
    return APIResponse.ok(data=UserResponse.model_validate(user), message="회원가입이 완료되었습니다.")


@router.get("/me", response_model=APIResponse[UserResponse], summary="내 정보 조회", responses=error_responses(401))
async def get_me(current_user: CurrentUser):
    return APIResponse.ok(data=UserResponse.model_validate(current_user))


@router.patch(
    "/me/password",
    response_model=APIResponse[None],
    summary="내 비밀번호 변경",
    description="로그인한 본인의 비밀번호만 변경할 수 있습니다.",
    responses=error_responses(400, 401, 422),
)
async def change_my_password(body: ChangePasswordRequest, current_user: CurrentUser, user_service: UserServiceDep):
    await user_service.change_password(current_user, body.old_password, body.new_password)
    return APIResponse.ok(message="비밀번호가 변경되었습니다.")


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="회원 탈퇴",
    description="소프트 삭제 방식으로 탈퇴합니다. 탈퇴 후에는 로그인할 수 없습니다.",
    responses=error_responses(401, 403),
)
async def withdraw_me(current_user: CurrentUser, user_service: UserServiceDep):
    await user_service.withdraw(target=current_user, requester=current_user)
```

### ✅ 3단계 결론
회원 규칙은 domain에, 가입·비밀번호 변경·탈퇴 흐름은 application에, DB와 bcrypt는 infrastructure에, HTTP 입출력은 presentation에 나눴습니다. 튜터님 코드의 "검증 에러가 409로 나가는 문제"와 "인증 없는 비밀번호 변경"을 고쳤습니다.

---

## 4. auth — 로그인/로그아웃(JWT)

### JWT 흐름 한눈에 보기

| 비유 | 실제 기술 용어 | 설명 |
|---|---|---|
| 놀이공원 입장 팔찌 | **JWT 액세스 토큰** | 로그인하면 발급, 요청마다 `Authorization: Bearer <토큰>`으로 제시 |
| 팔찌 위조 방지 홀로그램 | **서명(HS512 + 비밀키)** | 비밀키 없이는 내용을 바꿀 수 없음 |
| 팔찌 유효시간 | **exp (만료 시각)** | 지나면 `TOKEN_EXPIRED` 401 |
| 팔찌 일련번호 | **jti (토큰 고유 ID)** | 로그아웃 시 이 번호를 블랙리스트에 등록 |
| 분실 신고 명단 | **토큰 블랙리스트 테이블** | 명단에 있는 jti면 `TOKEN_REVOKED` 401 |
| 팔찌 없이 들어온 손님 | **비회원 (`get_optional_user` → None)** | 게시판 권한이 `ALL`인 기능만 사용 |
| 입구 직원 | **`resolve_optional_user` / `resolve_current_user`** | 팔찌 검사 → 회원 확인 = **인증** |
| "직원 전용" 구역 확인 | **게시판 권한 / 작성자 / 관리자 검사** | 할 수 있는지 판단 = **인가** |

### 4-1. `src/auth/domain/entities.py`

```python
# src/auth/domain/entities.py
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class TokenPayload:
    """JWT 안에 들어있는 정보"""
    user_id: UUID   # sub: 토큰 주인
    jti: str        # 토큰 고유 ID (로그아웃 블랙리스트에 사용)
    exp: datetime   # 만료 시각
```

### 4-2. `src/auth/domain/repository.py`

```python
# src/auth/domain/repository.py
from abc import ABC, abstractmethod
from datetime import datetime


class TokenBlacklistRepository(ABC):
    @abstractmethod
    async def add(self, jti: str, expired_at: datetime) -> None:
        """로그아웃한 토큰의 jti 를 블랙리스트에 등록"""

    @abstractmethod
    async def is_blacklisted(self, jti: str) -> bool:
        """블랙리스트에 등록된 토큰인지 확인"""

    @abstractmethod
    async def cleanup_expired(self, current_time: datetime) -> int:
        """이미 만료된 토큰은 블랙리스트에 둘 필요가 없으므로 정리"""
```

### 4-3. `src/auth/domain/service.py` — `UserCredentialVerifier` (튜터님 구조)

auth는 "이메일/비밀번호가 맞으면 user_id를 달라"는 것만 알고, 회원을 어떻게 찾고 비교하는지는 모릅니다. **auth와 user가 서로 덜 얽히게** 하는 설계입니다.

```python
# src/auth/domain/service.py
from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from auth.domain.entities import TokenPayload


class TokenProvider(ABC):
    @abstractmethod
    def create_access_token(self, user_id: UUID) -> tuple[str, str, datetime, int]:
        """(token, jti, expired_at, expires_in_seconds) 반환"""

    @abstractmethod
    def decode_token(self, token: str) -> TokenPayload:
        """토큰 서명/만료 검증 후 페이로드 반환"""


class UserCredentialVerifier(ABC):
    """
    로그인 정보 확인 인터페이스
    - auth 는 "이메일/비밀번호가 맞으면 user_id 를 달라"는 것만 알고,
      회원을 어떻게 찾고 비밀번호를 어떻게 비교하는지는 모른다 (user 모듈과의 결합도 감소)
    """

    @abstractmethod
    async def verify_credentials(self, email: str, plain_password: str) -> UUID | None:
        """로그인 성공 시 user_id, 실패 시 None"""
```

### 4-4. `src/auth/application/service.py`

로그인 실패 시 "이메일이 없음/비밀번호 틀림"을 구분하지 않습니다. 구분하면 공격자가 **가입된 이메일인지 알아낼 수 있기** 때문입니다.

```python
# src/auth/application/service.py
from datetime import datetime, timezone

from auth.domain.entities import TokenPayload
from auth.domain.repository import TokenBlacklistRepository
from auth.domain.service import TokenProvider, UserCredentialVerifier
from common.exception import UnauthorizedException


class AuthService:
    def __init__(
        self,
        credential_verifier: UserCredentialVerifier,
        token_blacklist_repo: TokenBlacklistRepository,
        token_provider: TokenProvider,
    ):
        self._credential_verifier = credential_verifier
        self._blacklist_repo = token_blacklist_repo
        self._token_provider = token_provider

    async def login(self, email: str, plain_password: str) -> tuple[str, str, int]:
        """(access_token, token_type, expires_in) 반환"""
        user_id = await self._credential_verifier.verify_credentials(email, plain_password)
        # 이메일이 틀렸는지 비밀번호가 틀렸는지 구분해서 알려주지 않는다 (계정 존재 여부 노출 방지)
        if not user_id:
            raise UnauthorizedException("이메일 또는 비밀번호가 올바르지 않습니다.", error_code="INVALID_CREDENTIALS")

        token, _, _, expires_in = self._token_provider.create_access_token(user_id)
        return token, "bearer", expires_in

    async def logout(self, token: str) -> None:
        payload = self._token_provider.decode_token(token)
        if not await self._blacklist_repo.is_blacklisted(payload.jti):
            await self._blacklist_repo.add(jti=payload.jti, expired_at=payload.exp)
        await self._blacklist_repo.cleanup_expired(datetime.now(timezone.utc))

    async def authenticate_token(self, token: str) -> TokenPayload:
        payload = self._token_provider.decode_token(token)
        if await self._blacklist_repo.is_blacklisted(payload.jti):
            raise UnauthorizedException("로그아웃된 토큰입니다. 다시 로그인해주세요.", error_code="TOKEN_REVOKED")
        return payload
```

### 4-5. `src/auth/infrastructure/models.py`

```python
# src/auth/infrastructure/models.py
from datetime import datetime
from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from common.models import Base


class TokenBlacklistModel(Base):
    __tablename__ = "token_blacklist"

    jti: Mapped[str] = mapped_column(String(36), primary_key=True)
    expired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
```

### 4-6. `src/auth/infrastructure/repositories.py`

```python
# src/auth/infrastructure/repositories.py
from datetime import datetime
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.domain.repository import TokenBlacklistRepository
from auth.infrastructure.models import TokenBlacklistModel


class SqlAlchemyTokenBlacklistRepository(TokenBlacklistRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, jti: str, expired_at: datetime) -> None:
        self.session.add(TokenBlacklistModel(jti=jti, expired_at=expired_at))
        await self.session.flush()

    async def is_blacklisted(self, jti: str) -> bool:
        result = await self.session.scalar(select(TokenBlacklistModel.jti).where(TokenBlacklistModel.jti == jti))
        return result is not None

    async def cleanup_expired(self, current_time: datetime) -> int:
        result = await self.session.execute(delete(TokenBlacklistModel).where(TokenBlacklistModel.expired_at <= current_time))
        await self.session.flush()
        return result.rowcount
```

### 4-7. `src/auth/infrastructure/credentials_verifier.py`

**탈퇴한 회원은 로그인할 수 없도록** `user.resign` 검사를 추가했습니다.

```python
# src/auth/infrastructure/credentials_verifier.py
from uuid import UUID

from auth.domain.service import UserCredentialVerifier
from user.domain.repository import UserRepository
from user.domain.service import PasswordHasher


class UserCredentialVerifierImpl(UserCredentialVerifier):
    def __init__(self, user_repo: UserRepository, password_hasher: PasswordHasher):
        self._user_repo = user_repo
        self._password_hasher = password_hasher

    async def verify_credentials(self, email: str, plain_password: str) -> UUID | None:
        user = await self._user_repo.find_by_email(email)
        if not user or user.resign:  # 없는 회원 / 탈퇴 회원은 로그인 불가
            return None
        if not self._password_hasher.verify(plain_password, user.password_hash):
            return None
        return user.id
```

### 4-8. `src/auth/infrastructure/security.py` — JWT 발급/검증

- `jwt.decode()`는 서명과 `exp`(만료)를 **자동으로** 검사합니다.
- 만료와 위조를 **다른 에러코드**로 구분해서, 프론트엔드가 "다시 로그인하세요"를 띄울 수 있게 합니다. (튜터님 코드는 둘 다 같은 메시지)

```python
# src/auth/infrastructure/security.py
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
```

### 4-9. `src/auth/presentation/dependencies.py`

`HTTPBearer(auto_error=False)` : 토큰이 없어도 일단 통과시킵니다. **비회원도 쓸 수 있는 API**가 있기 때문이고, 토큰이 꼭 필요한 곳에서는 직접 401을 공통 응답 모양으로 던집니다.

```python
# src/auth/presentation/dependencies.py
from typing import Annotated
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from auth.application.service import AuthService
from common.exception import UnauthorizedException

# auto_error=False : 토큰이 없을 때 FastAPI 기본 에러 대신 우리 공통 에러 형식으로 응답하기 위해
#                    (비회원 허용 API 에서는 토큰이 없어도 통과시켜야 하므로 필수)
bearer_scheme = HTTPBearer(auto_error=False, description="로그인 API 로 발급받은 access_token 을 입력하세요.")

BearerCredentials = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]


def provide_auth_service() -> AuthService:
    """FastAPI Depends 자리표시자 (실제 객체는 wiring/auth.py 에서 연결)"""
    raise NotImplementedError("AuthService 의존성이 주입되지 않았습니다.")


async def get_token(credentials: BearerCredentials) -> str:
    """Authorization: Bearer <토큰> 헤더에서 토큰 문자열만 꺼낸다 (없으면 401)"""
    if credentials is None:
        raise UnauthorizedException("로그인이 필요합니다.", error_code="TOKEN_MISSING")
    return credentials.credentials
```

### 4-10. `src/auth/presentation/schemas.py`

```python
# src/auth/presentation/schemas.py
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr = Field(description="이메일", examples=["user@example.com"])
    password: str = Field(min_length=1, description="비밀번호", examples=["P@ssw0rd!"])


class TokenResponse(BaseModel):
    access_token: str = Field(description="Authorization 헤더에 'Bearer <토큰>' 형태로 넣을 JWT")
    token_type: str = Field(default="bearer", description="토큰 타입", examples=["bearer"])
    expires_in: int = Field(description="토큰 유효기간(초)", examples=[3600])
```

### 4-11. `src/auth/presentation/routers/v1/router.py`

```python
# src/auth/presentation/routers/v1/router.py
from typing import Annotated
from fastapi import APIRouter, Depends, status

from auth.application.service import AuthService
from auth.presentation.dependencies import get_token, provide_auth_service
from auth.presentation.schemas import LoginRequest, TokenResponse
from common.schemas import APIResponse, error_responses

router = APIRouter(prefix="/v1/auth", tags=["Auth"])

AuthServiceDep = Annotated[AuthService, Depends(provide_auth_service)]


@router.post(
    "/login",
    response_model=APIResponse[TokenResponse],
    summary="로그인",
    description="이메일/비밀번호를 확인하고 JWT 액세스 토큰(HS512)을 발급합니다.",
    responses=error_responses(401, 422),
)
async def login(body: LoginRequest, auth_service: AuthServiceDep):
    token, token_type, expires_in = await auth_service.login(body.email, body.password)
    data = TokenResponse(access_token=token, token_type=token_type, expires_in=expires_in)
    return APIResponse.ok(data=data, message="로그인되었습니다.")


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="로그아웃",
    description="현재 토큰의 jti 를 블랙리스트에 등록해 즉시 사용할 수 없게 만듭니다.",
    responses=error_responses(401),
)
async def logout(token: Annotated[str, Depends(get_token)], auth_service: AuthServiceDep):
    await auth_service.logout(token)
```

### ✅ 4단계 결론
로그인하면 exp와 jti가 담긴 JWT를 발급하고, 로그아웃하면 jti를 블랙리스트에 넣어 즉시 무효화합니다. 토큰이 없으면 "비회원"으로 처리할 수 있게 `auto_error=False`를 사용합니다.

---

## 5. board — 게시판·게시글·댓글·첨부파일

튜터님 코드의 게시판 설계를 그대로 따르고, 첨부파일과 캐싱을 더했습니다.

### 5-1. `src/board/domain/enums.py` — 권한 등급과 검색 대상

`Role`에 **숫자 등급(level)**을 붙여서 "ADMIN은 USER 권한도 만족한다"를 `satisfies()` 하나로 판단합니다.

| 게시판 설정값 | 비회원(None) | 회원(USER) | 관리자(ADMIN) |
|---|---|---|---|
| `ALL` | ○ | ○ | ○ |
| `USER` | ✕ | ○ | ○ |
| `ADMIN` | ✕ | ✕ | ○ |

```python
# src/board/domain/enums.py
from enum import StrEnum


class Role(StrEnum):
    """게시판 권한 등급 (숫자가 클수록 상위 권한)"""

    ALL = "ALL"      # 비회원 포함 모두
    USER = "USER"    # 회원 + 관리자
    ADMIN = "ADMIN"  # 관리자만

    @property
    def level(self) -> int:
        return {Role.ALL: 0, Role.USER: 1, Role.ADMIN: 2}[self]

    def satisfies(self, required_role: "Role | str") -> bool:
        """현재 역할이 요구 권한 이상인지 확인 (예: ADMIN 은 USER 권한도 만족)"""
        return self.level >= Role(required_role).level


class PostSearchType(StrEnum):
    """게시글 검색 대상"""

    ALL = "ALL"                      # 제목 + 내용 + 작성자 이름 + 작성자 이메일
    TITLE = "TITLE"
    CONTENT = "CONTENT"
    TITLE_CONTENT = "TITLE_CONTENT"
    AUTHOR_NAME = "AUTHOR_NAME"
    AUTHOR_EMAIL = "AUTHOR_EMAIL"
```

### 5-2. `src/board/domain/board.py` — 게시판 설정 엔티티

```python
# src/board/domain/board.py
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

from board.domain.enums import Role
from common.exception import BadRequestException, ValidationException

"""
[게시판 설정 규칙]
1. 게시판은 무한대로 생성 가능하다. 게시판 설정 하나가 게시판 하나가 된다. (예: freetalk, qna)
2. 게시판은 비회원, 회원, 관리자 모두 사용 가능하며, 역할별로 이용 제한을 설정할 수 있다.
3. 권한 종류
    - edit_role         : 글 쓰기/수정/삭제
    - view_role         : 글 상세 열람
    - list_role         : 글 목록 열람
    - comment_list_role : 댓글 목록 열람
    - comment_edit_role : 댓글 쓰기/수정/삭제
4. 게시글 목록 노출 개수(page_size)는 설정 가능하며 기본값은 20이다.
5. 게시판 ID는 영문 소문자로 시작, 영문 소문자/숫자/하이픈/언더스코어 허용 (2~30자)
6. 게시판 설정은 소프트 삭제를 하며 삭제된 게시판은 수정할 수 없다.
7. 게시판 생성/수정/삭제는 관리자만 가능하다.
"""

BOARD_ID_REGEX = re.compile(r"^[a-z][a-z0-9_-]{1,29}$")


@dataclass(frozen=True)
class Authority:
    """게시판 세부 권한 설정 (값 객체)"""

    edit_role: Role = Role.ALL
    view_role: Role = Role.ALL
    list_role: Role = Role.ALL
    comment_list_role: Role = Role.ALL
    comment_edit_role: Role = Role.ALL

    def can_edit(self, user_role: Role | None) -> bool:
        return self._check(user_role, self.edit_role)

    def can_view(self, user_role: Role | None) -> bool:
        return self._check(user_role, self.view_role)

    def can_list(self, user_role: Role | None) -> bool:
        return self._check(user_role, self.list_role)

    def can_view_comments(self, user_role: Role | None) -> bool:
        return self._check(user_role, self.comment_list_role)

    def can_edit_comments(self, user_role: Role | None) -> bool:
        return self._check(user_role, self.comment_edit_role)

    @staticmethod
    def _check(user_role: Role | None, required: Role) -> bool:
        if user_role is None:  # 비회원
            return required == Role.ALL
        return Role(user_role).satisfies(required)


@dataclass
class Board:
    """게시판 설정 엔티티"""

    board_id: str    # freetalk, qna
    board_name: str  # 자유게시판, 질문과 답변
    authority: Authority = field(default_factory=Authority)
    page_size: int = 20

    created_at: datetime | None = None
    modified_at: datetime | None = None
    deleted_at: datetime | None = None

    def __post_init__(self):
        field_errors: dict[str, list[str]] = {}

        normalized_id = (self.board_id or "").strip().lower()
        if not BOARD_ID_REGEX.match(normalized_id):
            field_errors["board_id"] = [
                "영문 소문자로 시작해야 하며, 2~30자의 영문 소문자, 숫자, 특수문자(-, _)만 사용할 수 있습니다."
            ]
        else:
            self.board_id = normalized_id

        if not self.board_name or not self.board_name.strip():
            field_errors["board_name"] = ["게시판 이름은 공백일 수 없습니다."]

        if self.page_size < 1:
            field_errors["page_size"] = ["게시글 목록 노출 개수는 1 이상이어야 합니다."]

        if field_errors:
            raise ValidationException("게시판 설정 유효성 검사에 실패했습니다.", field_errors=field_errors)

    @classmethod
    def create(cls, board_id: str, board_name: str, authority: Authority | None = None, page_size: int = 20) -> "Board":
        return cls(board_id=board_id, board_name=board_name.strip(), authority=authority or Authority(), page_size=page_size)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def update_config(self, board_name: str, page_size: int, authority: Authority | None = None) -> None:
        if self.is_deleted:
            raise BadRequestException("삭제된 게시판 설정은 수정할 수 없습니다.", error_code="BOARD_DELETED")

        field_errors: dict[str, list[str]] = {}
        if not board_name or not board_name.strip():
            field_errors["board_name"] = ["게시판 이름은 공백일 수 없습니다."]
        if page_size < 1:
            field_errors["page_size"] = ["게시글 목록 노출 개수는 1 이상이어야 합니다."]
        if field_errors:
            raise ValidationException("게시판 설정 수정 유효성 검사에 실패했습니다.", field_errors=field_errors)

        self.board_name = board_name.strip()
        self.page_size = page_size
        if authority is not None:
            self.authority = authority
        self.modified_at = datetime.now(timezone.utc)

    def delete(self) -> None:
        if self.is_deleted:
            raise BadRequestException("이미 삭제된 게시판입니다.", error_code="BOARD_DELETED")
        self.deleted_at = datetime.now(timezone.utc)
```

### 5-3. `src/board/domain/service.py` — 해셔·파일 저장소 인터페이스

```python
# src/board/domain/service.py
from abc import ABC, abstractmethod
from typing import AsyncIterator


class PasswordHasher(ABC):
    """비회원 비밀번호 해싱 인터페이스 (구현은 infrastructure/security.py)"""

    @abstractmethod
    def hash(self, raw_password: str) -> str:
        """평문 비밀번호를 단방향 해시값으로 변환"""

    @abstractmethod
    def verify(self, raw_password: str, hashed_password: str) -> bool:
        """평문 비밀번호가 해시값과 일치하는지 검증"""


class FileStorage(ABC):
    """파일 저장소 인터페이스 - 지금은 로컬 디스크, 나중에 S3 로 바꿔도 서비스 코드는 그대로"""

    @abstractmethod
    async def save(self, chunks: AsyncIterator[bytes], extension: str, max_bytes: int) -> tuple[str, int]:
        """파일 조각(chunk)들을 저장하고 (저장된 파일명, 파일 크기) 반환"""

    @abstractmethod
    def open(self, stored_name: str) -> AsyncIterator[bytes]:
        """저장된 파일을 조각 단위로 읽는 비동기 제너레이터 반환"""

    @abstractmethod
    async def delete(self, stored_name: str) -> None:
        """저장된 파일 삭제 (없으면 무시)"""

    @abstractmethod
    def exists(self, stored_name: str) -> bool:
        """파일 존재 여부"""
```

### 5-4. `src/board/domain/post.py` — 게시글·댓글·첨부파일과 값 객체

**값 객체(Value Object)**: `BoardInfo`, `Author`, `GuestPassword`처럼 **값 자체가 의미인 작은 객체**입니다. `frozen=True`라 만든 뒤에는 바꿀 수 없습니다.

수정/삭제 권한 판단 순서(`_can_modify_or_delete`)는 튜터님 규칙 그대로입니다.
1. 관리자면 통과
2. 회원 글이면 → 작성자 본인인지
3. 비회원 글이면 → 비밀번호가 맞는지

튜터님 코드에서 `Post`와 `Comment`에 똑같이 있던 권한 판단·비밀번호 생성 코드는 함수 하나로 모았습니다.

```python
# src/board/domain/post.py
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from board.domain.enums import Role
from board.domain.service import PasswordHasher
from common.exception import BadRequestException, ValidationException

"""
[게시글/댓글 규칙]
1. 비회원으로 글 또는 댓글 작성 시 비밀번호(6자리 이상)를 등록해야 하며,
   수정/삭제 시 작성할 때 등록한 비밀번호를 검증한다.
2. 회원 글/댓글은 직접 작성한 회원만 수정/삭제 가능하며, 관리자는 상관없이 가능하다.
3. 게시글/댓글은 소프트 삭제한다. (deleted_at 기록)
4. 첨부파일은 회원 게시글에만 올릴 수 있으며, 작성자 본인 또는 관리자만 업로드/삭제할 수 있다.
5. 첨부파일은 허용된 확장자만 업로드할 수 있다.
"""

TITLE_MAX_LENGTH = 200
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".pdf", ".txt", ".zip"}


# ==================== 값 객체 (Value Object) ====================
@dataclass(frozen=True)
class BoardInfo:
    """게시글이 속한 게시판 정보"""
    board_id: str
    board_name: str


@dataclass(frozen=True)
class Author:
    """작성자 정보 (회원이면 author_id 가 있고, 비회원이면 None)"""
    author_name: str
    author_id: uuid.UUID | None = None

    def __post_init__(self):
        name = (self.author_name or "").strip()
        if not (1 <= len(name) <= 20):
            raise ValidationException(
                "작성자 정보 유효성 검사에 실패했습니다.",
                field_errors={"author_name": ["작성자 이름은 1자 이상 20자 이하여야 합니다."]},
            )

    @property
    def is_guest(self) -> bool:
        return self.author_id is None

    @classmethod
    def member(cls, user_id: uuid.UUID, username: str) -> "Author":
        return cls(author_id=user_id, author_name=username.strip())

    @classmethod
    def guest(cls, guest_name: str) -> "Author":
        return cls(author_id=None, author_name=guest_name.strip())

    def is_owner(self, user_id: uuid.UUID | None) -> bool:
        """로그인 사용자가 작성자 본인인지 (비회원 글은 항상 False)"""
        if self.is_guest or user_id is None:
            return False
        return self.author_id == user_id


@dataclass(frozen=True)
class GuestPassword:
    """비회원 비밀번호 (해시 문자열만 보관)"""
    hashed_value: str

    @classmethod
    def create(cls, raw_password: str, hasher: PasswordHasher) -> "GuestPassword":
        if not raw_password or len(raw_password) < 6:
            raise ValidationException(
                "비회원 비밀번호 유효성 검사에 실패했습니다.",
                field_errors={"guest_password": ["비회원 비밀번호는 6자리 이상이어야 합니다."]},
            )
        return cls(hashed_value=hasher.hash(raw_password))

    def verify(self, raw_password: str | None, hasher: PasswordHasher) -> bool:
        if not raw_password:
            return False
        return hasher.verify(raw_password, self.hashed_value)


def _can_modify_or_delete(
    author: Author,
    guest_password: GuestPassword | None,
    requester_id: uuid.UUID | None,
    user_role: Role | None,
    raw_guest_password: str | None,
    hasher: PasswordHasher,
) -> bool:
    """수정/삭제 권한 확인 (관리자 -> 회원 본인 -> 비회원 비밀번호 일치 순)"""
    if user_role == Role.ADMIN:
        return True
    if not author.is_guest:
        return author.is_owner(requester_id)
    return guest_password is not None and guest_password.verify(raw_guest_password, hasher)


def _make_guest_password(author: Author, raw_guest_password: str | None, hasher: PasswordHasher) -> GuestPassword | None:
    if not author.is_guest:
        return None
    if not raw_guest_password:
        raise ValidationException(
            "비회원은 비밀번호를 입력해야 합니다.",
            field_errors={"guest_password": ["비회원 비밀번호는 필수입니다."]},
        )
    return GuestPassword.create(raw_guest_password, hasher)


# ==================== 엔티티 ====================
@dataclass
class Attachment:
    """첨부파일"""
    post_id: int
    original_name: str       # 사용자가 올린 원래 파일명 (다운로드 시 표시)
    stored_name: str         # 서버 디스크 저장 파일명 (uuid - 중복/경로조작 방지)
    content_type: str | None
    size: int
    attachment_id: int | None = None
    created_at: datetime | None = None

    @staticmethod
    def extract_extension(filename: str) -> str:
        """파일명에서 확장자를 꺼내고, 허용된 확장자인지 검사"""
        name = os.path.basename(filename or "")
        extension = os.path.splitext(name)[1].lower()
        if not name or extension not in ALLOWED_EXTENSIONS:
            raise ValidationException(
                "허용되지 않는 파일 형식입니다.",
                error_code="INVALID_FILE_TYPE",
                field_errors={"file": [f"허용 확장자: {', '.join(sorted(ALLOWED_EXTENSIONS))}"]},
            )
        return extension


@dataclass
class Post:
    """게시글"""
    board_info: BoardInfo
    title: str
    content: str
    author: Author
    guest_password: GuestPassword | None = None
    post_id: int | None = None

    created_at: datetime | None = None
    modified_at: datetime | None = None
    deleted_at: datetime | None = None
    attachments: list[Attachment] = field(default_factory=list)

    def __post_init__(self):
        self._validate(self.title, self.content)
        if self.author.is_guest and self.guest_password is None:
            raise ValidationException(
                "게시글 유효성 검사에 실패했습니다.",
                field_errors={"guest_password": ["비회원 작성 시 비밀번호 등록은 필수입니다."]},
            )

    @classmethod
    def create(
        cls,
        board_info: BoardInfo,
        title: str,
        content: str,
        author: Author,
        raw_guest_password: str | None,
        hasher: PasswordHasher,
    ) -> "Post":
        return cls(
            board_info=board_info,
            title=title.strip(),
            content=content.strip(),
            author=author,
            guest_password=_make_guest_password(author, raw_guest_password, hasher),
        )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def can_modify_or_delete(
        self, requester_id: uuid.UUID | None, user_role: Role | None, raw_guest_password: str | None, hasher: PasswordHasher
    ) -> bool:
        return _can_modify_or_delete(self.author, self.guest_password, requester_id, user_role, raw_guest_password, hasher)

    def can_manage_attachments(self, requester_id: uuid.UUID | None, user_role: Role | None) -> bool:
        """첨부파일 업로드/삭제 권한: 관리자 또는 회원 작성자 본인"""
        return user_role == Role.ADMIN or self.author.is_owner(requester_id)

    def update_content(self, title: str, content: str) -> None:
        if self.is_deleted:
            raise BadRequestException("삭제된 게시글은 수정할 수 없습니다.", error_code="POST_DELETED")
        title, content = title.strip(), content.strip()
        self._validate(title, content)
        self.title, self.content = title, content
        self.modified_at = datetime.now(timezone.utc)

    def delete(self) -> None:
        if self.is_deleted:
            raise BadRequestException("이미 삭제된 게시글입니다.", error_code="POST_DELETED")
        self.deleted_at = datetime.now(timezone.utc)

    @staticmethod
    def _validate(title: str, content: str) -> None:
        field_errors: dict[str, list[str]] = {}
        if not title or not title.strip():
            field_errors["title"] = ["제목은 필수 입력값입니다."]
        elif len(title) > TITLE_MAX_LENGTH:
            field_errors["title"] = [f"제목은 {TITLE_MAX_LENGTH}자 이하여야 합니다."]
        if not content or not content.strip():
            field_errors["content"] = ["내용은 필수 입력값입니다."]
        if field_errors:
            raise ValidationException("게시글 유효성 검사에 실패했습니다.", field_errors=field_errors)


@dataclass
class Comment:
    """댓글"""
    post_id: int
    content: str
    author: Author
    guest_password: GuestPassword | None = None
    comment_id: int | None = None

    created_at: datetime | None = None
    modified_at: datetime | None = None
    deleted_at: datetime | None = None

    def __post_init__(self):
        if not self.content or not self.content.strip():
            raise ValidationException("댓글 유효성 검사에 실패했습니다.", field_errors={"content": ["댓글 내용은 필수 입력값입니다."]})
        if self.author.is_guest and self.guest_password is None:
            raise ValidationException(
                "댓글 유효성 검사에 실패했습니다.",
                field_errors={"guest_password": ["비회원 댓글 작성 시 비밀번호 등록은 필수입니다."]},
            )

    @classmethod
    def create(
        cls, post_id: int, content: str, author: Author, raw_guest_password: str | None, hasher: PasswordHasher
    ) -> "Comment":
        return cls(
            post_id=post_id,
            content=content.strip(),
            author=author,
            guest_password=_make_guest_password(author, raw_guest_password, hasher),
        )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def can_modify_or_delete(
        self, requester_id: uuid.UUID | None, user_role: Role | None, raw_guest_password: str | None, hasher: PasswordHasher
    ) -> bool:
        return _can_modify_or_delete(self.author, self.guest_password, requester_id, user_role, raw_guest_password, hasher)

    def update_content(self, content: str) -> None:
        if self.is_deleted:
            raise BadRequestException("삭제된 댓글은 수정할 수 없습니다.", error_code="COMMENT_DELETED")
        if not content or not content.strip():
            raise ValidationException("댓글 수정 유효성 검사에 실패했습니다.", field_errors={"content": ["댓글 내용은 공백일 수 없습니다."]})
        self.content = content.strip()
        self.modified_at = datetime.now(timezone.utc)

    def delete(self) -> None:
        if self.is_deleted:
            raise BadRequestException("이미 삭제된 댓글입니다.", error_code="COMMENT_DELETED")
        self.deleted_at = datetime.now(timezone.utc)
```

### 5-5. `src/board/domain/repository/*.py` — 저장소 인터페이스 4개

**`board_repository.py`**

```python
# src/board/domain/repository/board_repository.py
from abc import ABC, abstractmethod

from board.domain.board import Board


class BoardRepository(ABC):
    @abstractmethod
    async def find_by_id(self, board_id: str) -> Board | None:
        """게시판 단건 조회 (삭제된 게시판 제외)"""

    @abstractmethod
    async def find_all(self, include_deleted: bool = False) -> list[Board]:
        """게시판 목록 조회"""

    @abstractmethod
    async def exists_by_id(self, board_id: str) -> bool:
        """게시판 ID 사용 여부 (삭제된 게시판 포함 - ID 재사용 방지)"""

    @abstractmethod
    async def save(self, board: Board) -> Board:
        """신규면 INSERT, 기존이면 UPDATE"""
```

**`post_repository.py`**

```python
# src/board/domain/repository/post_repository.py
from abc import ABC, abstractmethod

from board.domain.enums import PostSearchType
from board.domain.post import Post


class PostRepository(ABC):
    @abstractmethod
    async def find_by_id(self, post_id: int) -> Post | None:
        """게시글 단건 조회 (삭제된 글 제외, 첨부파일 포함)"""

    @abstractmethod
    async def find_by_board_id(
        self, board_id: str, limit: int, offset: int, search_type: PostSearchType, keyword: str | None
    ) -> list[Post]:
        """특정 게시판의 게시글 목록을 최신순으로 페이징 조회"""

    @abstractmethod
    async def count_by_board_id(self, board_id: str, search_type: PostSearchType, keyword: str | None) -> int:
        """특정 게시판의 (검색 조건에 맞는) 게시글 수"""

    @abstractmethod
    async def save(self, post: Post) -> Post:
        """신규면 INSERT, 기존이면 UPDATE (소프트 삭제 포함)"""
```

**`comment_repository.py`**

```python
# src/board/domain/repository/comment_repository.py
from abc import ABC, abstractmethod

from board.domain.post import Comment


class CommentRepository(ABC):
    @abstractmethod
    async def find_by_id(self, comment_id: int) -> Comment | None:
        """댓글 단건 조회 (삭제된 댓글 제외)"""

    @abstractmethod
    async def find_by_post_id(self, post_id: int) -> list[Comment]:
        """게시글의 댓글 목록 (등록순)"""

    @abstractmethod
    async def save(self, comment: Comment) -> Comment:
        """신규면 INSERT, 기존이면 UPDATE (소프트 삭제 포함)"""
```

**`attachment_repository.py`**

```python
# src/board/domain/repository/attachment_repository.py
from abc import ABC, abstractmethod

from board.domain.post import Attachment


class AttachmentRepository(ABC):
    @abstractmethod
    async def find_by_id(self, attachment_id: int) -> Attachment | None:
        """첨부파일 단건 조회"""

    @abstractmethod
    async def save(self, attachment: Attachment) -> Attachment:
        """첨부파일 정보 등록"""

    @abstractmethod
    async def delete(self, attachment_id: int) -> None:
        """첨부파일 정보 삭제 (실제 파일은 FileStorage 가 삭제)"""
```

### 5-6. `src/board/application/service.py` — 서비스 4개 + 캐싱

튜터님 코드는 `PostService`와 `CommentService`에 똑같은 `_get_active_board()`/`_get_active_post()`가 있었습니다. 여기서는 **모듈 함수(`load_active_board`, `load_active_post`)로 한 번만** 만들고, 게시판 설정 조회에 캐시를 붙였습니다.

| 캐시 대상 | 키 | 지우는 시점 |
|---|---|---|
| 게시판 설정 | `boards:{board_id}` | 게시판 수정/삭제 |
| 게시글 상세 | `posts:detail:{post_id}` | 게시글 수정/삭제, 첨부파일 추가/삭제 |
| 게시글 목록 | `posts:list:{board_id}:...` | 그 게시판에 글 작성/수정/삭제 |

> ⚠️ **권한 확인은 캐시와 상관없이 요청마다** 합니다. (게시글을 캐시에서 꺼냈더라도 `can_view` 검사는 매번 실행)
> ⚠️ 수정·삭제 전에는 캐시가 아닌 **DB 최신값**으로 판단합니다.
>
> 💡 **튜터님 코드 버그 3**: 목록의 `total_pages`를 라우터는 "요청값 또는 20"으로, 서비스는 "요청값 또는 게시판 설정값"으로 계산해서, 게시판 `page_size`가 20이 아니면 **전체 페이지 수가 틀립니다.** 여기서는 서비스가 실제 적용한 크기를 함께 돌려줍니다.

```python
# src/board/application/service.py
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
```

### 5-7. `src/board/infrastructure/sqlalchemy/models.py` — 테이블과 관계

- 글에 `author_name`을 함께 저장합니다. 비회원 글도 이름이 필요하고, 목록 조회 때 users JOIN이 필요 없습니다. (튜터님 방식)
- 회원이 지워지면 `author_id`는 `SET NULL`로 처리합니다. (글은 남김)
- `board`는 `lazy="joined"`, `attachments`는 `lazy="selectin"` → **N+1 문제 방지**
- 인덱스: 목록 조회 조건(`board_id = ? AND deleted_at IS NULL`)에 맞춰 `(board_id, deleted_at)` 복합 인덱스를 만들었습니다. (튜터님 코드의 `(id, deleted_at)`은 `id`가 이미 기본키라 효과가 거의 없습니다)

```python
# src/board/infrastructure/sqlalchemy/models.py
import uuid
from datetime import datetime
from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.models import Base, DateTimeBase

"""
[테이블 관계]
boards 1 ── N posts        (게시판 하나에 여러 게시글)
users  1 ── N posts        (회원이 쓴 글 / 비회원 글은 author_id = NULL)
posts  1 ── N comments     (게시글 하나에 여러 댓글)
posts  1 ── N attachments  (게시글 하나에 여러 첨부파일)

[lazy 옵션]
joined   : 처음 조회할 때 LEFT JOIN 으로 같이 가져온다 (N:1, 예: 게시글 -> 게시판 이름)
selectin : 본 쿼리 후 "WHERE post_id IN (...)" 쿼리 1번으로 자식들을 한꺼번에 가져온다 (1:N)
-> 둘 다 게시글 10개를 조회할 때 쿼리가 10번 더 나가는 N+1 문제를 막는다
"""


class BoardModel(Base, DateTimeBase):
    """게시판 설정 테이블"""
    __tablename__ = "boards"

    board_id: Mapped[str] = mapped_column("id", String(30), primary_key=True)
    board_name: Mapped[str] = mapped_column(String(100), nullable=False)
    page_size: Mapped[int] = mapped_column(Integer, default=20, nullable=False)

    # 게시판 권한 (ALL / USER / ADMIN)
    edit_role: Mapped[str] = mapped_column(String(20), default="ALL", nullable=False)
    view_role: Mapped[str] = mapped_column(String(20), default="ALL", nullable=False)
    list_role: Mapped[str] = mapped_column(String(20), default="ALL", nullable=False)
    comment_list_role: Mapped[str] = mapped_column(String(20), default="ALL", nullable=False)
    comment_edit_role: Mapped[str] = mapped_column(String(20), default="ALL", nullable=False)


class PostModel(Base, DateTimeBase):
    """게시글 테이블"""
    __tablename__ = "posts"
    __table_args__ = (
        # 목록 조회 조건(board_id = ? AND deleted_at IS NULL)에 맞춘 복합 인덱스
        Index("ix_posts_board_id_deleted_at", "board_id", "deleted_at"),
        Index("ix_posts_author_id", "author_id"),
    )

    post_id: Mapped[int] = mapped_column("id", BigInteger, primary_key=True, autoincrement=True)
    board_id: Mapped[str] = mapped_column(String(30), ForeignKey("boards.id"), nullable=False)

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # 작성자 이름을 글에 같이 저장 -> 목록 조회 때 users 테이블을 JOIN 하지 않아도 된다
    author_name: Mapped[str] = mapped_column(String(50), nullable=False)
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    guest_password: Mapped[str | None] = mapped_column(String(255), nullable=True)  # 비회원 비밀번호 해시

    board: Mapped[BoardModel] = relationship(lazy="joined")
    attachments: Mapped[list["AttachmentModel"]] = relationship(
        back_populates="post", lazy="selectin", order_by="AttachmentModel.attachment_id"
    )


class CommentModel(Base, DateTimeBase):
    """댓글 테이블"""
    __tablename__ = "comments"
    __table_args__ = (Index("ix_comments_post_id_deleted_at", "post_id", "deleted_at"),)

    comment_id: Mapped[int] = mapped_column("id", BigInteger, primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("posts.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    author_name: Mapped[str] = mapped_column(String(50), nullable=False)
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    guest_password: Mapped[str | None] = mapped_column(String(255), nullable=True)


class AttachmentModel(Base):
    """첨부파일 테이블 (파일 자체는 디스크에, 여기엔 파일 정보만 저장)"""
    __tablename__ = "attachments"

    attachment_id: Mapped[int] = mapped_column("id", BigInteger, primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    post: Mapped[PostModel] = relationship(back_populates="attachments", lazy="raise")
```

### 5-8. `src/board/infrastructure/sqlalchemy/mappers.py` — 엔티티 ↔ 모델 변환 (튜터님 구조)

> 💡 튜터님 코드는 `to_model()`에 `created_at=domain.created_at`(None)을 넘깁니다. 명시적으로 None을 넣으면 DB 기본값 대신 **NULL이 들어가려고 해서** NOT NULL 오류가 날 수 있어 뺐습니다.

```python
# src/board/infrastructure/sqlalchemy/mappers.py
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
```

### 5-9. `src/board/infrastructure/sqlalchemy/board_repository.py`

삭제된 게시판의 ID도 "사용 중"으로 봅니다. 게시판 ID가 기본키라서, 같은 ID로 다시 만들면 DB 충돌이 나기 때문입니다.

```python
# src/board/infrastructure/sqlalchemy/board_repository.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from board.domain.board import Board
from board.domain.repository.board_repository import BoardRepository
from board.infrastructure.sqlalchemy.mappers import BoardMapper
from board.infrastructure.sqlalchemy.models import BoardModel


class SqlAlchemyBoardRepository(BoardRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_by_id(self, board_id: str) -> Board | None:
        stmt = select(BoardModel).where(BoardModel.board_id == board_id, BoardModel.deleted_at.is_(None))
        model = await self.session.scalar(stmt)
        return BoardMapper.to_domain(model) if model else None

    async def find_all(self, include_deleted: bool = False) -> list[Board]:
        stmt = select(BoardModel).order_by(BoardModel.created_at)
        if not include_deleted:
            stmt = stmt.where(BoardModel.deleted_at.is_(None))
        models = await self.session.scalars(stmt)
        return [BoardMapper.to_domain(m) for m in models]

    async def exists_by_id(self, board_id: str) -> bool:
        # 삭제된 게시판의 ID 도 "사용 중"으로 본다 (기본키라서 같은 ID 로 다시 만들 수 없음)
        return await self.session.get(BoardModel, board_id) is not None

    async def save(self, board: Board) -> Board:
        model = await self.session.get(BoardModel, board.board_id)
        if model:  # 수정
            model.board_name = board.board_name
            model.page_size = board.page_size
            model.edit_role = board.authority.edit_role.value
            model.view_role = board.authority.view_role.value
            model.list_role = board.authority.list_role.value
            model.comment_list_role = board.authority.comment_list_role.value
            model.comment_edit_role = board.authority.comment_edit_role.value
            model.deleted_at = board.deleted_at
        else:  # 등록
            model = BoardMapper.to_model(board)
            self.session.add(model)

        await self.session.flush()
        await self.session.refresh(model)
        return BoardMapper.to_domain(model)
```

### 5-10. `src/board/infrastructure/sqlalchemy/post_repository.py` — 검색·페이지네이션

- 검색 대상(`search_type`)별 조건을 딕셔너리로 고릅니다.
- 이메일 검색은 users 테이블이 필요하므로 **필요할 때만 OUTER JOIN**합니다. (비회원 글도 결과에 나와야 하므로 INNER가 아닌 OUTER)
- `icontains(..., autoescape=True)` : 검색어의 `%`, `_`를 **와일드카드가 아닌 글자 그대로** 찾습니다. (`100%` 검색 시 모든 글이 나오는 문제 방지)
- `save()` 후 `populate_existing=True`로 다시 조회해서 게시판 이름·첨부파일까지 최신 상태로 돌려줍니다.

```python
# src/board/infrastructure/sqlalchemy/post_repository.py
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
```

### 5-11. `src/board/infrastructure/sqlalchemy/comment_repository.py`

```python
# src/board/infrastructure/sqlalchemy/comment_repository.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from board.domain.post import Comment
from board.domain.repository.comment_repository import CommentRepository
from board.infrastructure.sqlalchemy.mappers import CommentMapper
from board.infrastructure.sqlalchemy.models import CommentModel


class SqlAlchemyCommentRepository(CommentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_by_id(self, comment_id: int) -> Comment | None:
        stmt = select(CommentModel).where(CommentModel.comment_id == comment_id, CommentModel.deleted_at.is_(None))
        model = await self.session.scalar(stmt)
        return CommentMapper.to_domain(model) if model else None

    async def find_by_post_id(self, post_id: int) -> list[Comment]:
        stmt = (
            select(CommentModel)
            .where(CommentModel.post_id == post_id, CommentModel.deleted_at.is_(None))
            .order_by(CommentModel.comment_id.asc())
        )
        models = await self.session.scalars(stmt)
        return [CommentMapper.to_domain(m) for m in models]

    async def save(self, comment: Comment) -> Comment:
        if comment.comment_id:  # 수정 / 소프트 삭제
            model = await self.session.get(CommentModel, comment.comment_id)
            model.content = comment.content
            model.modified_at = comment.modified_at
            model.deleted_at = comment.deleted_at
        else:  # 등록
            model = CommentMapper.to_model(comment)
            self.session.add(model)

        await self.session.flush()
        await self.session.refresh(model)
        return CommentMapper.to_domain(model)
```

### 5-12. `src/board/infrastructure/sqlalchemy/attachment_repository.py`

```python
# src/board/infrastructure/sqlalchemy/attachment_repository.py
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from board.domain.post import Attachment
from board.domain.repository.attachment_repository import AttachmentRepository
from board.infrastructure.sqlalchemy.mappers import AttachmentMapper
from board.infrastructure.sqlalchemy.models import AttachmentModel


class SqlAlchemyAttachmentRepository(AttachmentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_by_id(self, attachment_id: int) -> Attachment | None:
        model = await self.session.get(AttachmentModel, attachment_id)
        return AttachmentMapper.to_domain(model) if model else None

    async def save(self, attachment: Attachment) -> Attachment:
        model = AttachmentMapper.to_model(attachment)
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return AttachmentMapper.to_domain(model)

    async def delete(self, attachment_id: int) -> None:
        await self.session.execute(delete(AttachmentModel).where(AttachmentModel.attachment_id == attachment_id))
        await self.session.flush()
```

### 5-13. `src/board/infrastructure/sqlalchemy/seed.py` — 기본 게시판 자동 생성

게시판 생성은 관리자만 가능합니다. 배포 직후 **평가자가 관리자 없이도 바로 글쓰기를 테스트**할 수 있도록, 게시판이 하나도 없으면 `freetalk`(자유게시판)을 만듭니다.

```python
# src/board/infrastructure/sqlalchemy/seed.py
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from board.infrastructure.sqlalchemy.models import BoardModel
from common.logger import get_logger

logger = get_logger(__name__)


async def seed_default_board(session: AsyncSession) -> None:
    """
    게시판이 하나도 없으면 기본 게시판(freetalk)을 만든다.
    - 게시판 생성은 관리자만 가능하므로, 배포 직후 평가자가 바로 글쓰기를 테스트할 수 있게 하기 위함
    """
    count = await session.scalar(select(func.count()).select_from(BoardModel))
    if count:
        return
    session.add(BoardModel(board_id="freetalk", board_name="자유게시판", page_size=20))
    await session.commit()
    logger.info("기본 게시판 'freetalk' 을 생성했습니다.")
```

### 5-14. `src/board/infrastructure/security.py` — 비회원 비밀번호 bcrypt (튜터님 코드와 동일)

```python
# src/board/infrastructure/security.py
import bcrypt
from board.domain.service import PasswordHasher

class BcryptPasswordHasher(PasswordHasher):
    def hash(self, raw_password: str) -> str:
        pwd_bytes = raw_password.encode("utf-8")
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(pwd_bytes, salt)
        return hashed.decode("utf-8")

    def verify(self, raw_password: str, hashed_password: str) -> bool:
        pwd_bytes = raw_password.encode("utf-8")
        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hashed_bytes)
```

### 5-15. `src/board/infrastructure/file_storage.py` — 파일 저장

- 파일을 **1MB씩 나눠** 쓰고 읽어서, 큰 파일도 메모리를 적게 씁니다.
- 저장 파일명은 **uuid**로 바꿉니다. 원래 이름을 쓰면 같은 이름끼리 덮어쓰거나, `../../` 같은 이름으로 서버의 다른 폴더를 건드리는 공격이 가능합니다.
- 크기 제한을 넘거나 실패하면 덜 써진 파일을 지웁니다.

```python
# src/board/infrastructure/file_storage.py
import uuid
from pathlib import Path
from typing import AsyncIterator

import aiofiles
import aiofiles.os

from board.domain.service import FileStorage
from common.exception import BadRequestException

CHUNK_SIZE = 1024 * 1024  # 1MB 씩 나눠서 읽고 쓴다 (큰 파일도 메모리를 적게 사용)


class LocalFileStorage(FileStorage):
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, stored_name: str) -> Path:
        # 경로 조작 공격(../../etc/passwd 같은 이름) 방지: 파일명 부분만 사용
        return self.base_dir / Path(stored_name).name

    async def save(self, chunks: AsyncIterator[bytes], extension: str, max_bytes: int) -> tuple[str, int]:
        stored_name = f"{uuid.uuid4().hex}{extension}"  # 원래 파일명 대신 랜덤 이름으로 저장
        path = self._path(stored_name)
        size = 0
        try:
            async with aiofiles.open(path, "wb") as f:
                async for chunk in chunks:
                    size += len(chunk)
                    if size > max_bytes:
                        raise BadRequestException(
                            f"파일 크기는 최대 {max_bytes // (1024 * 1024)}MB 까지 업로드할 수 있습니다.",
                            error_code="FILE_TOO_LARGE",
                        )
                    await f.write(chunk)
        except Exception:
            if path.exists():  # 중간에 실패하면 덜 써진 파일 삭제
                await aiofiles.os.remove(path)
            raise
        return stored_name, size

    async def open(self, stored_name: str) -> AsyncIterator[bytes]:
        async with aiofiles.open(self._path(stored_name), "rb") as f:
            while chunk := await f.read(CHUNK_SIZE):
                yield chunk

    async def delete(self, stored_name: str) -> None:
        path = self._path(stored_name)
        if path.exists():
            await aiofiles.os.remove(path)

    def exists(self, stored_name: str) -> bool:
        return self._path(stored_name).is_file()
```

### 5-16. `src/board/presentation/schemas.py`

- `pattern=` : 게시판 ID 형식을 Pydantic에서 먼저 검사
- `_strip = field_validator(...)(_strip_not_blank)` : 같은 검증 함수를 여러 필드·여러 스키마에 재사용
- `PostSearchQuery` : 쿼리 파라미터 묶음 (`Depends()`로 사용, 튜터님 방식)
- `computed_field` : 응답에만 계산해서 넣는 값 (`download_url`)
- 비회원 비밀번호는 **응답에 절대 포함하지 않습니다.**

```python
# src/board/presentation/schemas.py
import uuid
from datetime import datetime
from pydantic import BaseModel, Field, computed_field, field_validator

from board.domain.board import Authority, Board
from board.domain.enums import PostSearchType, Role
from board.domain.post import TITLE_MAX_LENGTH, Attachment, Author, Comment, Post
from common.schemas import PageResponse

CONTENT_MAX_LENGTH = 10000


def _strip_not_blank(value: str | None) -> str | None:
    """앞뒤 공백 제거 후, 공백만 있는 문자열은 거부 (커스텀 검증)"""
    if value is None:
        return None
    value = value.strip()
    if not value:
        raise ValueError("공백만 입력할 수 없습니다.")
    return value


# ==================== 게시판 설정 ====================
class AuthoritySchema(BaseModel):
    """게시판 권한 세부 설정"""
    edit_role: Role = Field(default=Role.ALL, description="게시글 작성/수정/삭제 권한")
    view_role: Role = Field(default=Role.ALL, description="게시글 상세 열람 권한")
    list_role: Role = Field(default=Role.ALL, description="게시글 목록 열람 권한")
    comment_list_role: Role = Field(default=Role.ALL, description="댓글 목록 열람 권한")
    comment_edit_role: Role = Field(default=Role.ALL, description="댓글 작성/수정/삭제 권한")

    def to_domain(self) -> Authority:
        return Authority(**self.model_dump())

    @classmethod
    def from_domain(cls, authority: Authority) -> "AuthoritySchema":
        return cls(
            edit_role=authority.edit_role,
            view_role=authority.view_role,
            list_role=authority.list_role,
            comment_list_role=authority.comment_list_role,
            comment_edit_role=authority.comment_edit_role,
        )


class CreateBoardRequest(BaseModel):
    board_id: str = Field(
        pattern=r"^[a-z][a-z0-9_-]{1,29}$",
        description="게시판 ID (영문 소문자로 시작, 영문 소문자/숫자/-/_ 2~30자)",
        examples=["notice"],
    )
    board_name: str = Field(min_length=1, max_length=50, description="게시판 이름", examples=["공지사항"])
    authority: AuthoritySchema = Field(default_factory=AuthoritySchema, description="권한 설정")
    page_size: int = Field(default=20, ge=1, le=100, description="목록 한 페이지당 게시글 수")

    _strip = field_validator("board_name")(_strip_not_blank)


class UpdateBoardRequest(BaseModel):
    board_name: str = Field(min_length=1, max_length=50, description="게시판 이름")
    page_size: int = Field(default=20, ge=1, le=100, description="목록 한 페이지당 게시글 수")
    authority: AuthoritySchema | None = Field(default=None, description="변경할 권한 (생략하면 기존 유지)")

    _strip = field_validator("board_name")(_strip_not_blank)


class BoardResponse(BaseModel):
    board_id: str = Field(description="게시판 ID")
    board_name: str = Field(description="게시판 이름")
    authority: AuthoritySchema = Field(description="권한 설정")
    page_size: int = Field(description="목록 한 페이지당 게시글 수")
    created_at: datetime | None = Field(None, description="생성일시")
    modified_at: datetime | None = Field(None, description="수정일시")
    deleted_at: datetime | None = Field(None, description="삭제일시 (삭제된 게시판만)")

    @classmethod
    def from_domain(cls, board: Board) -> "BoardResponse":
        return cls(
            board_id=board.board_id,
            board_name=board.board_name,
            authority=AuthoritySchema.from_domain(board.authority),
            page_size=board.page_size,
            created_at=board.created_at,
            modified_at=board.modified_at,
            deleted_at=board.deleted_at,
        )


# ==================== 게시글 ====================
class CreatePostRequest(BaseModel):
    """게시글 작성 (회원은 title/content 만, 비회원은 guest_name/guest_password 까지)"""
    title: str = Field(min_length=1, max_length=TITLE_MAX_LENGTH, description="제목", examples=["첫 번째 게시글"])
    content: str = Field(min_length=1, max_length=CONTENT_MAX_LENGTH, description="내용", examples=["안녕하세요!"])
    guest_name: str | None = Field(default=None, min_length=1, max_length=20, description="[비회원] 작성자 이름")
    guest_password: str | None = Field(default=None, min_length=6, description="[비회원] 비밀번호 (6자 이상)")

    _strip = field_validator("title", "content", "guest_name")(_strip_not_blank)


class UpdatePostRequest(BaseModel):
    """게시글 수정 (PUT: 제목/내용을 모두 보낸다)"""
    title: str = Field(min_length=1, max_length=TITLE_MAX_LENGTH, description="제목")
    content: str = Field(min_length=1, max_length=CONTENT_MAX_LENGTH, description="내용")
    guest_password: str | None = Field(default=None, description="[비회원 글] 작성 시 등록한 비밀번호")

    _strip = field_validator("title", "content")(_strip_not_blank)


class GuestPasswordRequest(BaseModel):
    """삭제 요청 본문 (비회원 글/댓글일 때만 필요)"""
    guest_password: str | None = Field(default=None, description="[비회원 글/댓글] 작성 시 등록한 비밀번호")


class PostSearchQuery(BaseModel):
    """게시글 목록 쿼리 파라미터"""
    page: int = Field(default=1, ge=1, description="페이지 번호 (1부터)")
    page_size: int | None = Field(default=None, ge=1, le=100, description="페이지 크기 (생략 시 게시판 설정값)")
    search_type: PostSearchType = Field(default=PostSearchType.ALL, description="검색 대상")
    keyword: str | None = Field(default=None, min_length=1, max_length=50, description="검색어")


class AuthorResponse(BaseModel):
    author_id: uuid.UUID | None = Field(None, description="회원 ID (비회원은 null)")
    author_name: str = Field(description="작성자 이름")
    is_guest: bool = Field(description="비회원 작성 여부")

    @classmethod
    def from_domain(cls, author: Author) -> "AuthorResponse":
        return cls(author_id=author.author_id, author_name=author.author_name, is_guest=author.is_guest)


class AttachmentResponse(BaseModel):
    attachment_id: int = Field(description="첨부파일 ID")
    post_id: int = Field(description="게시글 ID")
    original_name: str = Field(description="원본 파일명")
    content_type: str | None = Field(None, description="파일 MIME 타입")
    size: int = Field(description="파일 크기(byte)")
    created_at: datetime | None = Field(None, description="업로드 일시")

    @computed_field(description="다운로드 URL")
    @property
    def download_url(self) -> str:
        return f"/v1/attachments/{self.attachment_id}"

    @classmethod
    def from_domain(cls, attachment: Attachment) -> "AttachmentResponse":
        return cls(
            attachment_id=attachment.attachment_id,
            post_id=attachment.post_id,
            original_name=attachment.original_name,
            content_type=attachment.content_type,
            size=attachment.size,
            created_at=attachment.created_at,
        )


class PostListItemResponse(BaseModel):
    """목록용 - 내용(content)은 빼서 응답 크기를 줄인다"""
    post_id: int = Field(description="게시글 ID")
    board_id: str = Field(description="게시판 ID")
    board_name: str = Field(description="게시판 이름")
    title: str = Field(description="제목")
    author: AuthorResponse = Field(description="작성자")
    attachment_count: int = Field(description="첨부파일 개수")
    created_at: datetime | None = Field(None, description="작성일시")
    modified_at: datetime | None = Field(None, description="수정일시")

    @classmethod
    def from_domain(cls, post: Post) -> "PostListItemResponse":
        return cls(
            post_id=post.post_id,
            board_id=post.board_info.board_id,
            board_name=post.board_info.board_name,
            title=post.title,
            author=AuthorResponse.from_domain(post.author),
            attachment_count=len(post.attachments),
            created_at=post.created_at,
            modified_at=post.modified_at,
        )


class PostDetailResponse(PostListItemResponse):
    content: str = Field(description="내용")
    attachments: list[AttachmentResponse] = Field(default_factory=list, description="첨부파일 목록")

    @classmethod
    def from_domain(cls, post: Post) -> "PostDetailResponse":
        base = PostListItemResponse.from_domain(post).model_dump()
        return cls(
            **base,
            content=post.content,
            attachments=[AttachmentResponse.from_domain(a) for a in post.attachments],
        )


class PostPageResponse(PageResponse[PostListItemResponse]):
    """게시글 목록 응답 = 공통 페이지 응답 + 적용된 검색 조건"""
    search_type: PostSearchType = Field(description="적용된 검색 대상")
    keyword: str | None = Field(default=None, description="적용된 검색어")


# ==================== 댓글 ====================
class CreateCommentRequest(BaseModel):
    content: str = Field(min_length=1, max_length=1000, description="댓글 내용", examples=["좋은 글이네요!"])
    guest_name: str | None = Field(default=None, min_length=1, max_length=20, description="[비회원] 작성자 이름")
    guest_password: str | None = Field(default=None, min_length=6, description="[비회원] 비밀번호 (6자 이상)")

    _strip = field_validator("content", "guest_name")(_strip_not_blank)


class UpdateCommentRequest(BaseModel):
    content: str = Field(min_length=1, max_length=1000, description="수정할 댓글 내용")
    guest_password: str | None = Field(default=None, description="[비회원 댓글] 작성 시 등록한 비밀번호")

    _strip = field_validator("content")(_strip_not_blank)


class CommentResponse(BaseModel):
    comment_id: int = Field(description="댓글 ID")
    post_id: int = Field(description="게시글 ID")
    content: str = Field(description="댓글 내용")
    author: AuthorResponse = Field(description="작성자")
    created_at: datetime | None = Field(None, description="작성일시")
    modified_at: datetime | None = Field(None, description="수정일시")

    @classmethod
    def from_domain(cls, comment: Comment) -> "CommentResponse":
        return cls(
            comment_id=comment.comment_id,
            post_id=comment.post_id,
            content=comment.content,
            author=AuthorResponse.from_domain(comment.author),
            created_at=comment.created_at,
            modified_at=comment.modified_at,
        )
```

### 5-17. `src/board/presentation/dependencies.py`

튜터님 코드는 라우터마다 "회원이면 회원 작성자, 아니면 비회원 작성자" 코드를 반복했습니다. `build_author()` 하나로 모았고, 비회원 정보가 없으면 **필드별 에러(422)**로 알려줍니다.

```python
# src/board/presentation/dependencies.py
from typing import Annotated
from fastapi import Depends

from board.application.service import AttachmentService, BoardService, CommentService, PostService
from board.domain.enums import Role
from board.domain.post import Author
from common.exception import ValidationException

"""
FastAPI Depends 자리표시자 모음 (실제 구현은 wiring/board.py 에서 연결)
"""


def provide_board_service() -> BoardService:
    raise NotImplementedError("BoardService 의존성이 주입되지 않았습니다.")


def provide_post_service() -> PostService:
    raise NotImplementedError("PostService 의존성이 주입되지 않았습니다.")


def provide_comment_service() -> CommentService:
    raise NotImplementedError("CommentService 의존성이 주입되지 않았습니다.")


def provide_attachment_service() -> AttachmentService:
    raise NotImplementedError("AttachmentService 의존성이 주입되지 않았습니다.")


async def get_current_role() -> Role | None:
    """요청자의 권한 - 비회원: None / 회원: Role.USER / 관리자: Role.ADMIN"""
    raise NotImplementedError("get_current_role 의존성이 주입되지 않았습니다.")


async def get_current_author() -> Author | None:
    """요청자의 작성자 정보 - 회원: Author.member(...) / 비회원: None"""
    raise NotImplementedError("get_current_author 의존성이 주입되지 않았습니다.")


async def require_admin_role() -> Role:
    """관리자만 통과 (게시판 설정 변경용)"""
    raise NotImplementedError("require_admin_role 의존성이 주입되지 않았습니다.")


# 라우터에서 짧게 쓰기 위한 별칭
CurrentRole = Annotated[Role | None, Depends(get_current_role)]
CurrentAuthor = Annotated[Author | None, Depends(get_current_author)]
AdminRole = Annotated[Role, Depends(require_admin_role)]


def build_author(current_author: Author | None, guest_name: str | None, guest_password: str | None) -> tuple[Author, str | None]:
    """
    글/댓글 작성자를 결정한다.
    - 로그인 회원: 토큰의 회원 정보 사용 (guest_* 값은 무시)
    - 비회원: guest_name, guest_password 필수
    """
    if current_author is not None:
        return current_author, None

    field_errors: dict[str, list[str]] = {}
    if not guest_name:
        field_errors["guest_name"] = ["비회원은 작성자 이름을 입력해야 합니다."]
    if not guest_password:
        field_errors["guest_password"] = ["비회원은 비밀번호(6자 이상)를 입력해야 합니다."]
    if field_errors:
        raise ValidationException("비회원 작성 정보가 부족합니다.", error_code="GUEST_INFO_REQUIRED", field_errors=field_errors)

    return Author.guest(guest_name), guest_password
```

### 5-18. 라우터 4개 (`src/board/presentation/routers/v1/`)

튜터님 코드는 라우터 파일 하나에 태그도 하나(`Boards`)였는데, Swagger에서 찾기 쉽도록 **기능별 파일·태그 4개로** 나눴습니다.

**`board_router.py`** — 게시판 설정 (관리자)

```python
# src/board/presentation/routers/v1/board_router.py
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
```

**`post_router.py`** — 게시글

- 비회원 글 삭제는 요청 **본문**에 `{"guest_password": "..."}`를 보냅니다. (튜터님 방식)

```python
# src/board/presentation/routers/v1/post_router.py
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
```

**`comment_router.py`** — 댓글

```python
# src/board/presentation/routers/v1/comment_router.py
from typing import Annotated
from fastapi import APIRouter, Body, Depends, Path, status

from board.application.service import CommentService
from board.presentation.dependencies import CurrentAuthor, CurrentRole, build_author, provide_comment_service
from board.presentation.schemas import CommentResponse, CreateCommentRequest, GuestPasswordRequest, UpdateCommentRequest
from common.schemas import APIResponse, error_responses

router = APIRouter(prefix="/v1", tags=["Comments"])

CommentServiceDep = Annotated[CommentService, Depends(provide_comment_service)]
PostId = Annotated[int, Path(ge=1, description="게시글 ID")]
CommentId = Annotated[int, Path(ge=1, description="댓글 ID")]


@router.post(
    "/posts/{post_id}/comments",
    response_model=APIResponse[CommentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="댓글 작성 (회원/비회원)",
    responses=error_responses(401, 403, 404, 422),
)
async def write_comment(
    post_id: PostId,
    body: CreateCommentRequest,
    current_author: CurrentAuthor,
    current_role: CurrentRole,
    service: CommentServiceDep,
):
    author, raw_password = build_author(current_author, body.guest_name, body.guest_password)
    comment = await service.write_comment(post_id, body.content, author, raw_password, current_role)
    return APIResponse.ok(data=CommentResponse.from_domain(comment), message="댓글이 등록되었습니다.")


@router.get(
    "/posts/{post_id}/comments",
    response_model=APIResponse[list[CommentResponse]],
    summary="댓글 목록 조회",
    responses=error_responses(403, 404),
)
async def list_comments(post_id: PostId, current_role: CurrentRole, service: CommentServiceDep):
    comments = await service.list_comments(post_id, current_role)
    return APIResponse.ok(data=[CommentResponse.from_domain(c) for c in comments])


@router.put(
    "/comments/{comment_id}",
    response_model=APIResponse[CommentResponse],
    summary="댓글 수정 (작성자/비회원 비밀번호/관리자)",
    responses=error_responses(400, 401, 403, 404, 422),
)
async def update_comment(
    comment_id: CommentId,
    body: UpdateCommentRequest,
    current_author: CurrentAuthor,
    current_role: CurrentRole,
    service: CommentServiceDep,
):
    requester_id = current_author.author_id if current_author else None
    comment = await service.update_comment(comment_id, body.content, requester_id, body.guest_password, current_role)
    return APIResponse.ok(data=CommentResponse.from_domain(comment), message="댓글이 수정되었습니다.")


@router.delete(
    "/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="댓글 삭제 (작성자/비회원 비밀번호/관리자, 소프트 삭제)",
    responses=error_responses(400, 401, 403, 404),
)
async def delete_comment(
    comment_id: CommentId,
    current_author: CurrentAuthor,
    current_role: CurrentRole,
    service: CommentServiceDep,
    body: Annotated[GuestPasswordRequest | None, Body()] = None,
):
    requester_id = current_author.author_id if current_author else None
    guest_password = body.guest_password if body else None
    await service.delete_comment(comment_id, requester_id, guest_password, current_role)
```

**`attachment_router.py`** — 첨부파일

- 다운로드는 `StreamingResponse`로 파일을 조금씩 흘려보냅니다. 한글 파일명은 `filename*=UTF-8''...` 형식이어야 깨지지 않습니다.

```python
# src/board/presentation/routers/v1/attachment_router.py
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
```

### ✅ 5단계 결론
튜터님의 게시판 설계(게시판별 권한, 회원/비회원, 소프트 삭제, 검색 6종, 매퍼)를 그대로 쓰고, 첨부파일과 캐싱을 더했습니다. 권한 판단은 domain 엔티티가, 순서 조율과 캐시는 application 서비스가 맡습니다.

---

## 6. wiring과 main.py — 조립하고 실행하기

### 6-1. `src/wiring/user.py` — 인증 의존성 구현

`resolve_optional_user`가 `Depends(provide_auth_service)` **자리표시자**를 그대로 씁니다. `dependency_overrides`는 중첩된 의존성에도 적용되기 때문에, 실행할 때는 `wiring/auth.py`의 실제 구현으로 바뀌어 들어옵니다.
(튜터님 코드는 함수 안에서 `from wiring.auth import ...`로 순환 import를 피했는데, 이 방식이 더 깔끔합니다.)

```python
# src/wiring/user.py
from typing import Annotated
from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from auth.application.service import AuthService
from auth.presentation.dependencies import BearerCredentials, provide_auth_service
from common.database import get_db
from common.exception import ForbiddenException, UnauthorizedException
from user.application.service import UserService
from user.domain.repository import UserRepository
from user.domain.service import PasswordHasher
from user.domain.user import User
from user.infrastructure.repositories import SqlAlchemyUserRepository
from user.infrastructure.security import BcryptPasswordHasher
from user.presentation.dependencies import (
    get_current_user,
    get_optional_user,
    provide_user_repository,
    provide_user_service,
    require_admin,
)

# 앱 전체에서 1개만 있으면 되는 객체 (싱글턴)
password_hasher: PasswordHasher = BcryptPasswordHasher()


def create_user_repository(session: AsyncSession = Depends(get_db)) -> UserRepository:
    return SqlAlchemyUserRepository(session)


def create_user_service(repository: UserRepository = Depends(create_user_repository)) -> UserService:
    return UserService(repository=repository, hasher=password_hasher)


async def resolve_optional_user(
    credentials: BearerCredentials,
    auth_service: Annotated[AuthService, Depends(provide_auth_service)],  # wiring/auth.py 의 구현으로 바뀌어 들어온다
    user_repo: Annotated[UserRepository, Depends(create_user_repository)],
) -> User | None:
    """[인증] 토큰이 없으면 None(비회원), 위조/만료/로그아웃된 토큰이면 401"""
    if credentials is None:
        return None

    payload = await auth_service.authenticate_token(credentials.credentials)
    user = await user_repo.find_by_id(payload.user_id)
    if user is None:
        raise UnauthorizedException("존재하지 않는 사용자입니다.", error_code="USER_NOT_FOUND")
    if user.resign:
        raise ForbiddenException("탈퇴한 회원은 서비스를 이용할 수 없습니다.", error_code="USER_ALREADY_WITHDRAWN")
    return user


async def resolve_current_user(current_user: Annotated[User | None, Depends(resolve_optional_user)]) -> User:
    """[인증] 로그인 필수"""
    if current_user is None:
        raise UnauthorizedException("로그인이 필요합니다.", error_code="TOKEN_MISSING")
    return current_user


async def resolve_require_admin(current_user: Annotated[User, Depends(resolve_current_user)]) -> User:
    """[인가] 관리자만 통과"""
    if not current_user.is_admin:
        raise ForbiddenException("관리자 권한이 필요합니다.", error_code="ADMIN_PERMISSION_DENIED")
    return current_user


def wire_user_dependencies(app: FastAPI) -> None:
    app.dependency_overrides.update(
        {
            provide_user_repository: create_user_repository,
            provide_user_service: create_user_service,
            get_optional_user: resolve_optional_user,
            get_current_user: resolve_current_user,
            require_admin: resolve_require_admin,
        }
    )
```

### 6-2. `src/wiring/auth.py`

```python
# src/wiring/auth.py
from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from auth.application.service import AuthService
from auth.domain.service import TokenProvider
from auth.infrastructure.credentials_verifier import UserCredentialVerifierImpl
from auth.infrastructure.repositories import SqlAlchemyTokenBlacklistRepository
from auth.infrastructure.security import JwtTokenProvider
from auth.presentation.dependencies import provide_auth_service
from common.database import get_db
from user.domain.repository import UserRepository
from wiring.user import create_user_repository, password_hasher

token_provider: TokenProvider = JwtTokenProvider()


def create_auth_service(
    session: AsyncSession = Depends(get_db),
    user_repository: UserRepository = Depends(create_user_repository),
) -> AuthService:
    return AuthService(
        credential_verifier=UserCredentialVerifierImpl(user_repo=user_repository, password_hasher=password_hasher),
        token_blacklist_repo=SqlAlchemyTokenBlacklistRepository(session),
        token_provider=token_provider,
    )


def wire_auth_dependencies(app: FastAPI) -> None:
    app.dependency_overrides.update({provide_auth_service: create_auth_service})
```

### 6-3. `src/wiring/board.py`

회원(`User`)을 게시판 도메인 언어(`Role`, `Author`)로 바꿔 주는 것도 여기서 합니다. 그래서 게시판 코드는 user 모듈을 직접 몰라도 됩니다.

```python
# src/wiring/board.py
from typing import Annotated
from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from board.application.service import AttachmentService, BoardService, CommentService, PostService
from board.domain.enums import Role
from board.domain.post import Author
from board.infrastructure.file_storage import LocalFileStorage
from board.infrastructure.security import BcryptPasswordHasher
from board.infrastructure.sqlalchemy.attachment_repository import SqlAlchemyAttachmentRepository
from board.infrastructure.sqlalchemy.board_repository import SqlAlchemyBoardRepository
from board.infrastructure.sqlalchemy.comment_repository import SqlAlchemyCommentRepository
from board.infrastructure.sqlalchemy.post_repository import SqlAlchemyPostRepository
from board.presentation.dependencies import (
    get_current_author,
    get_current_role,
    provide_attachment_service,
    provide_board_service,
    provide_comment_service,
    provide_post_service,
    require_admin_role,
)
from common.cache import InMemoryTTLCache
from common.config import settings
from common.database import get_db
from common.exception import ForbiddenException, UnauthorizedException
from user.domain.user import User
from user.presentation.dependencies import get_optional_user

# 앱 전체에서 1개만 있으면 되는 객체 (싱글턴)
_password_hasher = BcryptPasswordHasher()
_cache = InMemoryTTLCache(default_ttl=settings.CACHE_TTL_SECONDS)
_file_storage = LocalFileStorage(base_dir=settings.UPLOAD_DIR)


# ---------- 서비스 생성 ----------
# 같은 요청 안에서 get_db 는 한 번만 실행되므로, 아래 저장소들은 모두 "같은 세션(=같은 트랜잭션)"을 쓴다
def create_board_service(session: AsyncSession = Depends(get_db)) -> BoardService:
    return BoardService(board_repo=SqlAlchemyBoardRepository(session), cache=_cache)


def create_post_service(session: AsyncSession = Depends(get_db)) -> PostService:
    return PostService(
        post_repo=SqlAlchemyPostRepository(session),
        board_repo=SqlAlchemyBoardRepository(session),
        password_hasher=_password_hasher,
        cache=_cache,
    )


def create_comment_service(session: AsyncSession = Depends(get_db)) -> CommentService:
    return CommentService(
        comment_repo=SqlAlchemyCommentRepository(session),
        post_repo=SqlAlchemyPostRepository(session),
        board_repo=SqlAlchemyBoardRepository(session),
        password_hasher=_password_hasher,
        cache=_cache,
    )


def create_attachment_service(session: AsyncSession = Depends(get_db)) -> AttachmentService:
    return AttachmentService(
        attachment_repo=SqlAlchemyAttachmentRepository(session),
        post_repo=SqlAlchemyPostRepository(session),
        board_repo=SqlAlchemyBoardRepository(session),
        file_storage=_file_storage,
        cache=_cache,
        max_upload_bytes=settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024,
    )


# ---------- 요청자 정보 (회원 -> 게시판 도메인 언어로 변환) ----------
OptionalUserDep = Annotated[User | None, Depends(get_optional_user)]


async def _get_current_role(user: OptionalUserDep) -> Role | None:
    return Role(user.role) if user else None


async def _get_current_author(user: OptionalUserDep) -> Author | None:
    return Author.member(user_id=user.id, username=user.name) if user else None


async def _require_admin_role(role: Annotated[Role | None, Depends(_get_current_role)]) -> Role:
    if role is None:
        raise UnauthorizedException("로그인이 필요합니다.", error_code="TOKEN_MISSING")
    if role != Role.ADMIN:
        raise ForbiddenException("관리자 권한이 필요합니다.", error_code="ADMIN_PERMISSION_DENIED")
    return role


def wire_board_dependencies(app: FastAPI) -> None:
    app.dependency_overrides.update(
        {
            provide_board_service: create_board_service,
            provide_post_service: create_post_service,
            provide_comment_service: create_comment_service,
            provide_attachment_service: create_attachment_service,
            get_current_role: _get_current_role,
            get_current_author: _get_current_author,
            require_admin_role: _require_admin_role,
        }
    )
```

### 6-4. `src/wiring/__init__.py`

```python
# src/wiring/__init__.py
from fastapi import FastAPI

from wiring.auth import wire_auth_dependencies
from wiring.board import wire_board_dependencies
from wiring.user import wire_user_dependencies


def wire_dependencies(app: FastAPI) -> None:
    """presentation 의 자리표시자를 실제 구현으로 바꿔 끼운다 (도메인별로 나눠서 관리)"""
    wire_user_dependencies(app)
    wire_auth_dependencies(app)
    wire_board_dependencies(app)
```

### 6-5. `src/main.py`

- `lifespan` : 서버가 켜질 때 테이블 생성 + 기본 게시판 생성, 꺼질 때 DB 연결 정리
- `swagger_ui_parameters={"persistAuthorization": True}` : 새로고침해도 Authorize 토큰 유지
- `/` → `/docs`로 이동, `/health`는 DB 연결까지 확인

```python
# src/main.py
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.responses import RedirectResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from auth.presentation.routers.v1.router import router as auth_router
from board.infrastructure.sqlalchemy.seed import seed_default_board
from board.presentation.routers.v1.attachment_router import router as attachment_router
from board.presentation.routers.v1.board_router import router as board_router
from board.presentation.routers.v1.comment_router import router as comment_router
from board.presentation.routers.v1.post_router import router as post_router
from common.database import AsyncSessionLocal, close_db, engine, get_db
from common.exception_handlers import register_exception_handlers
from common.logger import get_logger
from common.middlewares import register_middlewares
from common.models import Base, init_models
from common.schemas import APIResponse
from user.presentation.routers.v1.router import router as user_router
from wiring import wire_dependencies

logger = get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("애플리케이션 시작 - 테이블 확인/생성 중...")
    init_models()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as session:
        await seed_default_board(session)
    logger.info("애플리케이션 준비 완료")
    yield
    await close_db()


app = FastAPI(
    title="게시판 API",
    description=(
        "JWT 인증 기반 RESTful 게시판 API 입니다. (회원/비회원/관리자)\n\n"
        "**사용 방법**: `POST /v1/users` 로 가입 → `POST /v1/auth/login` 으로 토큰 발급 → "
        "오른쪽 위 **Authorize** 버튼에 토큰을 붙여넣으면 회원으로 테스트할 수 있습니다. "
        "토큰 없이 `guest_name`/`guest_password` 를 보내면 비회원으로 글/댓글을 쓸 수 있습니다.\n\n"
        "기본 게시판 ID: `freetalk`"
    ),
    version="1.0.0",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "Users", "description": "회원가입 / 내 정보 / 탈퇴"},
        {"name": "Auth", "description": "로그인 / 로그아웃 (JWT)"},
        {"name": "Boards", "description": "게시판 설정 (생성·수정·삭제는 관리자)"},
        {"name": "Posts", "description": "게시글 CRUD, 검색, 페이지네이션"},
        {"name": "Comments", "description": "댓글 CRUD"},
        {"name": "Attachments", "description": "첨부파일 업로드/다운로드"},
        {"name": "Health", "description": "서버 상태 확인"},
    ],
    swagger_ui_parameters={"persistAuthorization": True},  # 새로고침해도 Authorize 토큰 유지
)

register_exception_handlers(app)
register_middlewares(app)
wire_dependencies(app)

app.include_router(user_router)
app.include_router(auth_router)
app.include_router(board_router)
app.include_router(post_router)
app.include_router(comment_router)
app.include_router(attachment_router)


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["Health"], summary="서버/DB 상태 확인", response_model=APIResponse[dict])
async def health(session: Annotated[AsyncSession, Depends(get_db)]):
    await session.execute(text("SELECT 1"))  # DB 연결까지 확인
    return APIResponse.ok(data={"status": "ok", "database": "ok"})
```

### 6-6. 실행

```bash
uv run uvicorn main:app --app-dir src --reload
```

- `--app-dir src` : `src` 폴더를 기준으로 import 합니다. (`from common...`가 동작하는 이유)
- 실행 위치는 `backend-api` 폴더여야 `.env`와 `storage/`가 올바른 곳에 생깁니다.

브라우저에서 http://localhost:8000/docs 를 열어 Swagger 화면이 보이면 성공입니다.

> ⚠️ `RuntimeError: JWT_SECRET_KEY 환경변수를...` → `.env`에 64자 이상 비밀키를 넣었는지 확인
> ⚠️ `ConnectionRefusedError` → `docker compose up -d db`로 DB를 띄웠는지 확인
> ⚠️ `Form data requires "python-multipart"` → `uv add python-multipart`

### ✅ 6단계 결론
`wiring/`이 도메인별로 부품을 조립하고, `main.py`가 예외 핸들러·미들웨어·라우터를 등록합니다. 실행하면 `freetalk` 게시판이 자동으로 생기고 `/docs`에서 전체 API를 볼 수 있습니다.

---

## 7. Swagger로 직접 테스트하기

http://localhost:8000/docs 에서 순서대로 해 보세요.

### 7-1. 회원/비회원 기본 흐름

| 순서 | API | 입력 | 기대 결과 |
|---|---|---|---|
| 1 | `POST /v1/users` | `{"email":"a@example.com","name":"홍길동","password":"P@ssw0rd!"}` | 201 |
| 2 | 같은 요청 한 번 더 | | 409 `EMAIL_ALREADY_EXISTS` |
| 3 | `POST /v1/users` | `{"email":"b@example.com","name":"김철수","password":"1234"}` | 422 (409 아님!) |
| 4 | `POST /v1/auth/login` | 1번 계정 | 200, `data.access_token` 복사 |
| 5 | 오른쪽 위 **Authorize** | 토큰 붙여넣기 (`Bearer ` 안 붙여도 됨) | 자물쇠 잠김 |
| 6 | `POST /v1/boards/freetalk/posts` | `{"title":"회원 글","content":"내용"}` | 201, `location` 헤더 |
| 7 | **Authorize → Logout**(비회원 상태) 후 같은 API | `{"title":"비회원 글","content":"내용","guest_name":"손님","guest_password":"123456"}` | 201, `author.is_guest: true` |
| 8 | 비회원 상태로 `PUT /v1/posts/{7번 글}` | `guest_password`를 틀리게 | 403 `POST_PERMISSION_DENIED` |
| 9 | 같은 요청, 비밀번호 맞게 | | 200 |
| 10 | `GET /v1/boards/freetalk/posts?search_type=AUTHOR_NAME&keyword=손님` | | 7번 글만 |
| 11 | 다시 Authorize 후 `POST /v1/posts/{6번 글}/attachments` | 파일 선택 | 201, `download_url` |
| 12 | `GET /v1/attachments/{id}` | | 파일 다운로드 |
| 13 | `POST /v1/auth/logout` | | 204 |
| 14 | 같은 토큰으로 `GET /v1/users/me` | | 401 `TOKEN_REVOKED` |

### 7-2. 관리자 기능

관리자 가입 API는 일부러 만들지 않았습니다. DB에서 직접 권한을 바꿉니다.

```bash
docker compose exec db psql -U postgres -d board -c "UPDATE users SET role='ADMIN' WHERE email='a@example.com';"
```

권한은 요청마다 DB에서 읽으므로 **다시 로그인하지 않아도** 바로 적용됩니다. (단, 13번에서 로그아웃했다면 다시 로그인)

| API | 입력 | 기대 결과 |
|---|---|---|
| `POST /v1/boards` | `{"board_id":"notice","board_name":"공지사항","authority":{"edit_role":"ADMIN"}}` | 201 |
| 일반 회원으로 `POST /v1/boards/notice/posts` | | 403 `BOARD_PERMISSION_DENIED` |
| 관리자로 남의 글 `DELETE /v1/posts/{id}` | | 204 |
| `DELETE /v1/boards/notice` | | 204 (소프트 삭제) |
| `GET /v1/boards?include_deleted=true` | | 삭제된 게시판도 보임 |

### ✅ 7단계 결론
Authorize 버튼으로 회원/비회원을 오가며 테스트할 수 있습니다. 성공뿐 아니라 409·422·403·401 같은 **실패 응답도 같은 모양**으로 나오는지 꼭 확인하세요.

---

## 8. 튜터님 코드와 달라진 점

### 8-1. 그대로 가져온 것 (튜터님 설계)
게시판 설정·권한(`Authority`, `Role.satisfies`), 회원/비회원 작성, 비회원 비밀번호, 소프트 삭제, 검색 6종, 값 객체(`Author`/`BoardInfo`/`GuestPassword`), 매퍼, `wiring/` 분리, `UserCredentialVerifier`, `get_optional_user`, 요청 단위 commit, `PUT` 수정, URL 구조

### 8-2. 새로 추가한 것

| 추가 | 이유 (채점 항목) |
|---|---|
| 첨부파일 업로드/다운로드/삭제 | 운영 환경 — 업로드 |
| 게시판·게시글 TTL 캐시 | 운영 환경 — 캐싱 |
| 요청 로깅 + CORS 미들웨어 | 운영 환경 — 미들웨어 |
| 404/405 핸들러, 모든 응답 `APIResponse` 통일 | Pydantic — 일관된 오류 응답 |
| Swagger 에러 응답 문서(`error_responses`), 태그 분리 | RESTful — 문서화 |
| `config.py`, 비밀키 필수화 | 보안 모범 사례 |
| 토큰 에러코드 세분화 (`TOKEN_EXPIRED`/`INVALID_TOKEN`/`TOKEN_REVOKED`/`TOKEN_MISSING`) | 인증 — 토큰 만료 처리 |
| 회원 탈퇴 API (`DELETE /v1/users/me`) | 튜터님 domain에 규칙만 있고 API가 없었음 |
| 기본 게시판 자동 생성, `/health` | 배포 후 검증 편의 |

### 8-3. 고친 것

| 위치 | 튜터님 코드 | 문제 | 이 가이드 |
|---|---|---|---|
| `DateTimeBase` | `default=datetime.now(...)` | 서버 시작 시 **한 번만** 계산 | `server_default=func.now()` |
| `UserService.register_user` | `except Exception: raise ConflictException()` | 검증 에러도 **409**로 나감 | 감싸지 않음 → 422 |
| 비밀번호 변경 | `/v1/users/{user_id}/password` (인증 없음) | **남의 비밀번호 변경 가능** | `/v1/users/me/password` + 인증 |
| 게시글 목록 `total_pages` | 라우터는 20 기준 계산 | 게시판 `page_size`≠20이면 틀림 | 서비스가 실제 크기 반환 |
| 게시판 API 응답 | `APIResponse` 없이 반환 | 응답 모양이 섞임 | 전부 `APIResponse` |
| 로그아웃 | `HTTPBearer()` | 토큰 누락 시 기본 에러 모양 | `auto_error=False` + 공통 에러 |
| 탈퇴 회원 로그인 | 검사 없음 | 탈퇴해도 토큰 발급 | `credentials_verifier`에서 차단 |
| 검색 | `icontains(keyword)` | `%`, `_`가 와일드카드로 동작 | `autoescape=True` |
| 매퍼 `to_model` | `created_at=None` 전달 | NOT NULL 오류 가능 | 전달 안 함 |
| 인덱스 | `(id, deleted_at)` | `id`가 기본키라 효과 없음 | `(board_id, deleted_at)` |
| 게시판 ID 재사용 | 삭제된 ID는 "없음"으로 판단 | 같은 ID 생성 시 PK 충돌 | 삭제된 ID도 409 |
| 중복 코드 | `_get_active_board` 등이 서비스마다 반복 | 수정 누락 위험 | 모듈 함수로 통합 |

---

## 9. GitHub에 올리기

> ℹ️ 지금 `backend-api` 폴더는 `ax_study` 저장소 안에 있습니다. 과제용으로 **별도 저장소**를 만들려면 `backend-api` 안에서 `git init`을 합니다.
> 이렇게 하면 바깥 `ax_study` 저장소는 이 폴더를 "다른 저장소"로 인식합니다. 바깥 저장소에 함께 올리지 않으려면 `ax_study/.gitignore`에 `backend-api/`를 추가하세요.

1. GitHub에서 새 저장소(예: `board-api`)를 **README 없이** 만듭니다. (배포 서버에서 받아야 하므로 Public 권장)
2. `backend-api` 폴더에서:

```bash
git init
```

```bash
git add .
```

```bash
git status
```

`git status` 결과에 **`.env`와 `.venv`가 없는지** 꼭 확인합니다.

```bash
git commit -m "feat: RESTful 게시판 API (JWT, 게시판 권한, 비회원, 첨부파일, 캐싱)"
```

```bash
git branch -M main
```

```bash
git remote add origin https://github.com/<내아이디>/board-api.git
```

```bash
git push -u origin main
```

> 💡 README.md에 "API 목록 표", "실행 방법", "배포 주소/Swagger 주소", "8번의 추가·수정한 점"을 적어 두면 평가자가 보기 좋습니다.

---

## 10. AWS EC2에 배포하기

### 10-1. 배포용 파일 2개 추가 (프로젝트 루트)

**`Dockerfile`**

```dockerfile
FROM python:3.13-slim

# uv 설치 (로컬과 같은 버전)
COPY --from=ghcr.io/astral-sh/uv:0.12.2 /uv /uvx /bin/

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# 의존성 먼저 설치 (코드만 바뀌면 이 단계는 캐시 재사용 -> 빌드가 빨라짐)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["uvicorn", "main:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
```

**`.dockerignore`**

```gitignore
.venv
__pycache__
.env
storage
.git
*.db
```

로컬에서 먼저 둘 다 띄워 보고(`http://localhost/docs`) 문제가 없으면 커밋·푸시합니다.

```bash
docker compose up -d --build
```

### 10-2. EC2 인스턴스 만들기 (AWS 콘솔)

| 항목 | 값 |
|---|---|
| AMI | Ubuntu Server 24.04 LTS |
| 인스턴스 유형 | t2.micro 또는 t3.micro (프리티어) |
| 키 페어 | 새로 만들고 `.pem` 파일 보관 |
| 보안 그룹 인바운드 | SSH 22 → **내 IP**만 / HTTP 80 → 0.0.0.0/0 |
| 스토리지 | 기본 8GB → 여유 있게 16~20GB 권장 |

> ⚠️ 5432(DB) 포트는 **열지 않습니다.** compose에서도 `127.0.0.1`에만 묶어 두었습니다.
> 💡 인스턴스를 껐다 켜면 퍼블릭 IP가 바뀝니다. 제출 주소가 바뀌지 않게 하려면 **탄력적 IP(Elastic IP)**를 연결하세요.

### 10-3. 서버 접속 후 설치

```bash
ssh -i <키파일>.pem ubuntu@<퍼블릭IP>
```

```bash
sudo apt-get update && sudo apt-get install -y docker.io docker-compose-v2 git
```

```bash
sudo usermod -aG docker ubuntu
```

`exit`로 나갔다가 다시 `ssh` 접속합니다. (docker 권한 적용)

### 10-4. 코드 받고 실행

```bash
git clone https://github.com/<내아이디>/board-api.git && cd board-api
```

```bash
cp .env.example .env && nano .env
```

운영 서버의 `.env`에서 바꿀 것:
- `JWT_SECRET_KEY` : 새로 생성 (`python3 -c "import secrets; print(secrets.token_urlsafe(64))"`)
- `POSTGRES_PASSWORD` : 추측하기 어려운 값으로 변경
- `CORS_ORIGINS` : 프론트엔드 주소가 있으면 추가

```bash
docker compose up -d --build
```

```bash
docker compose logs -f app
```

`애플리케이션 준비 완료` 로그가 보이면 `Ctrl+C`로 로그 보기만 빠져나옵니다. (서버는 계속 실행됨)

### 10-5. 관리자 지정 & 접속 확인

```bash
docker compose exec db psql -U postgres -d board -c "UPDATE users SET role='ADMIN' WHERE email='<내 이메일>';"
```

- Swagger: `http://<퍼블릭IP>/docs`
- 상태 확인: `http://<퍼블릭IP>/health`

### 10-6. 코드 수정 후 다시 배포

```bash
git pull && docker compose up -d --build
```

### ✅ 10단계 결론
Dockerfile로 앱을 이미지로 만들고, docker compose로 앱 + PostgreSQL을 한 번에 띄웁니다. EC2 보안 그룹은 22(내 IP)와 80만 열고, `http://<퍼블릭IP>/docs`가 제출할 Swagger 주소가 됩니다.

---

## 11. 제출 전 체크리스트

- [ ] `.env`가 GitHub에 올라가지 않았다 (`.env.example`만 있음)
- [ ] `http://<퍼블릭IP>/docs`가 외부(휴대폰 LTE 등)에서 열린다
- [ ] `/health`가 `"database": "ok"`를 반환한다
- [ ] `GET /v1/boards`에 `freetalk`가 보인다
- [ ] 회원 글·비회원 글 작성/수정/삭제가 된다 (비회원은 비밀번호로)
- [ ] 다른 회원이 수정하면 403, 토큰 없이 관리자 API를 부르면 401, 잘못된 입력은 422 — **모두 같은 응답 모양**
- [ ] 로그아웃한 토큰은 401 `TOKEN_REVOKED`
- [ ] 첨부파일 업로드/다운로드가 된다 (한글 파일명 포함)
- [ ] README에 GitHub 주소·배포 주소·Swagger 주소·API 목록이 있다
- [ ] 제출: **GitHub 저장소 URL** + **배포 주소(퍼블릭 IP)** + **Swagger 주소(`/docs`)**

### 알아두면 좋은 한계와 확장 아이디어
- 캐시는 commit 직전에 지워집니다. 아주 짧은 순간 다른 요청이 옛 데이터를 다시 캐시에 넣을 수 있지만, TTL(60초)이 지나면 자동으로 정리됩니다. 서버가 여러 대가 되면 Redis로 바꾸는 것이 정석입니다.
- bcrypt 해싱은 CPU를 쓰는 동기 작업이라, 요청이 몰리면 `fastapi.concurrency.run_in_threadpool`로 감싸는 것이 좋습니다.
- `create_all` 대신 Alembic으로 DB 마이그레이션 관리
- 게시글 목록에 댓글 수(`comment_count`)를 서브쿼리로 함께 조회

---

## 🔚 전체 결론

1. **환경**: uv + `.env` + Docker PostgreSQL
2. **공통 부품**: 설정·요청 단위 트랜잭션·커스텀 예외·공통 응답·미들웨어·캐시
3. **user → auth → board** 순서로, 각각 **domain → application → infrastructure → presentation** 안쪽부터 작성
4. **wiring/**으로 조립, **main.py**로 등록 후 `/docs`에서 회원·비회원·관리자로 테스트
5. **GitHub 푸시 → EC2에서 `docker compose up -d --build`** → 퍼블릭 IP와 `/docs` 주소 제출
