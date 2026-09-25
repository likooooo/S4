#!/usr/bin/env python3
"""Zero-arg product release: build → stage → pack → publish s4_lua.

Channel from HEAD subject (release* → release, else trial).
Pack CLI: HTTPS downloads/{channel}/simdb_cli-*.zip（禁止 --cli-root；禁止跨 channel）.
Host platform only (linux-x86_64 | win-x86_64).

Required env (no default): SIMULATION_DATABASE_KEY
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

S4_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent
BUILD_DIR = S4_ROOT / "out" / "build"
SSH_HOST = "aliyun"
REMOTE_RUNTIME_ROOT = "/home/like/simdb/runtime-root"
CLI_ZIP_TMPL = (
    "https://www.simulationtoolkits.com/downloads/{channel}/simdb_cli-{platform}-cp312.zip"
)


def _die(msg: str) -> None:
    raise SystemExit(f"error: {msg}")


def _channel_from_head() -> tuple[str, str]:
    subject = subprocess.check_output(
        ["git", "-C", str(S4_ROOT), "log", "-1", "--format=%s"],
        text=True,
    ).strip()
    if not subject:
        _die("git log -1 subject empty")
    channel = "release" if subject.startswith("release") else "trial"
    return subject, channel


def main() -> int:
    if len(sys.argv) != 1:
        print("usage: ci_release_products.py", file=sys.stderr)
        return 1

    if not str(os.environ.get("SIMULATION_DATABASE_KEY") or "").strip():
        _die("SIMULATION_DATABASE_KEY is required (no default)")

    sys.path.insert(0, str(SCRIPTS))
    from build import host_platform  # noqa: E402

    plat = host_platform()
    subject, channel = _channel_from_head()
    cli_url = CLI_ZIP_TMPL.format(channel=channel, platform=plat)
    print(
        f">>> ci_release_products: subject={subject!r} → channel={channel} platform={plat}",
        flush=True,
    )
    print(f">>> D4: channel-matched simdb_cli {cli_url}", flush=True)

    cmd = [
        sys.executable,
        str(SCRIPTS / "release_products.py"),
        "--cli-download-url",
        cli_url,
        "--build-dir",
        str(BUILD_DIR),
        "--platform",
        plat,
        "--ssh-host",
        SSH_HOST,
        "--remote-runtime-root",
        REMOTE_RUNTIME_ROOT,
        "--channel",
        channel,
    ]
    print(">>>", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, cwd=S4_ROOT)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as e:
        raise SystemExit(e.returncode) from e
