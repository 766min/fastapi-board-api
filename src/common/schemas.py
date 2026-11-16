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
