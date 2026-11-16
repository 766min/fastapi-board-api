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
