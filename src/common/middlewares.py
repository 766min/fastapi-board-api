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
