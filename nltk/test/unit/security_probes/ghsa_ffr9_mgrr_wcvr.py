"""GHSA-ffr9-mgrr-wcvr [draft] : Quadratic CPU exhaustion (CWE-400 / CWE-407)
in ``TreebankWordTokenizer.span_tokenize`` and the ``NLTKWordTokenizer`` engine
behind ``word_tokenize``. The quote-restore loop drew the matched quotes with
``list.pop(0)``, O(n) per token, so text with many quotes cost O(n**2)
(200000 quotes ran past 45 s).

The fix draws them from a ``deque`` with ``popleft`` (O(1)).
"""

from ._base import FIXED, QUADRATIC_RATIO, VULNERABLE, probe, scaling_ratio


@probe("GHSA-ffr9-mgrr-wcvr")
def _span_tokenize_quote_restore():
    """Span-tokenize a run of double quotes and measure how the time scales.

    Both engines are driven: a linear restore scales ~4x for 4x input, the
    pre-fix front pop scales super-linearly and trips the quadratic ratio.
    """
    from nltk.tokenize.destructive import NLTKWordTokenizer
    from nltk.tokenize.treebank import TreebankWordTokenizer

    # Sized so a quadratic small side clears the (lowered) noise floor even on
    # a fast runner; the linear restore at 16000 quotes is ~0.25 s.
    small, big = 4_000, 16_000  # big == 4 * small
    findings = []
    for tokenizer in (TreebankWordTokenizer(), NLTKWordTokenizer()):

        def op(n, tokenizer=tokenizer):
            list(tokenizer.span_tokenize('"' * n))

        ratio = scaling_ratio(op, small, big, reps=2, noise_floor=0.02)
        findings.append(f"{type(tokenizer).__name__} {ratio:.1f}x")
        if ratio >= QUADRATIC_RATIO:
            return (
                VULNERABLE,
                "quadratic quote restore over 4x input (%d->%d quotes): %s"
                % (
                    small,
                    big,
                    ", ".join(findings),
                ),
            )
    return FIXED, "linear quote restore over 4x input (%d->%d quotes): %s" % (
        small,
        big,
        ", ".join(findings),
    )
