# ishvacerto

**Prove your AI-written code — or get the exact input that breaks it. Never a guess.**

AI coding assistants are fast, but they ship confident bugs and hallucinated behavior. `ishvacerto` is the gate that sits
on top of them: give it a function and a way to check it (its own doctests, your tests, or a reference
implementation), and it returns one of three answers — **never a plausible-sounding maybe**:

- ✅ **VERIFIED** — it passed the spec (with a witness).
- ❌ **REFUTED** — it fails, and here is the **exact input that breaks it**.
- 🤷 **ABSTAIN** — no checkable spec could be captured, so it says so honestly instead of rubber-stamping.

It **runs entirely on your machine. Your code never leaves it.** No account, no cloud, no telemetry. Pure standard
library — zero dependencies.

## Why

A code suggestion you can't verify is a liability. `ishvacerto` does the one thing an LLM structurally cannot: it
**proves or refutes by execution**, and when it can't, it **abstains** rather than bluff. It doesn't compete with your
AI coder — it makes its output safe to ship.

> Honest scope: `ishvacerto` verifies what it can check (functions with doctests, tests, or a reference), and **abstains on
> the rest** — it never false-alarms on correct code. "Never wrong, sometimes silent." Coverage grows as you give it
> more to check against.

## Install

```bash
pip install ishvacerto
```

## Use

**Verify against the code's own doctests:**
```bash
ishvacerto my_function.py
```

**In Python:**
```python
from ishvacerto import verify, verify_against_reference

verify(open("f.py").read())                     # uses doctests if present
verify(code, tests=[("f(3)", "9"), "assert f(0) == 0"])   # against your tests
verify_against_reference(ai_code, known_good_code, "f")   # where does the AI code diverge?
```

**Differential — the high-leverage mode (no tests needed, just a reference):**
```bash
ishvacerto --ref reference.py --entry my_func ai_generated.py
```
`ishvacerto` generates inputs, runs both, and shows the first input where they disagree.

**In CI (exit code 1 on REFUTED):**
```yaml
# .github/workflows/verify.yml
- run: pip install ishvacerto
- run: ishvacerto changed_function.py
```

## Example

```text
$ ishvacerto buggy.py
REFUTED [doctest]  fn=square  counterexample: square(3)  (got 6, expected 9)
```
There's the bug — `square(3)` returned `6`, not `9`. Not "looks suspicious." The exact failing input.

## How it decides
- **VERIFIED** only if the captured spec passed on every input it could exercise.
- **REFUTED** only on a clean mismatch — and it tells you the input.
- **ABSTAIN** if it couldn't capture a usable spec (the discipline that keeps it from false-alarming on good code).

Differential runs are sandboxed in a separate process with a timeout. The timeout guards against hangs; it is **not**
a security sandbox for hostile code — verify code whose source you trust (e.g. your own assistant's output), or run it
in a container.

## License

MIT — see [LICENSE](LICENSE).

## Status

`v0.1` — the verify-or-abstain core. On the way: richer spec capture (a reference *proposer* so it covers code that
ships with no tests), more language targets, and an editor extension. Contributions welcome.
