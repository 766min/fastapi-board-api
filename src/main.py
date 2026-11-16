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
