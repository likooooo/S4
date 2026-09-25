#!/usr/bin/env python3
"""Zero-arg quality gate: build S4lua → out/build (host platform + smoke)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

S4_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent
BUILD_DIR = S4_ROOT / "out" / "build"


def main() -> int:
    if len(sys.argv) != 1:
        print("usage: ci_release.py", file=sys.stderr)
        return 1

    sys.path.insert(0, str(SCRIPTS))
    from build import host_platform  # noqa: E402

    plat = host_platform()
    cmd = [
        sys.executable,
        str(SCRIPTS / "build.py"),
        "--build-dir",
        str(BUILD_DIR),
        "--platform",
        plat,
    ]
    print(">>>", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, cwd=S4_ROOT)
    print(f">>> s4_lua ci_release 完成 platform={plat}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as e:
        raise SystemExit(e.returncode) from e
