#!/usr/bin/env python3
"""Build standalone S4lua (MEKIL/mekil embed) into --build-dir. Does not configure simulation_core."""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from pathlib import Path

S4_ROOT = Path(__file__).resolve().parent.parent
PRODUCT = "s4_lua"
PLATFORMS = ("linux-x86_64", "win-x86_64")
SMOKE_LUA = S4_ROOT / "examples" / "2d" / "Fan_PRB_65_2002" / "fig12.lua"

sys.path.insert(0, str(Path(__file__).resolve().parent / "_lib"))
from s4lua_path import find_s4lua  # noqa: E402


def _die(msg: str) -> None:
    raise SystemExit(f"error: {msg}")


def host_platform() -> str:
    if sys.platform.startswith("linux"):
        return "linux-x86_64"
    if sys.platform == "win32":
        return "win-x86_64"
    _die(f"unsupported host platform: {sys.platform!r}")


def _bat_quote(s: str) -> str:
    return '"' + s.replace('"', '""') + '"'


def _load_ci_runtime_env() -> dict[str, str]:
    envpy = S4_ROOT.parent / "infrastructure" / "ci_runtime_env.py"
    if not envpy.is_file():
        _die(f"missing {envpy} (sibling infrastructure under 3rdparty)")
    out = subprocess.check_output([sys.executable, str(envpy), "--export"], text=True)
    env = os.environ.copy()
    for line in out.splitlines():
        line = line.strip()
        if not line.startswith("export "):
            continue
        assign = line[len("export ") :]
        key, sep, raw = assign.partition("=")
        if not sep or not key:
            _die(f"bad export line from ci_runtime_env: {line!r}")
        env[key] = shlex.split(raw)[0] if raw else ""
    return env


def _jobs() -> str:
    try:
        return str(os.cpu_count() or 4)
    except Exception:
        return "4"


def _vcpkg_toolchain(*, env: dict[str, str] | None = None, required: bool = True) -> Path | None:
    src = env if env is not None else os.environ
    vcpkg = src.get("VCPKG_ROOT")
    if not vcpkg or not str(vcpkg).strip():
        if required:
            _die("VCPKG_ROOT is required (no fallback)")
        return None
    toolchain = Path(vcpkg) / "scripts" / "buildsystems" / "vcpkg.cmake"
    if not toolchain.is_file():
        _die(f"VCPKG_ROOT toolchain missing: {toolchain}")
    return toolchain


def _run_via_vcvars(cmds: list[list[str]], *, cwd: Path) -> None:
    """Run cmake/build in cmd after vcvars64 (same pattern as infrastructure/build_inf.py)."""
    vcvars = os.environ.get("VCVARS64")
    if not vcvars or not str(vcvars).strip():
        _die("VCVARS64 is required for win-x86_64 build (no fallback)")
    vcvars_p = Path(vcvars)
    if not vcvars_p.is_file():
        _die(f"VCVARS64 is not a file: {vcvars_p}")
    vcpkg = os.environ.get("VCPKG_ROOT")
    if not vcpkg or not str(vcpkg).strip():
        _die("VCPKG_ROOT is required for win-x86_64 build (no fallback)")
    if not (Path(vcpkg) / "scripts" / "buildsystems" / "vcpkg.cmake").is_file():
        _die(f"VCPKG_ROOT toolchain missing under: {vcpkg}")
    mkl = os.environ.get("MKLROOT")
    if not mkl or not str(mkl).strip():
        _die("MKLROOT is required for win-x86_64 build (no fallback)")
    mkl_p = Path(mkl)
    if not mkl_p.is_dir():
        _die(f"MKLROOT is not a directory: {mkl_p}")

    lines = [
        "@echo off",
        "setlocal",
        f"call {_bat_quote(str(vcvars_p))} || exit /b 1",
        # vcvars may clobber VCPKG_ROOT; restore the configured value.
        f"set {_bat_quote('VCPKG_ROOT=' + vcpkg)}",
        f"set {_bat_quote('MKLROOT=' + str(mkl_p))}",
    ]
    for cmd in cmds:
        lines.append(" ".join(_bat_quote(a) for a in cmd) + " || exit /b 1")

    tmp = Path(os.environ.get("TEMP") or os.environ.get("TMP") or ".") / "_s4_build_lua.bat"
    tmp.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
    print(">>>", " && ".join(" ".join(_bat_quote(a) for a in c) for c in cmds), flush=True)
    subprocess.run(["cmd.exe", "/c", str(tmp)], cwd=cwd, check=True)


def _build_linux(build_dir: Path, *, skip_smoke: bool) -> Path:
    env = _load_ci_runtime_env()
    cmake = [
        "cmake",
        "-S",
        str(S4_ROOT),
        "-B",
        str(build_dir),
        "-DCMAKE_BUILD_TYPE=Release",
        "-DS4_EIGEN_BACKEND=MEKIL",
        "-DS4_ENABLE_LUA=ON",
        "-DCMAKE_ENABLE_MKL=ON",
        "-DCMAKE_SCALAR_DOUBLE=ON",
    ]
    toolchain = _vcpkg_toolchain(env=env, required=False)
    if toolchain is not None:
        cmake.append(f"-DCMAKE_TOOLCHAIN_FILE={toolchain}")
    print(">>>", " ".join(cmake), flush=True)
    subprocess.run(cmake, check=True, env=env)
    build_cmd = ["cmake", "--build", str(build_dir), "--target", "S4lua", "-j", _jobs()]
    print(">>>", " ".join(build_cmd), flush=True)
    subprocess.run(build_cmd, check=True, env=env)
    binary = find_s4lua(build_dir, "linux-x86_64")
    if not skip_smoke:
        _smoke(binary, env, build_dir)
    return binary


def _build_win(build_dir: Path, *, skip_smoke: bool) -> Path:
    # Ninja + cl after vcvars (matches infrastructure/build_inf.py Windows path).
    toolchain = _vcpkg_toolchain(required=True)
    assert toolchain is not None
    cmake = [
        "cmake",
        "-S",
        str(S4_ROOT),
        "-B",
        str(build_dir),
        "-G",
        "Ninja",
        "-DCMAKE_BUILD_TYPE=Release",
        "-DCMAKE_C_COMPILER=cl",
        "-DCMAKE_CXX_COMPILER=cl",
        f"-DCMAKE_TOOLCHAIN_FILE={toolchain}",
        "-DS4_EIGEN_BACKEND=MEKIL",
        "-DS4_ENABLE_LUA=ON",
        "-DCMAKE_ENABLE_MKL=ON",
        "-DCMAKE_SCALAR_DOUBLE=ON",
    ]
    build_cmd = ["cmake", "--build", str(build_dir), "--target", "S4lua", "-j", _jobs()]
    _run_via_vcvars([cmake, build_cmd], cwd=S4_ROOT)
    binary = find_s4lua(build_dir, "win-x86_64")
    if not skip_smoke:
        _smoke(binary, os.environ.copy(), build_dir)
    return binary


def _smoke(binary: Path, env: dict[str, str], build_dir: Path) -> None:
    if not SMOKE_LUA.is_file():
        _die(f"smoke lua missing: {SMOKE_LUA}")
    smoke_env = env.copy()
    if sys.platform.startswith("linux"):
        prev = smoke_env.get("LD_LIBRARY_PATH", "")
        smoke_env["LD_LIBRARY_PATH"] = str(build_dir) + ((":" + prev) if prev else "")
    elif sys.platform == "win32":
        prev = smoke_env.get("PATH", "")
        smoke_env["PATH"] = str(build_dir) + ((";" + prev) if prev else "")
    print(f">>> smoke: {binary} {SMOKE_LUA}", flush=True)
    proc = subprocess.run(
        [str(binary), str(SMOKE_LUA)],
        check=False,
        env=smoke_env,
        capture_output=True,
        text=True,
    )
    head = (proc.stdout or proc.stderr or "").splitlines()[:1]
    if head:
        print(head[0], flush=True)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        _die(f"S4lua smoke failed rc={proc.returncode}" + (f": {err[:500]}" if err else ""))
    if not head:
        _die("S4lua smoke failed: no output")


def main() -> int:
    ap = argparse.ArgumentParser(description="Build S4lua for s4_lua runtime product")
    ap.add_argument("--build-dir", required=True, type=Path)
    ap.add_argument("--platform", required=True, choices=PLATFORMS)
    ap.add_argument("--skip-smoke", action="store_true")
    args = ap.parse_args()

    host = host_platform()
    if args.platform != host:
        _die(f"--platform={args.platform} requires host {args.platform}, got {host}")

    if not (S4_ROOT / "CMakeLists.txt").is_file():
        _die(f"missing {S4_ROOT / 'CMakeLists.txt'}")

    build_dir = args.build_dir.resolve()
    build_dir.mkdir(parents=True, exist_ok=True)

    if args.platform == "linux-x86_64":
        binary = _build_linux(build_dir, skip_smoke=args.skip_smoke)
    else:
        binary = _build_win(build_dir, skip_smoke=args.skip_smoke)

    print(f">>> build ok → {binary} (product={PRODUCT} platform={args.platform})")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as e:
        raise SystemExit(e.returncode) from e
