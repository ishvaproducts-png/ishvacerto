# Benchmarks

Reproducible measurements behind the claims in the README. Every number ishvacerto advertises has a script here you can run yourself.

## HumanEval gate

```bash
pip install ishvacerto
python benchmarks/humaneval_gate.py
```

Runs the verify-or-abstain gate over the real [HumanEval](https://github.com/openai/human-eval) benchmark (164 problems, MIT — downloaded on first run) and reports:

- **spec-capture** — how many problems carry a doctest the gate can check (~46%);
- **false alarms** — canonical *correct* solutions the gate wrongly refutes — **0** (the whole promise);
- **spec/code conflicts** — cases the gate refutes where the code passes the hidden tests, i.e. the benchmark's *doctest* is wrong (the gate caught a real benchmark bug, not a false alarm);
- **bug-catch** — safe single-operator mutations of correct code that the doctest exercises, refuted with a counterexample.

It writes `humaneval_gate_outcome.json` and exits non-zero if it ever false-alarms on correct code.

> What this does **not** measure: code that ships with *no* doctest/test (HumanEval's other ~54%). The gate honestly **abstains** there — coverage is a function of the spec or reference you give it, never a guess. Widening that reach (a reference proposer) is the roadmap, measured separately on the author's own verified corpus.
