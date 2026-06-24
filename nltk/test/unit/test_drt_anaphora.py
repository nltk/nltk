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

import pytest

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


def test_oversized_discourse_is_refused():
    # N such that N**2 exceeds the cap: resolution is refused before it can run
    # the full O(N**2) work. The budget trips at MAX_ANAPHORA_OPERATIONS, so this
    # stays bounded (~the cap's worth of candidates) and never exhausts memory --
    # even if the guard were removed, this N completes well within CI limits, so
    # the missing exception is detected rather than hanging/OOM-ing the suite.
    n = int(MAX_ANAPHORA_OPERATIONS**0.5) + 100
    with pytest.raises(AnaphoraResolutionException):
        dexpr(_flat_drs(n)).resolve_anaphora()
