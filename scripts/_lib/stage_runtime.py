#!/usr/bin/env python3
"""Assemble s4_lua stage: S4lua binary only (MKL stays on the runner)."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

S4_ROOT = Path(__file__).resolve().parents[2]
PRODUCT = "s4_lua"
PLATFORMS = ("linux-x86_64", "win-x86_64")


def _die(msg: str) -> None:
    raise SystemExit(f"error: {msg}")


def s4lua_name(platform: str) -> str:
    return "S4lua.exe" if platform == "win-x86_64" else "S4lua"


def find_s4lua(build_dir: Path, platform: str) -> Path:
    name = s4lua_name(platform)
    for c in (build_dir / name, build_dir / "Release" / name, build_dir / "RelWithDebInfo" / name):
        if c.is_file():
            return c
    _die(f"missing {name} under {build_dir} (run scripts/build.py first)")


def main() -> int:
    ap = argparse.ArgumentParser(description="Stage s4_lua tree")
    ap.add_argument("--build-dir", required=True, type=Path)
    ap.add_argument("--platform", required=True, choices=PLATFORMS)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    build_dir = args.build_dir.resolve()
    bin_name = s4lua_name(args.platform)
    binary = find_s4lua(build_dir, args.platform)

    out = args.out.resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    shutil.copy2(binary, out / bin_name)
    if not (out / bin_name).is_file():
        _die(f"stage incomplete: {bin_name}")

    print(f">>> stage ok → {out} (product={PRODUCT} platform={args.platform}, 1 file)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
