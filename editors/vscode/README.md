# ishvacerto — verify or abstain (VS Code extension)

A thin editor front-end for the [`ishvacerto`](https://github.com/ishvaproducts-png/ishvacerto) verify-or-abstain
code gate. It runs the **local** `ishvacerto` CLI on your current Python file and reports one of three honest
outcomes — it never guesses:

| Verdict | Meaning | In the editor |
|---|---|---|
| **VERIFIED** | the code passed a captured spec (doctest / supplied tests) | diagnostics cleared + an info message |
| **REFUTED** | the code **fails**, with the exact failing input | an **Error** diagnostic carrying the inline counterexample |
| **ABSTAIN** | no checkable spec could be captured | a subtle status-bar note — **not** an error (an honest non-answer is not a failure) |

Your code never leaves the machine: the extension only shells out to the CLI you already have installed.

## Prerequisites

Install the CLI (pure stdlib Python, no runtime deps):

```
pip install ishvacerto
```

The extension calls `ishvacerto --json <file>`. If `ishvacerto` is not on your `PATH`, point the
`ishvacerto.path` setting at it — e.g. set it to `python -m ishvacerto` to use the module form.

## Run it

- **From source (one key):** open this `editors/vscode` folder in VS Code and press **F5** — that launches an
  Extension Development Host with the extension loaded. Open a Python file and run the command
  **“ishvacerto: Verify current file”** from the Command Palette.
- **As a package:** `vsce package` produces a `.vsix` you can install via *Extensions → … → Install from VSIX*.

## Settings

| Setting | Default | What it does |
|---|---|---|
| `ishvacerto.path` | `ishvacerto` | Path (or command) to the CLI. Use `python -m ishvacerto` if not on PATH. |
| `ishvacerto.verifyOnSave` | `false` | Run the gate automatically whenever a Python file is saved. |

## Command

- `ishvacerto.verifyFile` — **ishvacerto: Verify current file**

## The inline counterexample

When a function is **REFUTED**, the Error diagnostic doesn’t just say “wrong” — it shows the exact failing
call, e.g.:

```
ishvacerto REFUTED square — counterexample: square(3) (got 6, expected 9)
```

That counterexample is the bug, made concrete.

## Tests

The pure JSON parser is unit-tested headlessly (no VS Code needed):

```
node test/parse.test.js
```

`parseVerdict()` is exported from `extension.js` and deliberately does **not** import `vscode`, so it runs in
plain Node.
