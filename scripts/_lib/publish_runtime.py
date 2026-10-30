#!/usr/bin/env python3
"""Upload objects/<product>/<platform>/<12hex>/; then write refs (12hex pointers)."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cli_root import commit12_hex_ok, segment_ok, sha256_hex_ok  # noqa: E402

PRODUCT = "s4_lua"
PLATFORMS = ("linux-x86_64", "win-x86_64")
PACKAGE_NAME = "package.simdb"
MANIFEST_NAME = "manifest.json"
_REMOTE_ROOT_RE = re.compile(r"/[A-Za-z0-9._/-]+")


def _die(msg: str) -> None:
    raise SystemExit(f"error: {msg}")


def require_remote_root(raw: str) -> str:
    """Absolute, shell-safe remote runtime root (it feeds `rm -rf` and quoted remote commands)."""
    root = raw.rstrip("/")
    if not _REMOTE_ROOT_RE.fullmatch(root) or root == "/" or ".." in root.split("/"):
        _die(f"--remote-runtime-root must be an absolute path matching [A-Za-z0-9._/-]: {raw!r}")
    return root


def _ssh_bash(host: str, script: str, *, capture: bool = False) -> str:
    """Run a remote shell script via ssh.

    Windows OpenSSH hangs if stdout/stderr are subprocess PIPEs (capture_output)
    or if the script is fed on stdin via ``bash -s`` (EOF often never reaches
    the remote). Pass the script as one remote command and capture via temp files.
    """
    print(">>> ssh", host, flush=True)
    payload = script.replace("\r\n", "\n").replace("\r", "\n")
    out_p = err_p = None
    try:
        with tempfile.NamedTemporaryFile(delete=False) as out_f, tempfile.NamedTemporaryFile(delete=False) as err_f:
            out_p, err_p = out_f.name, err_f.name
        with open(out_p, "wb") as out, open(err_p, "wb") as err:
            r = subprocess.run(
                ["ssh", "-n", "-T", "-o", "ConnectTimeout=20", "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=8", host, payload],
                check=False,
                stdin=subprocess.DEVNULL,
                stdout=out,
                stderr=err,
            )
        out_b = Path(out_p).read_bytes()
        err_b = Path(err_p).read_bytes()
    finally:
        if out_p:
            Path(out_p).unlink(missing_ok=True)
        if err_p:
            Path(err_p).unlink(missing_ok=True)
    if r.returncode != 0:
        err = err_b.decode("utf-8", errors="replace").strip()
        out = out_b.decode("utf-8", errors="replace").strip()
        if err:
            print(err, file=sys.stderr, flush=True)
        if out and capture:
            print(out, file=sys.stderr, flush=True)
        raise subprocess.CalledProcessError(r.returncode, ["ssh", host], out_b, err_b)
    if not capture:
        if out_b:
            sys.stdout.buffer.write(out_b)
            sys.stdout.buffer.flush()
        return ""
    return out_b.decode("utf-8", errors="replace")


def _scp(srcs: list[str], dest: str) -> None:
    cmd = ["scp", "-o", "ConnectTimeout=20", *srcs, dest]
    print(">>>", " ".join(cmd), flush=True)
    # Avoid PIPE capture: Windows OpenSSH can hang with redirected stdio.
    subprocess.run(cmd, check=True, stdin=subprocess.DEVNULL)


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

    remote_base = require_remote_root(args.remote_runtime_root)
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
