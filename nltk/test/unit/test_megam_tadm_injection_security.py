"""Feature-file injection guards for the megam and tadm writers (CWE-93).

``write_megam_file`` / ``write_tadm_file`` serialise a training corpus into the
line-oriented, space (and, for megam, ``:``/``#``) delimited format the external
optimiser reads on stdin. The id/value/cost fields were interpolated with
``%s`` / ``str()`` / an f-string, none of which enforce a numeric shape, so a
feature id, feature value, or per-label cost carrying a space or newline (from a
hostile or buggy encoding) could split into extra fields or inject a whole new
instance line, corrupting the trained model.

The writers now require feature ids to be non-negative integers and feature
values / costs to be finite reals, whose ``str()`` is always separator free.
These tests pin both the refusals and that genuine integer-encoded corpora still
serialise unchanged.
"""

import io

import pytest

from nltk.classify.megam import _megam_int, _megam_number, write_megam_file
from nltk.classify.tadm import _tadm_int, write_tadm_file

# --- helper encodings emitting attacker-shaped fields --------------------------


class _Enc:
    """Minimal encoding stub: fixed labels, caller-supplied encode()/cost()."""

    def __init__(self, labels, vector=None, cost=None):
        self._labels = labels
        self._vector = vector
        self._cost = cost

    def labels(self):
        return self._labels

    def encode(self, featureset, label):
        return self._vector

    # only present when a cost is supplied (write_megam_file uses hasattr)
    def __getattr__(self, name):
        if name == "cost" and self.__dict__.get("_cost") is not None:
            return lambda fs, label, l: self._cost(l)
        raise AttributeError(name)


def _megam(enc, **kw):
    buf = io.StringIO()
    write_megam_file([({"x": 1}, enc.labels()[0])], enc, buf, **kw)
    return buf.getvalue()


def _tadm(enc):
    buf = io.StringIO()
    write_tadm_file([({"x": 1}, enc.labels()[0])], enc, buf)
    return buf.getvalue()


# --- megam feature id/value injection ------------------------------------------


@pytest.mark.parametrize(
    "bad_fid",
    ["7\n0 99", "9 9", "3\t4", "5#6", "1:2", -1, 1.5, "12", True, None],
)
def test_megam_rejects_non_integer_feature_id(bad_fid):
    enc = _Enc(["yes", "no"], vector=[(bad_fid, 1)])
    with pytest.raises(ValueError, match="non-negative integer"):
        _megam(enc, bernoulli=True, explicit=False)


@pytest.mark.parametrize("bad_fval", ["1 2", "3\n4", "x", float("inf"), float("nan")])
def test_megam_rejects_non_numeric_feature_value(bad_fval):
    enc = _Enc(["yes", "no"], vector=[(1, bad_fval)])
    with pytest.raises(ValueError, match="finite real number"):
        _megam(enc, bernoulli=False, explicit=False)


@pytest.mark.parametrize("bad_cost", ["0\n99 100", "1:2", "x", float("inf")])
def test_megam_rejects_injected_label_cost(bad_cost):
    enc = _Enc(["a", "b"], vector=[(1, 1)], cost=lambda l: bad_cost if l == "a" else 1)
    with pytest.raises(ValueError, match="finite real number"):
        _megam(enc, bernoulli=True, explicit=False)


def test_megam_helpers_accept_legit_numbers():
    assert _megam_int(0) == 0 and _megam_int(42) == 42
    assert _megam_number(1) == 1 and _megam_number(-0.5) == -0.5


# --- tadm feature id/value injection -------------------------------------------


@pytest.mark.parametrize(
    "bad", ["5\n6", "7 8", "x", float("inf"), float("nan"), True, None]
)
def test_tadm_rejects_non_numeric_fields(bad):
    enc = _Enc(["a", "b"], vector=[(bad, 1)])
    with pytest.raises(ValueError):
        _tadm(enc)


def test_tadm_helper_truncates_finite_reals_like_percent_d():
    # A finite real is truncated exactly as the original "%d" did (no injection),
    # so legitimate integer-valued floats keep working.
    assert _tadm_int(3, "feature id") == 3
    assert _tadm_int(3.9, "feature value") == 3


# --- legit corpora still serialise unchanged (real encodings, no mocks) --------


def test_real_encodings_still_serialise():
    from nltk.classify.maxent import (
        BinaryMaxentFeatureEncoding,
        TadmEventMaxentFeatureEncoding,
        TypedMaxentFeatureEncoding,
    )

    train = [
        ({"a": 1, "b": "x"}, "pos"),
        ({"a": 2, "b": "y"}, "neg"),
        ({"a": 1, "b": "y"}, "pos"),
    ]

    benc = BinaryMaxentFeatureEncoding.train(train)
    buf = io.StringIO()
    write_megam_file(train, benc, buf, bernoulli=True, explicit=False)
    lines = buf.getvalue().splitlines()
    assert len(lines) == len(train)
    for line in lines:  # "<label-index> <fid> <fid> ..." all integers
        assert all(tok.isdigit() for tok in line.split())

    tenc = TypedMaxentFeatureEncoding.train(train)
    buf = io.StringIO()
    write_megam_file(train, tenc, buf, bernoulli=False, explicit=False)
    assert buf.getvalue().splitlines()  # non-empty, no exception

    tadmenc = TadmEventMaxentFeatureEncoding.train(train)
    buf = io.StringIO()
    write_tadm_file(train, tadmenc, buf)
    out = buf.getvalue().splitlines()
    # length line then one line per label, repeated per instance
    assert out and out[0].isdigit()
