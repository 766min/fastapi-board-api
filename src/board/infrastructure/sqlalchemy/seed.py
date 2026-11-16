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
