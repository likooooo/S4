#!/usr/bin/env python3
"""Upload objects/<product>/<platform>/<12hex>/; then write refs (12hex pointers)."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cli_root import commit12_hex_ok, segment_ok, sha256_hex_ok  # noqa: E402

PRODUCT = "s4_lua"
PLATFORMS = ("linux-x86_64", "win-x86_64")
PACKAGE_NAME = "package.simdb"
MANIFEST_NAME = "manifest.json"


def _die(msg: str) -> None:
    raise SystemExit(f"error: {msg}")


def _ssh_bash(host: str, script: str, *, capture: bool = False) -> str:
    print(">>> ssh", host, "bash -s", flush=True)
    payload = script.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    r = subprocess.run(
        ["ssh", host, "bash", "-s"],
        check=True,
        input=payload,
        capture_output=True,
    )
    if not capture:
        if r.stdout:
            sys.stdout.buffer.write(r.stdout)
            sys.stdout.buffer.flush()
        return ""
    return (r.stdout or b"").decode("utf-8", errors="replace")


def _scp(srcs: list[str], dest: str) -> None:
    cmd = ["scp", *srcs, dest]
    print(">>>", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="Publish s4_lua objects+refs via ssh/scp")
    ap.add_argument("--ssh-host", required=True)
    ap.add_argument("--remote-runtime-root", required=True)
    ap.add_argument("--channel", required=True, choices=("release", "trial"))
    ap.add_argument("--platform", required=True, choices=PLATFORMS)
    ap.add_argument(
        "--local-object-dir",
        required=True,
        type=Path,
        help="Local …/objects/<product>/<platform>/<12hex> dir",
    )
    args = ap.parse_args()

    if not segment_ok(args.platform):
        _die("platform must be charset-safe segment")

    local = args.local_object_dir.resolve()
    man = local / MANIFEST_NAME
    pkg = local / PACKAGE_NAME
    if not man.is_file() or not pkg.is_file():
        _die(f"need {man} and {pkg}")

    version = local.name
    if local.parent.name != args.platform or local.parent.parent.name != PRODUCT or local.parent.parent.parent.name != "objects":
        _die(f"local-object-dir must end with objects/{PRODUCT}/<platform>/<12hex>, got {local}")
    if not commit12_hex_ok(version):
        _die(f"invalid object commit dir name: {version}")

    content_sha = hashlib.sha256(pkg.read_bytes()).hexdigest()
    if not sha256_hex_ok(content_sha):
        _die(f"invalid package content_sha256: {content_sha}")
    meta = json.loads(man.read_text(encoding="utf-8"))
    if not isinstance(meta, dict) or meta.get("content_sha256") != content_sha:
        _die("manifest.content_sha256 must match package bytes")
    if meta.get("version") != version:
        _die("manifest.version must match object dir name")
    if meta.get("product") != PRODUCT or meta.get("platform") != args.platform:
        _die("manifest product/platform must match CLI args")

    remote_base = args.remote_runtime_root.rstrip("/")
    remote_obj = f"{remote_base}/objects/{PRODUCT}/{args.platform}/{version}"
    remote_refs = f"{remote_base}/refs/{PRODUCT}/{args.platform}"

    _ssh_bash(
        args.ssh_host,
        "set -euo pipefail\n"
        f'mkdir -p "{remote_base}/objects/{PRODUCT}/{args.platform}"\n'
        f'rm -rf "{remote_obj}"\n'
        f'mkdir -p "{remote_obj}"\n',
    )
    _scp([str(man), str(pkg)], f"{args.ssh_host}:{remote_obj}/")

    ptr_lines = [
        f'mkdir -p "{remote_refs}"',
        f'printf "%s\\n" "{version}" > "{remote_refs}/trial"',
    ]
    if args.channel == "release":
        ptr_lines.insert(1, f'printf "%s\\n" "{version}" > "{remote_refs}/release"')

    _ssh_bash(
        args.ssh_host,
        "set -euo pipefail\n"
        f'test -f "{remote_obj}/{MANIFEST_NAME}"\n'
        f'test -f "{remote_obj}/{PACKAGE_NAME}"\n'
        f'rem=$(sha256sum "{remote_obj}/{PACKAGE_NAME}" | cut -d" " -f1)\n'
        f'if [ "$rem" != "{content_sha}" ]; then echo "error: verify content_sha256 failed: $rem" >&2; exit 1; fi\n'
        + "\n".join(ptr_lines)
        + "\n",
    )
    print(f">>> published objects/{PRODUCT}/{args.platform}/{version} refs/{PRODUCT}/{args.platform} channel={args.channel}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as e:
        raise SystemExit(e.returncode) from e
