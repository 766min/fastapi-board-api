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
