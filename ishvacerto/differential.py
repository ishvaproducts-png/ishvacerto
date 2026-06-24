"""ishvacerto.differential -- verify AI-written code against a known-good REFERENCE implementation.

When you have a reference (a previous version, a spec impl, a second model's answer), ishvacerto runs the candidate and
the reference on generated inputs and returns VERIFIED / REFUTED + the exact COUNTEREXAMPLE / ABSTAIN. This is the
high-leverage mode for AI codegen: you don't need to write tests -- give a reference, ishvacerto finds where the AI code
diverges (and shows the failing input), or proves they agree on everything it could exercise, or abstains.

Inputs are GENERATED (signature-agnostic: generic values; the reference filters the valid ones; >=1 exercised input
required, else ABSTAIN -- no vacuous pass). Each run is sandboxed in a PROCESS with a hard timeout (terminated on
hang). Inputs are DEEP-COPIED per call, so a function that mutates its argument can't corrupt the other side.

NOTE: the process timeout guards against hangs; it is not a security sandbox for hostile code. Verify code you trust
the source of (e.g. your own AI assistant's output), or run inside a container.
"""
from __future__ import annotations

import copy
import multiprocessing as mp
import re

from .verifier import Verdict

_POOL = [1, 0, 5, -3, 10, "abc", "", "a b c", "hello world", "((()))", [1, 2, 3], [], [3, 1, 2],
         [5, 5, 1, 8, 2], [1.0, 2.0, 3.0], [-1, 0, 4], True, 2.5, ["a", "b", "c"], "racecar"]


def _arity(code, ep):
    m = re.search(r"def\s+" + re.escape(ep) + r"\s*\((.*?)\)\s*(->|:)", code, re.S)
    if not m:
        return None
    params = [p for p in m.group(1).split(",") if p.strip() and "self" not in p and "=" not in p]
    return len(params)


def _gen_inputs(code, ep, cap=30):
    k = _arity(code, ep)
    if k is None or k == 0 or k > 3:
        return None
    neutral = _POOL[0]
    tuples, seen = [], set()
    cand = [tuple([v] * k) for v in _POOL]
    for i in range(k):
        for v in _POOL:
            a = [neutral] * k; a[i] = v; cand.append(tuple(a))
    for t in cand:
        key = repr(t)
        if key not in seen:
            seen.add(key); tuples.append(t)
    return tuples[:cap]


def _worker(cand_code, ref_code, ep, inputs, q):
    try:
        gc = {"__builtins__": __import__("builtins")}; exec(cand_code, gc); cf = gc[ep]
        gr = {"__builtins__": __import__("builtins")}; exec(ref_code, gr); rf = gr[ep]
    except Exception:
        q.put(("ABSTAIN", "candidate or reference failed to load")); return
    valid = 0
    for args in inputs:
        try:
            r = rf(*copy.deepcopy(args))                 # reference defines validity; deepcopy -> no input aliasing
        except Exception:
            continue
        valid += 1
        try:
            g = cf(*copy.deepcopy(args))
        except Exception:
            q.put(("REFUTED", f"{ep}{args!r} (candidate raised, reference did not)")); return
        if g != r:
            q.put(("REFUTED", f"{ep}{args!r}")); return
    q.put(("VERIFIED" if valid else "ABSTAIN", None if valid else "no valid input exercised"))


def verify_against_reference(code: str, reference_code: str, entry_point: str,
                             inputs=None, timeout: int = 4) -> Verdict:
    """Differential verify: run `code` vs `reference_code` (same entry_point) on inputs -> Verdict with counterexample."""
    ins = inputs if inputs is not None else _gen_inputs(reference_code, entry_point)
    if not ins:
        return Verdict("ABSTAIN", entry_point, "differential", detail={"reason": "could not generate inputs (arity 0 or >3)"})
    q = mp.Queue()
    p = mp.Process(target=_worker, args=(code, reference_code, entry_point, ins, q))
    p.start(); p.join(timeout)
    if p.is_alive():
        p.terminate(); p.join()
        return Verdict("ABSTAIN", entry_point, "differential", detail={"reason": "timeout (possible infinite loop)"})
    try:
        verdict, cex = q.get_nowait()
    except Exception:
        return Verdict("ABSTAIN", entry_point, "differential", detail={"reason": "no result"})
    return Verdict(verdict, entry_point, "differential", counterexample=(cex or ""),
                   detail={"n_inputs": len(ins)})
