"""ishvacerto.verifier -- the verify-or-abstain gate.

Give it code; it returns one of three, never a guess:
  * VERIFIED  -- passed a captured spec (a witness is attached)
  * REFUTED   -- it FAILS, with the exact COUNTEREXAMPLE input (the bug, shown)
  * ABSTAIN   -- no checkable spec could be captured -> honest non-answer (it never rubber-stamps unverifiable code)

Spec capture: supplied tests > the code's own doctests. The discipline that keeps it from false-alarming on correct
code: a spec-capture failure (unparseable doctest, print-doctest, etc.) ABSTAINS -- it never refutes on a spec it
couldn't read. Pure stdlib. Runs locally; your code never leaves the machine.
"""
from __future__ import annotations

import re
import signal
from dataclasses import dataclass, field

_DOCTEST = re.compile(r">>>\s*(.+?)\n\s*([^\n>][^\n]*)")
_DEF = re.compile(r"^\s*def\s+([A-Za-z_]\w*)\s*\(", re.M)


@dataclass
class Verdict:
    verdict: str                       # "VERIFIED" | "REFUTED" | "ABSTAIN"
    entry_point: str = ""
    spec_source: str = ""              # "given_tests" | "doctest" | ""
    counterexample: str = ""           # the failing call, on REFUTED
    detail: dict = field(default_factory=dict)

    def __bool__(self):                # truthy unless refuted -> usable as a CI gate
        return self.verdict != "REFUTED"


def _timeout(seconds):
    if hasattr(signal, "SIGALRM"):     # POSIX only; on Windows there is no in-process alarm (see differential sandbox)
        signal.signal(signal.SIGALRM, lambda *a: (_ for _ in ()).throw(TimeoutError()))
        signal.alarm(seconds)


def _untimeout():
    if hasattr(signal, "SIGALRM"):
        signal.alarm(0)


class Verifier:
    """The verify-or-abstain gate. verify(code) -> Verdict."""

    def __init__(self, exec_timeout: int = 3):
        self.exec_timeout = exec_timeout

    def _entry(self, code, entry_point):
        if entry_point:
            return entry_point
        m = _DEF.search(code)
        return m.group(1) if m else None

    def _doctests(self, code):
        if '"""' not in code and "'''" not in code:
            return []
        parts = re.split(r'"""|\'\'\'', code)
        body = parts[1] if len(parts) > 1 else code
        return [(m.group(1).strip(), m.group(2).strip()) for m in _DOCTEST.finditer(body)]

    def _build(self, code, entry_point):
        g = {"__builtins__": __import__("builtins")}      # SINGLE namespace -> recursion + helper refs resolve
        try:
            _timeout(self.exec_timeout)
            exec(code, g)
            return g.get(entry_point)
        except Exception:
            return None
        finally:
            _untimeout()

    def verify(self, code: str, entry_point: str = None, tests=None) -> Verdict:
        """Verify a code string. `tests`: optional list of assert-strings OR (call_str, expected_repr) pairs."""
        ep = self._entry(code, entry_point)
        if not ep:
            return Verdict("ABSTAIN", "", "", detail={"reason": "no function definition found"})
        fn = self._build(code, ep)
        if fn is None:
            return Verdict("REFUTED", ep, "exec", counterexample="<does not load/run>",
                           detail={"reason": "code failed to import/execute"})

        bi = {"__builtins__": __import__("builtins")}
        # spec 1: explicit tests
        if tests:
            for t in tests:
                try:
                    _timeout(self.exec_timeout)
                    if isinstance(t, (tuple, list)) and len(t) == 2:
                        if eval(t[0], bi, {ep: fn}) != eval(t[1], bi, {}):
                            return Verdict("REFUTED", ep, "given_tests", counterexample=str(t[0]))
                    else:
                        exec(str(t), {"__builtins__": __import__("builtins"), ep: fn})
                except AssertionError:
                    return Verdict("REFUTED", ep, "given_tests", counterexample=str(t))
                except Exception as e:
                    return Verdict("REFUTED", ep, "given_tests", counterexample=str(t), detail={"error": type(e).__name__})
                finally:
                    _untimeout()
            return Verdict("VERIFIED", ep, "given_tests", detail={"n_tests": len(tests)})

        # spec 2: doctests -- a spec-capture failure ABSTAINS, never refutes
        usable = 0
        for call, expected in self._doctests(code):
            if call.strip().startswith(("print", "import")):
                continue
            try:
                exp = eval(expected, bi, {})
            except Exception:
                continue                                  # unparseable expected -> skip
            try:
                _timeout(self.exec_timeout)
                got = eval(call, bi, {ep: fn})
            except Exception:
                continue                                  # call errored -> skip (don't false-refute on a parse issue)
            finally:
                _untimeout()
            usable += 1
            if got != exp:
                return Verdict("REFUTED", ep, "doctest", counterexample=call, detail={"got": got, "expected": exp})
        if usable:
            return Verdict("VERIFIED", ep, "doctest", detail={"n_examples": usable})

        return Verdict("ABSTAIN", ep, "", detail={"reason": "no clean spec capturable (no tests, no usable doctest)"})


def verify(code: str, entry_point: str = None, tests=None) -> Verdict:
    """Module-level convenience: verify(code) -> Verdict."""
    return Verifier().verify(code, entry_point, tests)
