#!/usr/bin/env python3
"""Pack stage → objects/<product>/<platform>/<12hex>/ via tool_database C++ pack."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cli_root import commit12_hex_ok, resolve_cli_root, segment_ok, sha256_hex_ok  # noqa: E402

PRODUCT = "s4_lua"
PLATFORMS = ("linux-x86_64", "win-x86_64")
CHUNK_SIZE = 1_048_576
FORMAT = "simdb_runtime_v1"
PACKAGE_NAME = "package.simdb"
MANIFEST_NAME = "manifest.json"
ROOT = Path(__file__).resolve().parents[2]


def _die(msg: str) -> None:
    raise SystemExit(f"error: {msg}")


def _require_key() -> None:
    if not str(os.environ.get("SIMULATION_DATABASE_KEY") or "").strip():
        _die("SIMULATION_DATABASE_KEY is required (no default)")


def _git_commit12(repo: Path) -> str:
    r = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--short=12", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        _die(f"git rev-parse failed: {r.stderr.strip()}")
    ver = r.stdout.strip().lower()
    if not commit12_hex_ok(ver):
        _die(f"invalid short commit: {ver!r}")
    full = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", ver],
        check=False,
        capture_output=True,
        text=True,
    )
    if full.returncode != 0:
        _die(f"short commit not unique: {ver}")
    return ver


def main() -> int:
    ap = argparse.ArgumentParser(description="Pack s4_lua → objects/<product>/<platform>/<12hex>/")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--cli-root", type=Path)
    g.add_argument("--cli-download-url")
    ap.add_argument("--stage", type=Path, required=True)
    ap.add_argument("--out-root", type=Path, required=True)
    ap.add_argument("--platform", required=True, choices=PLATFORMS)
    ap.add_argument("--version", default=None, help="12hex commit; default: this repo HEAD short=12")
    args = ap.parse_args()

    _require_key()
    resolve_cli_root(
        cli_root=args.cli_root,
        cli_download_url=args.cli_download_url,
        work=ROOT / "out" / "cli_bootstrap",
    )
    from clients.user.runtime_package import pack_package_bytes  # noqa: E402

    stage = args.stage.resolve()
    if not stage.is_dir():
        _die(f"stage missing: {stage}")
    ver = args.version if args.version is not None else _git_commit12(ROOT)
    if not commit12_hex_ok(ver):
        _die(f"invalid version (need 12 hex): {ver!r}")
    if not segment_ok(PRODUCT) or not segment_ok(args.platform):
        _die("invalid product/platform")

    pkg = pack_package_bytes(stage)
    content_sha = hashlib.sha256(pkg).hexdigest()
    if not sha256_hex_ok(content_sha):
        _die(f"invalid content_sha256 from pack: {content_sha!r}")

    out_obj = args.out_root.resolve() / "objects" / PRODUCT / args.platform / ver
    manifest = {
        "product": PRODUCT,
        "platform": args.platform,
        "version": ver,
        "content_sha256": content_sha,
        "size": len(pkg),
        "chunk_size": CHUNK_SIZE,
        "format": FORMAT,
    }
    if out_obj.exists():
        shutil.rmtree(out_obj)
    out_obj.mkdir(parents=True, exist_ok=True)
    (out_obj / PACKAGE_NAME).write_bytes(pkg)
    (out_obj / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, sort_keys=True), flush=True)
    print(f">>> packed {out_obj}", file=sys.stderr, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
