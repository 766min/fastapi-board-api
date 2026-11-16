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
