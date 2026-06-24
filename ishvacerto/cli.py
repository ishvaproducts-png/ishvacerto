"""ishvacerto CLI -- verify code from a file, stdin, or against a reference. Exit code 1 on REFUTED (so it gates CI)."""
from __future__ import annotations

import argparse
import json
import sys

from .verifier import verify
from .differential import verify_against_reference


def _print(v):
    src = f" [{v.spec_source}]" if v.spec_source else ""
    extra = f"  counterexample: {v.counterexample}" if v.verdict == "REFUTED" and v.counterexample else ""
    note = ""
    if v.verdict == "REFUTED" and v.detail.get("got") is not None:
        note = f"  (got {v.detail['got']!r}, expected {v.detail['expected']!r})"
    print(f"{v.verdict}{src}  fn={v.entry_point}{extra}{note}")


def _print_json(v):
    # one JSON object on stdout; values are JSON-safe strings (detail values can be arbitrary reprs)
    print(json.dumps({
        "verdict": v.verdict,
        "entry_point": v.entry_point,
        "spec_source": v.spec_source,
        "counterexample": v.counterexample,
        "detail": {k: (x if isinstance(x, (str, int, float, bool, type(None))) else repr(x))
                   for k, x in v.detail.items()},
    }))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="ishvacerto", description="Prove AI code, refute with a counterexample, or abstain.")
    ap.add_argument("file", nargs="?", help="Python file to verify (or read from stdin)")
    ap.add_argument("--ref", help="reference implementation file for differential verification")
    ap.add_argument("--entry", help="entry-point function name (auto-detected if omitted)")
    ap.add_argument("--demo", action="store_true", help="run a built-in demo")
    ap.add_argument("--json", action="store_true", help="emit the Verdict as one JSON object on stdout (same exit codes)")
    args = ap.parse_args(argv)

    emit = _print_json if args.json else _print

    if args.demo:
        if not args.json:
            print("ishvacerto demo:")
        emit(verify('def f(n):\n    """sq.\n    >>> f(3)\n    9\n    """\n    return n*n\n'))
        emit(verify('def f(n):\n    """sq.\n    >>> f(3)\n    9\n    """\n    return n+n\n'))
        emit(verify('def f(n):\n    return n*n\n'))   # no spec -> abstain
        emit(verify_against_reference("def f(n):\n    return n*3\n", "def f(n):\n    return n*n*n\n", "f"))
        return 0

    code = open(args.file, encoding="utf-8", errors="ignore").read() if args.file else sys.stdin.read()
    if args.ref:
        if not args.entry:
            print("ishvacerto: --entry is required with --ref", file=sys.stderr); return 2
        v = verify_against_reference(code, open(args.ref, encoding="utf-8").read(), args.entry)
    else:
        v = verify(code, entry_point=args.entry)
    emit(v)
    return 1 if v.verdict == "REFUTED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
