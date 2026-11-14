"""Static CSS/JS shipped with the generated pages, kept as real files in src/static/."""

from functools import lru_cache
from pathlib import Path

STATIC_DIR = Path(__file__).resolve().parent / "static"


@lru_cache(maxsize=None)
def read_asset(name: str) -> str:
    # newline="" so the bytes written to output/ are exactly the bytes stored here.
    with open(STATIC_DIR / name, encoding="utf-8", newline="") as f:
        return f.read()
