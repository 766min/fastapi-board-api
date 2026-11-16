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
