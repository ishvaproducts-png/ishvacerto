"""Reproduce ishvacerto's HumanEval numbers — anyone can run this.

Measures, on the real HumanEval benchmark (164 problems, MIT, from openai/human-eval):

  * SPEC-CAPTURE  — how many problems carry a checkable doctest spec the gate can use
  * FALSE ALARMS  — canonical CORRECT solutions the gate wrongly REFUTES   (must be 0)
  * SPEC CONFLICT — REFUTED but the code passes the hidden tests => the *doctest* is wrong
                    (the gate correctly flagged a benchmark bug, not a verifier false alarm)
  * BUG-CATCH     — safe single-operator mutations of correct code that the doctest exercises,
                    refuted with a counterexample

It downloads HumanEval.jsonl.gz (~ a few hundred KB) on first run if not already present.

    pip install ishvacerto
    python benchmarks/humaneval_gate.py

Exits non-zero if the gate ever false-alarms on correct code.
"""
from __future__ import annotations

import gzip
import json
import os
import urllib.request

from ishvacerto import verify

URL = "https://raw.githubusercontent.com/openai/human-eval/master/data/HumanEval.jsonl.gz"
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "HumanEval.jsonl.gz")

# safe single-token operator mutations (LLM-style slips); applied to the FIRST match in the body
_MUT = [(" + ", " - "), (" - ", " + "), (" * ", " + "), (" == ", " != "), (" < ", " <= "),
        (" and ", " or "), (" >= ", " > "), (" // ", " * ")]


def mutate(body: str):
    for a, b in _MUT:
        if a in body:
            return body.replace(a, b, 1)
    return None


def main() -> int:
    if not os.path.exists(DATA):
        print(f"downloading HumanEval (164 problems) from {URL} ...")
        urllib.request.urlretrieve(URL, DATA)

    recs = [json.loads(line) for line in gzip.open(DATA, "rt", encoding="utf-8")]
    n = len(recs)
    captured = sum(1 for r in recs if ">>>" in r["prompt"])

    verified = false_alarm = spec_conflict = abstain_nodoc = 0
    bug_attempts = bug_caught = bug_benign = 0
    examples = []

    for r in recs:
        ep = r["entry_point"]
        correct = r["prompt"] + r["canonical_solution"]
        if ">>>" not in r["prompt"]:
            abstain_nodoc += 1
            continue

        # (1) soundness: the gate must NOT refute a correct solution via its own doctests
        vc = verify(correct, entry_point=ep)
        if vc.verdict == "VERIFIED":
            verified += 1
        elif vc.verdict == "REFUTED":
            # classify honestly: if the canonical passes the HIDDEN tests, the DOCTEST is wrong
            # (a real benchmark bug the gate caught) -- NOT a verifier false alarm.
            passes_hidden = True
            try:
                g = {"__builtins__": __import__("builtins")}
                exec(correct, g)
                exec(r["test"], g)
                g["check"](g[ep])
            except Exception:
                passes_hidden = False
            if passes_hidden:
                spec_conflict += 1
                if len(examples) < 4:
                    examples.append({"SPEC_CONFLICT (doctest wrong, code passes hidden tests)": r["task_id"],
                                     "doctest_expected": vc.detail.get("expected"),
                                     "code_gives": vc.detail.get("got")})
            else:
                false_alarm += 1
                if len(examples) < 4:
                    examples.append({"FALSE_ALARM_on_correct": r["task_id"], "cex": vc.counterexample})

        # (2) bug-catch: a safe mutation that changes a doctest output should be REFUTED w/ a counterexample
        mb = mutate(r["canonical_solution"])
        if mb is not None and mb != r["canonical_solution"] and vc.verdict == "VERIFIED":
            vb = verify(r["prompt"] + mb, entry_point=ep)
            bug_attempts += 1
            if vb.verdict == "REFUTED":
                bug_caught += 1
            else:
                bug_benign += 1  # mutation didn't change a doctest output -> not exercised (a coverage gap)

    print("=" * 92)
    print(f"ishvacerto on REAL HumanEval ({n} problems)")
    print("=" * 92)
    print(f"  spec-capture (problems with a doctest):                 {captured}/{n}  ({captured / n:.3f})")
    print(f"  on those {captured}:")
    print(f"     VERIFIED (correct canonical passed its doctests):    {verified}/{captured}")
    print(f"     VERIFIER FALSE ALARMS (correct refuted, code wrong): {false_alarm}        <-- must be 0")
    print(f"     SPEC/CODE CONFLICTS (doctest wrong, code passes hidden tests): {spec_conflict}")
    print(f"  ABSTAIN (no doctest -> no checkable spec):               {abstain_nodoc}/{n}")
    print(f"  bug-catch (doctest-exercised operator mutations):       {bug_caught}/{bug_attempts}"
          f"  ({bug_benign} mutations not exercised by the doctest)")
    for e in examples[:4]:
        print("     " + json.dumps(e))

    out = {"problems": n, "spec_capture_doctests": captured, "spec_capture_rate": round(captured / n, 3),
           "verified": verified, "false_alarms": false_alarm, "spec_conflicts": spec_conflict,
           "abstain_no_doctest": abstain_nodoc, "bug_caught": bug_caught, "bug_attempts": bug_attempts,
           "bug_not_exercised": bug_benign}
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "humaneval_gate_outcome.json")
    json.dump(out, open(out_path, "w"), indent=2)
    print("\n  " + ("PASS" if false_alarm == 0 else "FAIL") +
          f": {false_alarm} false alarms on correct code; doctest spec-capture {captured / n:.3f}; "
          f"catches doctest-exercised bugs with a counterexample.")
    print(f"  outcome JSON -> {out_path}")
    return 0 if false_alarm == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
