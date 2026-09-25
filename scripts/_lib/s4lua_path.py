"""Single path to the S4lua binary (RUNTIME_OUTPUT_DIRECTORY = build dir)."""

from __future__ import annotations

from pathlib import Path


def s4lua_name(platform: str) -> str:
    return "S4lua.exe" if platform == "win-x86_64" else "S4lua"


def find_s4lua(build_dir: Path, platform: str) -> Path:
    name = s4lua_name(platform)
    binary = build_dir / name
    if not binary.is_file():
        raise SystemExit(f"error: missing {name} at {binary} (run scripts/build.py first)")
    return binary
