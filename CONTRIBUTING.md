# Contributing to ishvacerto

Thanks for your interest. `ishvacerto` has one job and one promise: **verify or abstain — never false-alarm on correct code.** Every contribution is measured against that promise.

## The one rule

A change is only acceptable if it **never causes a VERIFIED-correct function to be REFUTED.** Widening what we can check (spec capture) is welcome; loosening the gate so it guesses is not. When in doubt, the gate should **ABSTAIN**, not bluff.

## Setup

```bash
git clone https://github.com/ishvaproducts-png/ishvacerto
cd ishvacerto
pip install -e ".[dev]" || pip install -e . pytest
pytest -q
ishvacerto --demo
```

`ishvacerto` is **pure standard library** — please keep it that way. A new runtime dependency needs a strong, discussed justification.

## What helps most

- **Spec capture** — new ways to *honestly* capture a checkable spec (more doctest forms, pytest discovery, type-driven inputs). Each must come with a test proving it does **not** refute correct code.
- **Counterexamples** — clearer, smaller failing inputs on REFUTED.
- **Language targets** — verifying beyond Python.
- **Editor / CI integrations.**

## Bar for a PR

1. `pytest -q` is green and you **added a test** for the behavior you changed.
2. If you touched the gate logic, include a test that feeds it **known-correct** code and asserts it is **not** REFUTED (the anti-false-alarm guarantee).
3. No new runtime dependencies without prior discussion in an issue.
4. Keep it small and reviewable.

## Reporting a false alarm

A correct function that gets REFUTED is the highest-priority bug. Open an issue with the function, how it's correct, and the verdict you saw. That's a gate failure and we treat it as one.

By contributing you agree your contributions are licensed under the project's [MIT License](LICENSE).
