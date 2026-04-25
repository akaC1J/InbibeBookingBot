from collections import UserDict
from threading import RLock
from typing import TypeVar, Generic, Iterator, ItemsView, Any

K = TypeVar("K")
V = TypeVar("V")


class ThreadSafeDict(UserDict[K, V], Generic[K, V]):
    _lock: RLock
    data: dict[K, V]

    def __init__(self) -> None:
        super().__init__()
        self._lock = RLock()

    def __getitem__(self, key: K) -> V:
        with self._lock:
            return super().__getitem__(key)

    def __setitem__(self, key: K, value: V) -> None:
        with self._lock:
            super().__setitem__(key, value)

    def __delitem__(self, key: K) -> None:
        with self._lock:
            super().__delitem__(key)

    def get(self, key: K, default: Any = None) -> Any:
        with self._lock:
            return super().get(key, default)

    def items(self) -> ItemsView[K, V]:
        with self._lock:
            return self.data.copy().items()

    def __iter__(self) -> Iterator[K]:
        with self._lock:
            return iter(list(self.data.keys()))
