"""Regression tests for ReDoS in ReviewsCorpusReader (CWE-1333).

The ``FEATURES`` regex extracts ``feature[+N]`` annotations from each review
line. With an unbounded feature label, ``re.findall`` rescans a long
bracket-less line quadratically, so a crafted corpus line can hang the reader.
The label length is now bounded, making extraction linear.
"""

import os
import re
import tempfile
import threading

from nltk.corpus.reader.reviews import FEATURES, ReviewsCorpusReader


def test_features_regex_preserves_normal_extraction():
    """The bounded regex must extract the same features as before on real data."""
    line = "battery life[+2] and the zoom[-1] are ok"
    assert FEATURES.findall(line) == [("battery life", "+2"), ("and the zoom", "-1")]
    assert FEATURES.findall("size[+3]") == [("size", "+3")]
    assert FEATURES.findall("no feature annotation here") == []


def test_features_regex_is_linear_on_crafted_line():
    """A long, bracket-less word run must not blow up (ReDoS)."""
    crafted = "word " * 50_000  # ~250 KB; ~50s on the vulnerable (quadratic) regex
    done = []
    t = threading.Thread(target=lambda: done.append(FEATURES.findall(crafted)))
    t.daemon = True
    t.start()
    t.join(timeout=10)
    assert not t.is_alive(), "FEATURES regex hung on a crafted line (ReDoS)"
    assert done == [[]]


def test_reviews_reader_does_not_hang_on_crafted_corpus():
    """End-to-end: reading a malicious review file must terminate quickly."""
    root = tempfile.mkdtemp(prefix="reviews_redos_")
    with open(os.path.join(root, "r.txt"), "w") as fh:
        fh.write("[t]title\n" + "word " * 50_000 + "\n")
    reader = ReviewsCorpusReader(root, "r.txt")

    out = []
    t = threading.Thread(target=lambda: out.append(reader.reviews()[0]))
    t.daemon = True
    t.start()
    t.join(timeout=10)
    assert not t.is_alive(), "ReviewsCorpusReader hung on a crafted corpus line (ReDoS)"
