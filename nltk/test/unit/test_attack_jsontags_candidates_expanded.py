# Natural Language Toolkit: expanded jsontags candidate attack matrix
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Net-new candidate matrix for ``nltk.jsontags`` structured-format guards.

This file is a companion to ``test_attack_json_loaders_expanded.py`` and
``test_json_serialization.py``. It drives a broad set of plausible inputs,
benign and hostile alike, through the REAL structured-format chokepoints:

* :func:`nltk.jsontags.safe_json_loads` / :func:`nltk.jsontags.safe_json_load`
  (the depth cap ``JSON_MAX_DEPTH``, the size cap ``JSON_MAX_BYTES`` and the
  non-finite refusal every caller inherits), and
* :class:`nltk.jsontags.JSONTaggedDecoder` (the model-artifact tag decoder whose
  reconstruction is gated by a ``!``-prefixed allowlist).

Every hostile candidate is held to one hard property: it is REFUSED with a
bounded ``ValueError`` (or a clean ``TypeError`` at the type gate), never a hang
or an interpreter crash, and never a class named by an attacker. Every benign
candidate PARSES (and, for a registered tag, round-trips to the real object).

No mocking: the actual decoder / parser runs on each input.
"""

import json

import pytest

from nltk.jsontags import (
    JSON_MAX_BYTES,
    JSON_MAX_DEPTH,
    TAG_PREFIX,
    JSONTaggedDecoder,
    JSONTaggedEncoder,
    register_tag,
    safe_json_load,
    safe_json_loads,
)

# Depths comfortably past each cap while staying tiny (a few thousand bytes):
# past the loader's 2000-deep default, and past the tagged decoder's 200.
OVER_LOADER_DEPTH = JSON_MAX_DEPTH + 500
OVER_DECODER_DEPTH = JSONTaggedDecoder.MAX_DECODE_DEPTH + 300


# ===========================================================================
# 1. Deep nesting past the cap: arrays, objects, and mixed towers, on both
#    the loader chokepoint and the tagged decoder (whose super().decode drives
#    the recursive C accelerator, so it must bound depth BEFORE that call).
# ===========================================================================

DEEP_PAYLOADS = {
    "deep-array": "[" * OVER_LOADER_DEPTH + "]" * OVER_LOADER_DEPTH,
    "deep-object": '{"a":' * OVER_LOADER_DEPTH + "1" + "}" * OVER_LOADER_DEPTH,
    "deep-mixed": '{"a":[' * (OVER_LOADER_DEPTH // 2)
    + "1"
    + "]}" * (OVER_LOADER_DEPTH // 2),
}


@pytest.mark.parametrize(
    "payload", list(DEEP_PAYLOADS.values()), ids=list(DEEP_PAYLOADS)
)
def test_deep_nesting_refused_by_loader(payload):
    with pytest.raises(ValueError, match="nesting depth"):
        safe_json_loads(payload)


def test_deep_nesting_refused_by_tagged_decoder():
    over = "[" * OVER_DECODER_DEPTH + "]" * OVER_DECODER_DEPTH
    with pytest.raises(ValueError, match="nesting depth"):
        JSONTaggedDecoder().decode(over)
    # The stdlib entry point routes through the same decode(), so it is bounded.
    with pytest.raises(ValueError, match="nesting depth"):
        json.loads(over, cls=JSONTaggedDecoder)


def test_depth_exactly_at_limit_still_parses():
    # A document exactly at each depth limit is legitimate and must still load.
    assert isinstance(
        safe_json_loads("[" * JSON_MAX_DEPTH + "]" * JSON_MAX_DEPTH), list
    )
    at = (
        "[" * JSONTaggedDecoder.MAX_DECODE_DEPTH
        + "]" * JSONTaggedDecoder.MAX_DECODE_DEPTH
    )
    assert isinstance(JSONTaggedDecoder().decode(at), list)


# ===========================================================================
# 2. Oversize payload past JSON_MAX_BYTES. The default is 200 MiB; the guard
#    is exercised with a small explicit cap (the same code path every caller
#    inherits at the default) and the documented constant is pinned.
# ===========================================================================


def test_size_cap_is_the_documented_default():
    assert JSON_MAX_BYTES == 200 * 1024 * 1024
    assert JSONTaggedDecoder.MAX_DECODE_BYTES == JSON_MAX_BYTES


def test_oversize_document_refused_by_loader():
    with pytest.raises(ValueError, match="over the"):
        safe_json_loads('"' + "a" * 4000 + '"', max_bytes=100)
    # An under-cap document still parses.
    assert safe_json_loads('"' + "a" * 50 + '"', max_bytes=100) == "a" * 50


def test_oversize_document_refused_by_stream():
    import io

    with pytest.raises(ValueError, match="exceeds the|over the"):
        safe_json_load(io.BytesIO(b'"' + b"a" * 4000 + b'"'), max_bytes=100)


def test_oversize_document_refused_by_tagged_decoder():
    decoder = JSONTaggedDecoder()
    decoder.MAX_DECODE_BYTES = 100  # shrink so the test stays cheap
    with pytest.raises(ValueError, match="over the"):
        decoder.decode('"' + "a" * 4000 + '"')
    assert decoder.decode('{"a": 1}') == {"a": 1}


# ===========================================================================
# 3. Non-finite floats: NaN / Infinity / -Infinity words (parse_constant) and
#    numeric literals overflowing an IEEE double to inf (parse_float). All must
#    be refused; every finite value, including the largest double, must parse.
# ===========================================================================

NON_FINITE = [
    "NaN",
    "Infinity",
    "-Infinity",
    '{"w": NaN}',
    "[1, 2, Infinity]",
    '{"nested": {"w": -Infinity}}',
    "1e400",
    "-1e400",
    "1e999999",
    '{"w": 1e400}',
    "[1e309]",
]


@pytest.mark.parametrize("payload", NON_FINITE)
def test_non_finite_refused_by_loader(payload):
    with pytest.raises(ValueError, match="non-finite"):
        safe_json_loads(payload)


@pytest.mark.parametrize("payload", ["NaN", "Infinity", '{"x": -Infinity}', "1e400"])
def test_non_finite_refused_by_tagged_decoder(payload):
    with pytest.raises(ValueError, match="non-finite"):
        JSONTaggedDecoder().decode(payload)


def test_finite_edge_floats_still_parse():
    assert safe_json_loads("1.7976931348623157e308") == 1.7976931348623157e308
    assert safe_json_loads("5e-324") == 5e-324  # smallest subnormal double
    assert safe_json_loads("1e-999999") == 0.0  # underflow to finite zero
    assert safe_json_loads('{"w": [0.5, -1.25, 1e10]}') == {"w": [0.5, -1.25, 1e10]}


# ===========================================================================
# 4. A "!tag" whose class is NOT on the allowlist must be refused: the tag path
#    reconstructs only pre-registered classes, so an attacker cannot name an
#    arbitrary module or class (CWE-502).
# ===========================================================================

UNKNOWN_TAGS = [
    '{"!nltk.not.a.real.tag": 1}',
    '{"!nltk.evil.RCE": {"cmd": "x"}}',
    '{"!os.system": ["id"]}',
    '{"!subprocess.Popen": [["sh", "-c", "id"]]}',
    '{"!builtins.eval": "1+1"}',
]


@pytest.mark.parametrize("payload", UNKNOWN_TAGS)
def test_unknown_tag_refused(payload):
    with pytest.raises(ValueError, match="Unknown tag"):
        JSONTaggedDecoder().decode(payload)


# ===========================================================================
# 5. Spoofed / forged tag prefix. The fully-qualified "tag:nltk.org,2011:" form
#    is only honoured when it carries the "!" marker AND is registered; a forged
#    "!"-prefixed variant is an unknown tag, while a key that merely LOOKS
#    class-like but lacks the "!" marker is returned as inert data, never
#    resolved to a class.
# ===========================================================================


def test_forged_qualified_prefix_with_bang_is_unknown_tag():
    # "!tag:nltk.org,2011:..." carries the "!" marker but is not registered.
    with pytest.raises(ValueError, match="Unknown tag"):
        JSONTaggedDecoder().decode('{"!tag:nltk.org,2011:evil.RCE": {"cmd": "x"}}')


@pytest.mark.parametrize(
    "payload",
    [
        '{"tag:nltk.org,2011:evil": 1}',  # qualified form WITHOUT the "!" marker
        '{"nltk.tag.DefaultTagger": "NN"}',  # a real class name, but no "!" marker
        '{"os.system": ["id"]}',
    ],
)
def test_tag_like_key_without_bang_marker_is_inert(payload):
    # No "!" marker => not treated as a tag => returned as a plain dict of inert
    # data. No class is named, resolved or constructed.
    result = JSONTaggedDecoder().decode(payload)
    assert isinstance(result, dict)


def test_multi_key_object_with_a_tag_key_is_inert():
    # A tag object is single-key; a two-key object is never a tag, so a "!"-keyed
    # entry buried alongside another key is inert data, not a reconstruction.
    result = JSONTaggedDecoder().decode(
        '{"!nltk.tag.sequential.DefaultTagger": "NN", "x": 1}'
    )
    assert result == {"!nltk.tag.sequential.DefaultTagger": "NN", "x": 1}


def test_nested_tag_bomb_is_depth_bounded():
    # A tower of single-key "!"-tag objects is bounded by the decoder's depth
    # cap, never unbounded reconstruction (jackson / fastjson polymorphic class).
    payload = '{"!x":' * OVER_DECODER_DEPTH + "1" + "}" * OVER_DECODER_DEPTH
    with pytest.raises(ValueError):
        JSONTaggedDecoder().decode(payload)


# ===========================================================================
# 6. Duplicate keys: standard json last-value-wins semantics, preserved on both
#    the loader and the tagged decoder (no ambiguity or misbehaviour).
# ===========================================================================


def test_duplicate_keys_last_value_wins_loader():
    assert safe_json_loads('{"a": 1, "a": 2, "a": 3}') == {"a": 3}
    assert safe_json_loads('{"a": 1, "b": 2, "a": 9}') == {"a": 9, "b": 2}


def test_duplicate_keys_last_value_wins_tagged_decoder():
    assert JSONTaggedDecoder().decode('{"a": 1, "a": 2}') == {"a": 2}
    # A duplicated "!"-tag key collapses to one entry, then is gated as a tag:
    # unregistered => refused (never a silent second-value reconstruction).
    with pytest.raises(ValueError, match="Unknown tag"):
        JSONTaggedDecoder().decode('{"!nltk.nope": 1, "!nltk.nope": 2}')


# ===========================================================================
# 7. Unicode escapes and forms: they parse to inert str data or are refused as
#    invalid JSON, but never crash the decoder.
# ===========================================================================


def test_unicode_escapes_parse_as_inert_data():
    assert safe_json_loads(r'"café"') == "café"
    assert safe_json_loads('"a\\u0000b"') == "a\x00b"  # escaped NUL is data
    assert safe_json_loads('"x\\u202ey"') == "x‮y"  # RTL override, inert
    assert isinstance(safe_json_loads(r'"\ud800"'), str)  # lone surrogate, inert
    # A surrogate pair escape composes to one astral code point.
    assert safe_json_loads(r'"😀"') == "\U0001f600"
    # Raw non-ASCII round-trips through the byte-measured path.
    assert safe_json_loads('{"k": "猫"}') == {"k": "猫"}


@pytest.mark.parametrize("payload", [r'"\x41"', r'"\U0001F600"', '﻿{"a":1}'])
def test_invalid_unicode_forms_refused_not_crashed(payload):
    with pytest.raises(ValueError):
        safe_json_loads(payload)


# ===========================================================================
# 8. Integer / float edge values: valid finite numbers parse; a giant integer
#    is bounded by the interpreter's int/str conversion limit (a ValueError, not
#    a quadratic hang); non-RFC number syntax is refused.
# ===========================================================================


def test_integer_and_float_edges_parse():
    assert safe_json_loads("9223372036854775808") == 9223372036854775808  # > int64
    assert safe_json_loads("-9223372036854775809") == -9223372036854775809
    assert safe_json_loads("0") == 0
    assert safe_json_loads("-0") == 0  # negative zero integer normalises
    assert safe_json_loads("-0.0") == 0.0
    assert (
        safe_json_loads("123456789012345678901234567890")
        == 123456789012345678901234567890
    )
    assert safe_json_loads("[1, 2.5, -3, 4e2, 5E-1]") == [1, 2.5, -3, 400.0, 0.5]


def test_giant_integer_raises_not_hangs():
    with pytest.raises(ValueError):
        safe_json_loads("1" + "0" * 10_000_000)


@pytest.mark.parametrize(
    "payload",
    ["01", "+1", ".5", "1.", "0x1F", "0o17", "1_000", "1e", "- 1", "Infinity1"],
)
def test_non_rfc_number_syntax_refused(payload):
    with pytest.raises(ValueError):
        safe_json_loads(payload)


# ===========================================================================
# 9. BENIGN: a legit allowlisted tag round-trips to the real object. Both a
#    genuinely registered NLTK class (DefaultTagger) and a locally registered
#    class are exercised, confirming the gate is a functional round-trip, not a
#    blanket refusal.
# ===========================================================================


def test_registered_nltk_tag_round_trips():
    import nltk.tag  # noqa: F401  (import registers the tagger tags)
    from nltk.tag import DefaultTagger

    encoded = json.dumps(DefaultTagger("NN"), cls=JSONTaggedEncoder)
    assert encoded == '{"!nltk.tag.sequential.DefaultTagger": "NN"}'
    restored = JSONTaggedDecoder().decode(encoded)
    assert isinstance(restored, DefaultTagger)
    assert restored._tag == "NN"


def test_locally_registered_tag_round_trips():
    @register_tag
    class _Widget:
        json_tag = "test_candidates._Widget"

        def __init__(self, n):
            self.n = n

        def encode_json_obj(self):
            return {"n": self.n}

        @classmethod
        def decode_json_obj(cls, obj):
            return cls(obj["n"])

    assert TAG_PREFIX + "test_candidates._Widget" in json.loads(
        json.dumps(_Widget(3), cls=JSONTaggedEncoder)
    )
    restored = JSONTaggedDecoder().decode(json.dumps(_Widget(3), cls=JSONTaggedEncoder))
    assert isinstance(restored, _Widget) and restored.n == 3


def test_benign_plain_documents_parse():
    assert safe_json_loads('{"a": [1, 2, 3], "b": {"c": 4}}') == {
        "a": [1, 2, 3],
        "b": {"c": 4},
    }
    assert safe_json_loads("[]") == []
    assert safe_json_loads("{}") == {}
    assert safe_json_loads("true") is True
    assert safe_json_loads("null") is None
    # A benign untagged object passes cleanly through the tagged decoder too.
    assert JSONTaggedDecoder().decode('{"weights": {"NN": 1.5}}') == {
        "weights": {"NN": 1.5}
    }


# ===========================================================================
# 10. Input-type gate (CWE-20): a non str/bytes input fails at the chokepoint
#     with a clear TypeError; bytes and bytearray are accepted and parse.
# ===========================================================================


@pytest.mark.parametrize("bad", [None, 123, 4.5, [1, 2], {"a": 1}, memoryview(b"{}")])
def test_non_str_bytes_input_is_a_clean_type_error(bad):
    with pytest.raises(TypeError, match="expected str or bytes"):
        safe_json_loads(bad)


def test_bytes_and_bytearray_inputs_parse():
    assert safe_json_loads(b'{"a": 1}') == {"a": 1}
    assert safe_json_loads(bytearray(b'{"a": 1}')) == {"a": 1}
    # Byte cap counts UTF-8 bytes, not code points: 40 euro signs = 120 bytes.
    payload = '"' + "€" * 40 + '"'
    assert len(payload) < 60 < len(payload.encode("utf-8"))
    with pytest.raises(ValueError, match="over the"):
        safe_json_loads(payload, max_bytes=60)
