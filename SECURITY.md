# Security Policy

## Scope and threat model — read this first

`ishvacerto` **executes code** in order to verify it. Differential and doctest verification run the target function in a subprocess with a timeout.

- The **timeout** guards against hangs and runaway loops. It is **not** a security sandbox.
- `ishvacerto` is designed to verify code **whose source you trust** — for example, your own AI assistant's output that you were about to run anyway. It does not make hostile code safe to execute.
- **Do not** point `ishvacerto` at untrusted or adversarial code outside a container/VM. If you must verify untrusted code, run `ishvacerto` inside an isolated sandbox (container, microVM, or a locked-down user with no network and no filesystem access).

Everything runs **locally**. `ishvacerto` makes no network calls, has no telemetry, and requires no account — your code never leaves your machine.

## Reporting a vulnerability

If you find a way that `ishvacerto`:

- reports **VERIFIED** for code that demonstrably fails its captured spec (a false negative on a bug), or
- escapes the intended local-only execution model (network egress, sandbox escape beyond the documented "not a sandbox" caveat),

please report it privately via GitHub's **"Report a vulnerability"** (Security → Advisories) on this repository, or by opening a minimal issue **without** a working exploit and asking to take it private.

Please include: version, OS/Python version, a minimal reproduction, and the observed vs. expected verdict. We aim to acknowledge within a few days.

## Supported versions

`ishvacerto` is pre-1.0. Security fixes are applied to the latest release.
