"""ishvacerto -- prove AI-written code, or refute it with the exact failing input, or honestly abstain. Never guesses.

    from ishvacerto import verify, verify_against_reference
    verify(code)                              # uses the code's own doctests / supplied tests
    verify(code, tests=[("f(3)", "9")])       # against your tests
    verify_against_reference(code, ref, "f")  # differential: where does the AI code diverge from a reference?

Runs locally. Your code never leaves the machine.
"""
from .verifier import Verdict, Verifier, verify
from .differential import verify_against_reference

__version__ = "0.1.1"
__all__ = ["Verdict", "Verifier", "verify", "verify_against_reference", "__version__"]
