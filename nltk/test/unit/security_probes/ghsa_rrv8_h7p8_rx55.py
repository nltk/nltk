"""GHSA-rrv8-h7p8-rx55 [high] -- ReDoS in nltk.text.Text.findall() via unvalidated user-supplied regular expressions"""

from ._base import DOS_BUDGET, FIXED, VULNERABLE, probe, timed


@probe("GHSA-rrv8-h7p8-rx55")
def _text_findall_redos():
    """Text.findall() compiled a user-supplied regex with no backstop."""
    from nltk.text import Text

    text = Text("a b c d e".split())
    try:
        seconds = timed(text.findall, "(<.*>)+" * 6 + "<zzz>")
    except Exception as exc:
        return FIXED, "hostile pattern rejected (%s)" % type(exc).__name__
    if seconds > DOS_BUDGET:
        return VULNERABLE, "findall took %.1fs" % seconds
    return FIXED, "hostile pattern completed in %.3fs" % seconds
