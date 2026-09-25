#!/usr/bin/env python3
"""Parameterized: build → stage → pack (C++ via CLI) → publish s4_lua objects+refs.

CI / hand-publish entry: scripts/ci_release_products.py (zero-arg; fixed paths).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

S4_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent
_LIB = SCRIPTS / "_lib"
sys.path.insert(0, str(_LIB))
PLATFORMS = ("linux-x86_64", "win-x86_64")


def _run(cmd: list[str]) -> None:
    print(">>>", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="release_products: build+stage+pack+publish s4_lua")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--cli-root", type=Path, help="tool_database repo or unpacked CLI zip")
    g.add_argument("--cli-download-url", help="full URL to simdb_cli-<platform>.zip")
    ap.add_argument("--build-dir", required=True, type=Path)
    ap.add_argument("--platform", required=True, choices=PLATFORMS)
    ap.add_argument("--ssh-host", required=True)
    ap.add_argument("--remote-runtime-root", required=True)
    ap.add_argument("--channel", required=True, choices=("release", "trial"))
    ap.add_argument("--skip-build", action="store_true")
    ap.add_argument("--skip-smoke", action="store_true")
    args = ap.parse_args()

    from cli_root import require_clean_git, resolve_cli_root  # noqa: E402

    require_clean_git(S4_ROOT)

    cli_root = resolve_cli_root(
        cli_root=args.cli_root,
        cli_download_url=args.cli_download_url,
        work=S4_ROOT / "out" / "cli_bootstrap",
    )

    py = sys.executable
    build_dir = args.build_dir.resolve()

    if not args.skip_build:
        build_cmd = [
            py,
            str(SCRIPTS / "build.py"),
            "--build-dir",
            str(build_dir),
            "--platform",
            args.platform,
        ]
        if args.skip_smoke:
            build_cmd.append("--skip-smoke")
        _run(build_cmd)

    stage = S4_ROOT / "out" / "stage" / args.platform
    _run(
        [
            py,
            str(_LIB / "stage_runtime.py"),
            "--build-dir",
            str(build_dir),
            "--platform",
            args.platform,
            "--out",
            str(stage),
        ]
    )

    pack_root = S4_ROOT / "out" / "pack"
    pack_cmd = [
        py,
        str(_LIB / "pack_runtime.py"),
        "--cli-root",
        str(cli_root),
        "--stage",
        str(stage),
        "--out-root",
        str(pack_root),
        "--platform",
        args.platform,
    ]
    print(">>>", " ".join(pack_cmd), flush=True)
    proc = subprocess.run(pack_cmd, check=True, text=True, capture_output=True)
    if proc.stderr:
        print(proc.stderr, end="" if proc.stderr.endswith("\n") else "\n", file=sys.stderr)
    line = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
    print(line, flush=True)
    try:
        man = json.loads(line)
    except json.JSONDecodeError as e:
        raise SystemExit(f"error: pack stdout not JSON: {line!r}") from e
    local_obj = pack_root / "objects" / man["product"] / man["platform"] / man["version"]

    _run(
        [
            py,
            str(_LIB / "publish_runtime.py"),
            "--ssh-host",
            args.ssh_host,
            "--remote-runtime-root",
            args.remote_runtime_root,
            "--channel",
            args.channel,
            "--platform",
            args.platform,
            "--local-object-dir",
            str(local_obj),
        ]
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as e:
        raise SystemExit(e.returncode) from e
