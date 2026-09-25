#!/usr/bin/env python3
"""Assemble s4_lua ootb stage: S4lua + DT_NEEDED closure (mekil, iomp5, fftw; no libmkl_*)."""

from __future__ import annotations

import argparse
import shutil
import struct
import subprocess
from pathlib import Path

from s4lua_path import find_s4lua, s4lua_name

S4_ROOT = Path(__file__).resolve().parents[2]
PRODUCT = "s4_lua"
PLATFORMS = ("linux-x86_64", "win-x86_64")


def _die(msg: str) -> None:
    raise SystemExit(f"error: {msg}")


def _readelf_dynamic(so: Path, tag: str) -> list[str]:
    r = subprocess.run(
        ["readelf", "-d", str(so)],
        check=False,
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        _die(f"readelf -d failed for {so}: {r.stderr.strip()}")
    needle = f"({tag})"
    out: list[str] = []
    for ln in r.stdout.splitlines():
        if needle not in ln or "[" not in ln or "]" not in ln:
            continue
        out.append(ln[ln.rfind("[") + 1 : ln.rfind("]")])
    return out


def _readelf_needed(path: Path) -> list[str]:
    return _readelf_dynamic(path, "NEEDED")


def _readelf_runpaths(path: Path) -> list[str]:
    rp = _readelf_dynamic(path, "RUNPATH")
    if rp:
        return rp
    return _readelf_dynamic(path, "RPATH")


def _linux_system_or_interpreter_soname(name: str) -> bool:
    if name.startswith("ld-linux"):
        return True
    for p in (
        "libc.so",
        "libm.so",
        "libdl.so",
        "libpthread.so",
        "librt.so",
        "libresolv.so",
        "libgcc_s.so",
        "libstdc++.so",
        "libgomp.so",
        "libgfortran.so",
    ):
        if name == p or name.startswith(p + "."):
            return True
    return False


def _expand_runpath_entry(entry: str, *, origin: Path) -> Path | None:
    if "$LIB" in entry or "${LIB}" in entry:
        return None
    expanded = entry.replace("$ORIGIN", str(origin)).replace("${ORIGIN}", str(origin))
    if "$" in expanded:
        return None
    return Path(expanded)


def _linux_search_dirs(path: Path, *, build_dir: Path, stage: Path) -> list[Path]:
    dirs: list[Path] = []
    seen: set[Path] = set()

    def add(p: Path) -> None:
        try:
            r = p.resolve()
        except OSError:
            return
        if r in seen or not r.is_dir():
            return
        seen.add(r)
        dirs.append(r)

    add(path.parent)
    add(stage)
    add(build_dir)
    for entry in _readelf_runpaths(path):
        for part in entry.split(":"):
            if not part:
                continue
            exp = _expand_runpath_entry(part, origin=path.parent)
            if exp is not None:
                add(exp)
    for base in (
        Path("/lib/x86_64-linux-gnu"),
        Path("/usr/lib/x86_64-linux-gnu"),
        Path("/usr/local/lib"),
    ):
        add(base)
    return dirs


def _resolve_linux_soname(soname: str, *, search_dirs: list[Path], stage: Path) -> Path:
    stage_r = stage.resolve()
    for base in search_dirs:
        if base.resolve() == stage_r and not (base / soname).is_file():
            continue
        cand = base / soname
        if cand.is_file():
            return cand.resolve()
    _die(
        f"cannot resolve shared library for soname {soname!r} "
        f"(searched build/$ORIGIN/system dirs; not ldconfig/LD_LIBRARY_PATH/MKLROOT)"
    )


def _linux_elfs(stage: Path) -> list[Path]:
    out: list[Path] = []
    for p in sorted(stage.iterdir()):
        if not p.is_file():
            continue
        if p.name == "S4lua" or p.suffix == ".so" or ".so." in p.name:
            out.append(p)
    return out


def _assert_linux_origin_only_runpath(path: Path) -> None:
    for entry in _readelf_runpaths(path):
        for part in entry.split(":"):
            if not part:
                continue
            if part in ("$ORIGIN", "${ORIGIN}"):
                continue
            _die(
                f"{path.name} RUNPATH/RPATH has non-$ORIGIN entry {part!r}; "
                f"rebuild with BUILD_WITH_INSTALL_RPATH (ootb stage forbids abs host paths)"
            )


def _vendor_linux_dt_needed(stage: Path, build_dir: Path) -> None:
    """Copy non-system DT_NEEDED into stage so $ORIGIN works without host packages."""
    for _ in range(8):
        staged = {p.name for p in stage.iterdir() if p.is_file()}
        missing: list[str] = []
        for elf in _linux_elfs(stage):
            for need in _readelf_needed(elf):
                if need in staged or _linux_system_or_interpreter_soname(need):
                    continue
                if need not in missing:
                    missing.append(need)
        if not missing:
            return
        for soname in missing:
            search: list[Path] = []
            seen: set[Path] = set()
            for elf in _linux_elfs(stage):
                for d in _linux_search_dirs(elf, build_dir=build_dir, stage=stage):
                    if d not in seen:
                        seen.add(d)
                        search.append(d)
            shutil.copy2(_resolve_linux_soname(soname, search_dirs=search, stage=stage), stage / soname)
    _die("vendor DT_NEEDED did not converge within 8 passes")


def _assert_linux_stage_self_contained(stage: Path) -> None:
    staged = {p.name for p in stage.iterdir() if p.is_file()}
    for elf in _linux_elfs(stage):
        for need in _readelf_needed(elf):
            if need in staged or _linux_system_or_interpreter_soname(need):
                continue
            _die(
                f"staged {elf.name} NEEDED {need!r} not in stage "
                f"(and not system); pack is not $ORIGIN-self-contained"
            )


def _pe_imported_dlls(path: Path) -> list[str]:
    data = path.read_bytes()
    if len(data) < 0x40 or data[:2] != b"MZ":
        _die(f"{path.name} is not a PE image")
    e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
    if e_lfanew + 24 > len(data) or data[e_lfanew : e_lfanew + 4] != b"PE\0\0":
        _die(f"{path.name} has no PE signature")
    coff = e_lfanew + 4
    nsections = struct.unpack_from("<H", data, coff + 2)[0]
    opt_size = struct.unpack_from("<H", data, coff + 16)[0]
    opt = coff + 20
    if opt + opt_size > len(data):
        _die(f"{path.name} optional header truncated")
    magic = struct.unpack_from("<H", data, opt)[0]
    if magic == 0x20B:
        dd = opt + 112
    elif magic == 0x10B:
        dd = opt + 96
    else:
        _die(f"{path.name} unknown PE magic {magic:#x}")
    if dd + 16 > len(data):
        _die(f"{path.name} missing import data directory")
    import_rva, import_size = struct.unpack_from("<II", data, dd + 8)
    if import_rva == 0 or import_size == 0:
        return []
    sections: list[tuple[int, int, int]] = []
    sec = opt + opt_size
    for i in range(nsections):
        off = sec + i * 40
        vsize, va, rawsize, raw = struct.unpack_from("<IIII", data, off + 8)
        sections.append((va, max(vsize, rawsize), raw))

    def rva_to_off(rva: int) -> int:
        for va, span, raw in sections:
            if va <= rva < va + span:
                return raw + (rva - va)
        _die(f"{path.name} RVA {rva:#x} is not in any section")
        return 0

    names: list[str] = []
    desc = rva_to_off(import_rva)
    while True:
        if desc + 20 > len(data):
            _die(f"{path.name} import descriptor truncated")
        oft, _ts, _fc, name_rva, ft = struct.unpack_from("<IIIII", data, desc)
        if oft == 0 and name_rva == 0 and ft == 0:
            break
        name_off = rva_to_off(name_rva)
        end = data.find(b"\x00", name_off)
        if end < 0:
            _die(f"{path.name} import name unterminated")
        names.append(data[name_off:end].decode("ascii"))
        desc += 20
    return names


def _win_system_dll(name: str) -> bool:
    low = name.lower()
    if low.startswith("api-ms-") or low.startswith("ext-ms-"):
        return True
    for p in (
        "kernel32.dll",
        "kernelbase.dll",
        "ntdll.dll",
        "user32.dll",
        "advapi32.dll",
        "sechost.dll",
        "rpcrt4.dll",
        "msvcrt.dll",
        "ucrtbase.dll",
        "vcruntime",
        "msvcp",
        "concrt",
        "ws2_32.dll",
        "shell32.dll",
        "ole32.dll",
        "oleaut32.dll",
        "gdi32.dll",
        "imm32.dll",
        "winmm.dll",
        "bcrypt.dll",
        "cryptbase.dll",
        "sspicli.dll",
        "powrprof.dll",
        "imagehlp.dll",
    ):
        if low == p or low.startswith(p):
            return True
    return False


def _vendor_windows_imports(stage: Path, build_dir: Path, binary: Path) -> None:
    """Copy non-system PE imports from build_dir (fftw / mekil / iomp5md)."""
    staged_bin = stage / binary.name
    for _ in range(8):
        staged = {p.name.lower(): p.name for p in stage.iterdir() if p.is_file()}
        missing: list[str] = []
        roots = [staged_bin] + sorted(stage.glob("*.dll"))
        for pe in roots:
            if not pe.is_file():
                continue
            for dll in _pe_imported_dlls(pe):
                if _win_system_dll(dll) or dll.lower() in staged:
                    continue
                if dll not in missing:
                    missing.append(dll)
        if not missing:
            return
        for dll in missing:
            src = build_dir / dll
            if not src.is_file():
                # vcpkg / oneAPI may use alternate casing
                matches = list(build_dir.glob(dll)) + list(build_dir.glob(dll.lower()))
                if not matches:
                    _die(f"ootb stage missing {dll} under {build_dir} (needed by PE import)")
                src = matches[0]
            shutil.copy2(src, stage / src.name)
            staged[src.name.lower()] = src.name
    _die("vendor PE imports did not converge within 8 passes")


def _assert_no_mkl_dso(stage: Path) -> None:
    bad = []
    for p in stage.iterdir():
        if not p.is_file():
            continue
        low = p.name.lower()
        if low.startswith("libmkl_") or low.startswith("mkl_"):
            bad.append(p.name)
        elif "mkl_sim" in low or "mkl_rt" in low:
            bad.append(p.name)
    if bad:
        _die(f"stage must not contain MKL DSOs {bad} (subset is inside mekil)")


def main() -> int:
    ap = argparse.ArgumentParser(description="Stage s4_lua ootb tree")
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

    if args.platform == "linux-x86_64":
        _assert_linux_origin_only_runpath(out / bin_name)
        _vendor_linux_dt_needed(out, build_dir)
        for elf in _linux_elfs(out):
            _assert_linux_origin_only_runpath(elf)
        _assert_linux_stage_self_contained(out)
    else:
        _vendor_windows_imports(out, build_dir, binary)

    _assert_no_mkl_dso(out)
    if not (out / bin_name).is_file():
        _die(f"stage incomplete: {bin_name}")
    if not any(p.name.startswith("libmekil") or p.name in ("mekil.dll", "libmekil.dll") for p in out.iterdir()):
        _die("stage incomplete: mekil not vendored")

    n = sum(1 for p in out.iterdir() if p.is_file())
    names = ", ".join(sorted(p.name for p in out.iterdir() if p.is_file()))
    print(f">>> stage ok → {out} (product={PRODUCT} platform={args.platform}, {n} files: {names})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
