from pathlib import Path

_DATA_DIR = Path("data")
_INDENT = ""


class _Registry:
    def __init__(self, filename: str) -> None:
        self._path = _DATA_DIR / filename
        self._known: set[int] = set()
        self._loaded = False

    def _load(self) -> None:
        if self._loaded:
            return
        _DATA_DIR.mkdir(exist_ok=True)
        if self._path.exists():
            for line in self._path.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if stripped.lstrip("-").isdigit():
                    self._known.add(int(stripped))
        self._loaded = True

    def register(self, user_id: int) -> bool:
        """Записывает user_id в файл при первом обращении. Возвращает True если пользователь новый."""
        self._load()
        if user_id in self._known:
            return False
        self._known.add(user_id)
        with self._path.open("a", encoding="utf-8") as f:
            f.write(f"{_INDENT}{user_id}\n")
        return True


_tg = _Registry("tg_users.txt")
_vk = _Registry("vk_users.txt")


def register_tg_user(user_id: int) -> bool:
    return _tg.register(user_id)


def register_vk_user(user_id: int) -> bool:
    return _vk.register(user_id)
