#!/usr/bin/env python3
"""Compare S4 backend dump binaries (S4BDMP v1) and optionally visualize differences."""

from __future__ import annotations

import argparse
import fnmatch
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

try:
    import matplotlib.pyplot as plt
except ImportError:  # pragma: no cover
    plt = None


MAGIC = b"S4BDMP\0\x01"
DTYPE_F64 = 0
DTYPE_C128 = 1


@dataclass
class Block:
    tag: str
    dtype: int
    dims: list[int]
    data: np.ndarray


@dataclass
class CaseDump:
    name: str
    blocks: dict[str, Block] = field(default_factory=dict)


@dataclass
class DumpFile:
    path: Path
    backend: int
    cases: dict[str, CaseDump]


def _read_string(f) -> str:
    (n,) = struct.unpack("<I", f.read(4))
    return f.read(n).decode("utf-8")


def read_dump(path: Path) -> DumpFile:
    with path.open("rb") as f:
        magic = f.read(8)
        if magic != MAGIC:
            raise ValueError(f"{path}: invalid magic {magic!r}")
        version, backend, n_cases = struct.unpack("<III", f.read(12))
        if version != 1:
            raise ValueError(f"{path}: unsupported version {version}")
        f.read(8)  # timestamp
        out = DumpFile(path=path, backend=backend, cases={})
        for _ in range(n_cases):
            name = _read_string(f)
            (n_blocks,) = struct.unpack("<I", f.read(4))
            case = CaseDump(name=name)
            for _ in range(n_blocks):
                tag = _read_string(f)
                dtype, rank = struct.unpack("<II", f.read(8))
                dims = list(struct.unpack(f"<{rank}Q", f.read(8 * rank)))
                (payload_len,) = struct.unpack("<Q", f.read(8))
                payload = f.read(payload_len)
                if dtype == DTYPE_F64:
                    arr = np.frombuffer(payload, dtype=np.float64).reshape(dims)
                elif dtype == DTYPE_C128:
                    arr = np.frombuffer(payload, dtype=np.complex128).reshape(dims)
                else:
                    raise ValueError(f"unknown dtype {dtype}")
                case.blocks[tag] = Block(tag=tag, dtype=dtype, dims=dims, data=arr)
            out.cases[name] = case
        return out


def max_abs_diff(a: np.ndarray, b: np.ndarray) -> float:
    if a.shape != b.shape:
        return float("inf")
    if np.iscomplexobj(a) or np.iscomplexobj(b):
        d = np.abs(a.astype(np.complex128) - b.astype(np.complex128))
    else:
        d = np.abs(a.astype(np.float64) - b.astype(np.float64))
    return float(np.max(d)) if d.size else 0.0


def parse_case_tols(specs: list[str]) -> dict[str, float]:
    out: dict[str, float] = {}
    for spec in specs:
        if "=" not in spec:
            raise ValueError(f"invalid --case-tol {spec!r}; expected PATTERN=TOL")
        pattern, tol_text = spec.rsplit("=", 1)
        pattern = pattern.strip()
        if not pattern:
            raise ValueError(f"invalid --case-tol {spec!r}; empty pattern")
        out[pattern] = float(tol_text.strip())
    return out


def tol_for_case(case: str, default_tol: float, case_tols: dict[str, float]) -> float:
    if case in case_tols:
        return case_tols[case]
    best_tol = default_tol
    matched = False
    for pattern, tol in case_tols.items():
        if fnmatch.fnmatch(case, pattern):
            if not matched or tol > best_tol:
                best_tol = tol
                matched = True
    return best_tol


def compare_dumps(ref: DumpFile,
                  other: DumpFile,
                  tol: float,
                  case_tols: dict[str, float] | None = None) -> tuple[bool, list[dict]]:
    rows: list[dict] = []
    ok = True
    overrides = case_tols or {}
    all_cases = sorted(set(ref.cases) | set(other.cases))
    for case in all_cases:
        case_tol = tol_for_case(case, tol, overrides)
        if case not in ref.cases or case not in other.cases:
            rows.append({
                "case": case,
                "block": "*",
                "max_abs": float("inf"),
                "tol": case_tol,
                "pass": False,
            })
            ok = False
            continue
        c_ref = ref.cases[case]
        c_other = other.cases[case]
        all_blocks = sorted(set(c_ref.blocks) | set(c_other.blocks))
        for tag in all_blocks:
            if tag not in c_ref.blocks or tag not in c_other.blocks:
                rows.append({
                    "case": case,
                    "block": tag,
                    "max_abs": float("inf"),
                    "tol": case_tol,
                    "pass": False,
                })
                ok = False
                continue
            err = max_abs_diff(c_ref.blocks[tag].data, c_other.blocks[tag].data)
            passed = err <= case_tol
            rows.append({
                "case": case,
                "block": tag,
                "max_abs": err,
                "tol": case_tol,
                "pass": passed,
            })
            ok &= passed
    return ok, rows


def visualize(rows: list[dict], out_dir: Path) -> None:
    if plt is None:
        print("matplotlib not available; skipping visualization", file=sys.stderr)
        return
    out_dir.mkdir(parents=True, exist_ok=True)
    by_case: dict[str, float] = {}
    for r in rows:
        by_case[r["case"]] = max(by_case.get(r["case"], 0.0), r["max_abs"])
    cases = list(by_case.keys())
    errs = [by_case[c] for c in cases]
    fig, ax = plt.subplots(figsize=(10, max(4, 0.3 * len(cases))))
    ax.barh(cases, errs)
    ax.set_xlabel("max_abs diff")
    ax.set_title("S4 backend comparison")
    fig.tight_layout()
    fig.savefig(out_dir / "backend_compare_summary.png", dpi=120)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path, help="Reference dump (typically RNP)")
    parser.add_argument("candidate", type=Path, help="Candidate dump (typically MEKIL)")
    parser.add_argument("--tol", type=float, default=1e-12)
    parser.add_argument(
        "--case-tol",
        action="append",
        default=[],
        metavar="PATTERN=TOL",
        help="Per-case tolerance override (fnmatch pattern); may be repeated",
    )
    parser.add_argument("--visualize", action="store_true")
    parser.add_argument("--report", type=Path, default=None, help="Write text report")
    parser.add_argument("--viz-dir", type=Path, default=Path("s4_backend_compare_viz"))
    args = parser.parse_args()

    ref = read_dump(args.reference)
    cand = read_dump(args.candidate)
    case_tols = parse_case_tols(args.case_tol)
    ok, rows = compare_dumps(ref, cand, args.tol, case_tols)

    lines = [
        f"reference: {args.reference} backend={ref.backend}",
        f"candidate: {args.candidate} backend={cand.backend}",
        f"tolerance: {args.tol:g}",
    ]
    if case_tols:
        overrides = ", ".join(f"{pattern}={tol:g}" for pattern, tol in case_tols.items())
        lines.append(f"case overrides: {overrides}")
    lines.append("")
    for r in rows:
        status = "PASS" if r["pass"] else "FAIL"
        tol_note = ""
        if r["tol"] != args.tol:
            tol_note = f" tol={r['tol']:.6g}"
        lines.append(
            f"{status} case={r['case']} block={r['block']} max_abs={r['max_abs']:.6e}{tol_note}"
        )
    text = "\n".join(lines)
    print(text)
    if args.report is not None:
        args.report.write_text(text + "\n", encoding="utf-8")
    if args.visualize:
        visualize(rows, args.viz_dir)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
