"""ishvacerto tests -- the gate must: verify correct code, refute buggy code with a counterexample, abstain when it can't
capture a spec, and NEVER false-alarm on correct code (including recursion + input-mutating functions)."""
import json

from ishvacerto import verify, verify_against_reference
from ishvacerto.cli import main


def test_doctest_verified():
    assert verify('def f(n):\n    """sq.\n    >>> f(3)\n    9\n    >>> f(2)\n    4\n    """\n    return n*n\n').verdict == "VERIFIED"


def test_doctest_refuted_with_counterexample():
    v = verify('def f(n):\n    """sq.\n    >>> f(3)\n    9\n    """\n    return n+n\n')
    assert v.verdict == "REFUTED" and v.counterexample == "f(3)" and v.spec_source == "doctest"


def test_given_tests():
    assert verify("def g(a,b):\n    return a+b\n", tests=[("g(2,3)", "5"), "assert g(0,0)==0"]).verdict == "VERIFIED"
    assert verify("def g(a,b):\n    return a-b\n", tests=[("g(2,3)", "5")]).verdict == "REFUTED"


def test_abstain_without_spec():
    assert verify("def h(x):\n    return x*x\n").verdict == "ABSTAIN"
    assert verify("x = 1 + 1\n").verdict == "ABSTAIN"


def test_unparseable_doctest_abstains_not_refutes():
    # a print-style doctest can't be compared as a return value -> ABSTAIN, never a false REFUTE on correct code
    assert verify('def f(n):\n    """\n    >>> print(f(3))\n    9\n    """\n    return n*n\n').verdict == "ABSTAIN"


def test_recursion_does_not_false_alarm():
    code = 'def fib(n):\n    """\n    >>> fib(7)\n    13\n    """\n    return n if n < 2 else fib(n-1) + fib(n-2)\n'
    assert verify(code).verdict == "VERIFIED"


def test_differential_refutes_with_counterexample():
    v = verify_against_reference("def f(n):\n    return n*3\n", "def f(n):\n    return n*n*n\n", "f")
    assert v.verdict == "REFUTED" and v.counterexample


def test_differential_verifies_equivalent():
    v = verify_against_reference("def f(a,b):\n    return a+b\n", "def f(a,b):\n    return b+a\n", "f")
    assert v.verdict == "VERIFIED"


def test_differential_no_false_alarm_on_input_mutating_fn():
    # reference MUTATES its input (reverse in place) but is equivalent to the candidate (both return the last element).
    # Without per-call deep-copy the reference would corrupt the candidate's input -> a FALSE REFUTE. With it -> VERIFIED.
    ref = "def f(xs):\n    xs.reverse()\n    return xs[0]\n"
    cand = "def f(xs):\n    return xs[-1]\n"
    assert verify_against_reference(cand, ref, "f").verdict == "VERIFIED"


def test_verdict_is_falsey_only_when_refuted():
    assert bool(verify('def f(n):\n    """\n    >>> f(1)\n    1\n    """\n    return n*n\n'))           # VERIFIED -> truthy
    assert not bool(verify('def f(n):\n    """\n    >>> f(3)\n    9\n    """\n    return n+n\n'))       # REFUTED -> falsey


# --- CLI --json contract: one JSON object on stdout, same exit codes as the human path ---------------------

def _run_json(tmp_path, code, capsys, extra=None):
    f = tmp_path / "snippet.py"
    f.write_text(code, encoding="utf-8")
    rc = main([str(f), "--json", *(extra or [])])
    out = capsys.readouterr().out.strip()
    return rc, json.loads(out)


def test_cli_json_verified_exit0(tmp_path, capsys):
    rc, obj = _run_json(tmp_path, 'def f(n):\n    """sq.\n    >>> f(3)\n    9\n    """\n    return n*n\n', capsys)
    assert rc == 0
    assert set(obj) == {"verdict", "entry_point", "spec_source", "counterexample", "detail"}
    assert obj["verdict"] == "VERIFIED" and obj["entry_point"] == "f" and obj["spec_source"] == "doctest"


def test_cli_json_refuted_exit1_with_counterexample(tmp_path, capsys):
    rc, obj = _run_json(tmp_path, 'def f(n):\n    """sq.\n    >>> f(3)\n    9\n    """\n    return n+n\n', capsys)
    assert rc == 1                                           # REFUTED gates CI
    assert obj["verdict"] == "REFUTED" and obj["counterexample"] == "f(3)"


def test_cli_json_abstain_exit0(tmp_path, capsys):
    rc, obj = _run_json(tmp_path, 'def h(x):\n    return x*x\n', capsys)
    assert rc == 0                                           # ABSTAIN passes the gate
    assert obj["verdict"] == "ABSTAIN" and obj["entry_point"] == "h"
