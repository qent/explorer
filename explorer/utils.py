"""Utility helpers for Explorer."""

from pathlib import Path


def get_file_content(path: str | Path) -> str:
    """Return the contents of a text file."""
    file_path = Path(path)
    return file_path.read_text(encoding="utf-8")