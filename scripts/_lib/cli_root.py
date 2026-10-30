#!/usr/bin/env python3
"""Load simulation_tool_database clients + wrapper from --cli-root (repo or CLI zip tree)."""

from __future__ import annotations

import shutil
import subprocess
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path


def load_cli_root(cli_root: Path) -> Path:
    """Put cli_root (and cli_root/build if present) on sys.path. Returns resolved root."""
    root = cli_root.expanduser().resolve()
    if not (root / "clients" / "user").is_dir():
        raise SystemExit(f"error: cli-root missing clients/user: {root}")
    build = root / "build"
    if build.is_dir():
        p = str(build)
        if p not in sys.path:
            sys.path.insert(0, p)
    r = str(root)
    if r not in sys.path:
        sys.path.insert(0, r)
    try:
        import simulation_tool_database_wrapper  # noqa: F401
    except ImportError as e:
        raise SystemExit(
            "error: cannot import simulation_tool_database_wrapper from "
            f"{root} (build wrapper or unpack CLI zip first): {e}"
        ) from e
    return root


def download_cli_zip(url: str, dest_dir: Path) -> Path:
    """HTTP GET full CLI zip URL → unpack under dest_dir/cli. Non-2xx hard fails."""
    if not url or not str(url).strip():
        raise SystemExit("error: --cli-download-url must be a non-empty full URL")
    dest_dir = dest_dir.expanduser().resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)
    zip_path = dest_dir / "simdb_cli.zip"
    try:
        with urllib.request.urlopen(url) as resp:
            status = getattr(resp, "status", None)
            if status is not None and status != 200:
                raise SystemExit(f"error: cli download HTTP {status}: {url}")
            zip_path.write_bytes(resp.read())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"error: cli download HTTP {e.code}: {url}") from e
    except urllib.error.URLError as e:
        raise SystemExit(f"error: cli download failed: {url}: {e}") from e
    extract = dest_dir / "cli"
    if extract.exists():
        shutil.rmtree(extract)
    extract.mkdir(parents=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract)
    # Zip may contain a single top-level directory.
    kids = [p for p in extract.iterdir()]
    if len(kids) == 1 and kids[0].is_dir() and (kids[0] / "clients" / "user").is_dir():
        return kids[0]
    return extract


def resolve_cli_root(
    *,
    cli_root: Path | None,
    cli_download_url: str | None,
    work: Path,
) -> Path:
    """Exactly one of --cli-root or --cli-download-url; returns loadable root."""
    has_root = cli_root is not None
    has_url = bool(cli_download_url and str(cli_download_url).strip())
    if has_root and has_url:
        raise SystemExit("error: pass only one of --cli-root or --cli-download-url")
    if not has_root and not has_url:
        raise SystemExit("error: require --cli-root or --cli-download-url")
    if has_root:
        assert cli_root is not None
        return load_cli_root(cli_root)
    assert cli_download_url is not None
    unpacked = download_cli_zip(cli_download_url, work / "cli_bootstrap")
    return load_cli_root(unpacked)


def segment_ok(s: str) -> bool:
    if not s or len(s) > 128 or "__" in s:
        return False
    return all((c.islower() or c.isdigit() or c in "-_") for c in s)


def sha256_hex_ok(s: str) -> bool:
    if len(s) != 64:
        return False
    return all(c in "0123456789abcdef" for c in s)


def commit12_hex_ok(s: str) -> bool:
    if len(s) != 12:
        return False
    return all(c in "0123456789abcdef" for c in s)


def require_clean_git(repo: Path) -> None:
    r = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain"],
        check=False,
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        raise SystemExit(f"error: git status failed in {repo}: {r.stderr.strip()}")
    if r.stdout.strip():
        raise SystemExit(f"error: dirty working tree in {repo}; commit or stash before release")
