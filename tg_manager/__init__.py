"""Bridge package path so root project can import tg_manager modules."""

from __future__ import annotations

from pathlib import Path
from pkgutil import extend_path

__path__ = extend_path(__path__, __name__)  # type: ignore[name-defined]

_inner_pkg = Path(__file__).resolve().parent / "tg_manager"
if _inner_pkg.is_dir():
    inner = str(_inner_pkg)
    if inner not in __path__:
        __path__.append(inner)
