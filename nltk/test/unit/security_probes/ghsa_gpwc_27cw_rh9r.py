"""GHSA-gpwc-27cw-rh9r [draft] : Quadratic CPU exhaustion (CWE-400 / CWE-407)
in ``LegalitySyllableTokenizer.tokenize``. The onset under construction grew
with the token and was reversed on every iteration, O(n**2) on a long vowel
run.

The fix stops growing and reversing the onset once it is longer than the
longest legal onset (it can never be legal past that), so the loop is linear;
``MAX_TOKEN_LEN`` refuses oversized tokens as defence in depth.
"""

from ._base import FIXED, QUADRATIC_RATIO, VULNERABLE, probe, scaling_ratio


@probe("GHSA-gpwc-27cw-rh9r")
def _legality_onset_reversal():
    """Check the token cap, then measure the loop itself past it.

    The cap is defence in depth and the advisory is about the loop, so the cap
    is lifted on this one instance to time the loop at sizes where the pre-fix
    reversal is visibly quadratic.
    """
    from nltk.tokenize import LegalitySyllableTokenizer

    tokenizer = LegalitySyllableTokenizer(["wonderful", "sentence", "this", "is"])
    cap = tokenizer.MAX_TOKEN_LEN
    if cap >= 10**6:
        cap_note = "no effective token cap (MAX_TOKEN_LEN=%d)" % cap
    else:
        try:
            tokenizer.tokenize("a" * (cap + 1))
        except ValueError as exc:
            if "MAX_TOKEN_LEN" not in str(exc):
                return VULNERABLE, "oversized token rejected without the cap: %s" % exc
            cap_note = "oversized token refused by MAX_TOKEN_LEN"
        else:
            cap_note = "oversized token accepted, no cap"

    tokenizer.MAX_TOKEN_LEN = 10**9  # this instance only
    # Sized so a quadratic small side clears the (lowered) noise floor even on
    # a fast runner; the linear loop at 40000 chars is ~0.05 s.
    small, big = 10_000, 40_000  # big == 4 * small
    ratio = scaling_ratio(
        lambda n: tokenizer.tokenize("a" * n),
        small,
        big,
        reps=2,
        noise_floor=0.02,
        cpu_bound=True,  # the sink computes
    )
    detail = "%s; loop scales %.1fx over 4x input (%d->%d chars)" % (
        cap_note,
        ratio,
        small,
        big,
    )
    if ratio >= QUADRATIC_RATIO:
        return VULNERABLE, "onset reversed every iteration: " + detail
    return FIXED, "linear onset saturation: " + detail
