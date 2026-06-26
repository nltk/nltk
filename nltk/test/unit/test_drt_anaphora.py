"""Regression tests for the quadratic time+memory DoS in DRT anaphora
resolution (CWE-770; CVE-2026-12873).

``nltk.sem.drt.resolve_anaphora`` resolves each pronoun condition by scanning
every discourse referent on the trail and retaining the compatible ones as
candidate antecedents. A DRS with N referents and N ``PRO`` conditions therefore
costs O(N**2) time and retained memory, so a small crafted DRS string exhausts
the process. The total number of (pronoun, referent) examinations is now bounded
by ``MAX_ANAPHORA_OPERATIONS``; once exceeded, resolution raises
``AnaphoraResolutionException``.
"""

import math

import pytest

from nltk.sem import drt
from nltk.sem.drt import (
    MAX_ANAPHORA_OPERATIONS,
    AnaphoraResolutionException,
    DrtExpression,
    resolve_anaphora,
)

dexpr = DrtExpression.fromstring


def _flat_drs(n):
    """A flat DRS string with ``n`` referents and ``n`` PRO conditions."""
    refs = ",".join(f"x{i}" for i in range(n))
    conds = ",".join(f"PRO(x{i})" for i in range(n))
    return f"([{refs}],[{conds}])"


def test_max_anaphora_operations_is_a_finite_positive_int():
    assert isinstance(MAX_ANAPHORA_OPERATIONS, int)
    assert MAX_ANAPHORA_OPERATIONS > 0


def test_resolution_examples_preserved():
    # The documented resolve_anaphora outputs must be unchanged.
    assert (
        str(resolve_anaphora(dexpr(r"([x,y,z],[dog(x), cat(y), walks(z), PRO(z)])")))
        == "([x,y,z],[dog(x), cat(y), walks(z), (z = [x,y])])"
    )
    assert (
        str(resolve_anaphora(dexpr(r"(([x,y],[]) + ([],[PRO(x)]))")).simplify())
        == "([x,y],[(x = y)])"
    )
    # A pronoun that resolves to nothing still raises the domain exception.
    with pytest.raises(AnaphoraResolutionException):
        resolve_anaphora(dexpr(r"([x],[walks(x), PRO(x)])"))


def test_small_discourse_resolves():
    # Well under the cap: resolves normally (every PRO gets its antecedents).
    resolved = dexpr(_flat_drs(300)).resolve_anaphora()
    assert resolved is not None


def test_oversized_discourse_is_refused(monkeypatch):
    # Drive the guard with a small cap so the test stays fast and low-memory
    # (rather than running the real 1,000,000-step budget in process). A DRS with
    # n referents and n pronouns performs n**2 candidate examinations, so n just
    # above the integer square root of the cap exceeds it. The budget then trips
    # at ~the (small) cap's worth of candidates; even without the guard this n
    # completes immediately, so a regression is detected rather than hanging.
    cap = 1000
    monkeypatch.setattr(drt, "MAX_ANAPHORA_OPERATIONS", cap)
    n = math.isqrt(cap) + 1
    with pytest.raises(AnaphoraResolutionException):
        dexpr(_flat_drs(n)).resolve_anaphora()
