# Natural Language Toolkit: JSON Encoder/Decoder Helpers
#
# Copyright (C) 2001-2026 NLTK Project
# Author: Steven Xu <xxu@student.unimelb.edu.au>
#
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Register JSON tags, so the nltk data loader knows what module and class to look for.

NLTK uses simple '!' tags to mark the types of objects, but the fully-qualified
"tag:nltk.org,2011:" prefix is also accepted in case anyone ends up
using it.
"""

import json

json_tags = {}

TAG_PREFIX = "!"

JSON_MAX_DEPTH = 2000
"""Hard cap on the structural nesting depth handed to the C JSON decoder.

CPython's C accelerator recurses in C, so when a process has raised its
recursion limit a deeply nested document overflows the C stack and segfaults
the interpreter (an uncatchable crash) instead of raising a bounded
``RecursionError``. Over-deep input is therefore rejected before parsing. 2000
sits far above any real NLTK artifact (model weights nest 2 deep, tagsets 2,
tweets a handful) and far below the C-stack limit at which the accelerator
crashes.
"""

JSON_MAX_BYTES = 200 * 1024 * 1024
"""Upper bound (in bytes) on a JSON document loaded from an NLTK resource.

200 MiB clears the largest shipped model (the Russian perceptron weights are
about 30 MB) with headroom while refusing an unbounded-memory payload. It is
deliberately generous: the depth guard, not this size guard, is what
neutralises the crash primitive; this one only bounds memory and, together with
the interpreter's ``int_max_str_digits`` default, the giant-integer conversion
cost.
"""

# Keep only the six bytes that can change structural nesting depth or open and
# close a string literal; ``_scan_json_depth`` deletes everything else at C
# speed before its Python-level scan (see that function's docstring).
_STRUCTURAL_BYTES = b'"\\[]{}'
_IDENTITY_TABLE = bytes(range(256))
_NON_STRUCTURAL = bytes(i for i in range(256) if i not in _STRUCTURAL_BYTES)


_POS_INF = float("inf")


def _reject_non_finite(token):
    """``parse_constant`` hook: refuse ``NaN`` / ``Infinity`` / ``-Infinity``.

    These three are a CPython ``json`` extension, not RFC 8259, so a standards
    conformant document never contains them and no shipped NLTK resource does.
    An attacker-supplied model weight or tweet field could, though, and a NaN
    weight silently poisons every downstream score while an Infinity can turn a
    comparison into a hang, so untrusted input is held to strict JSON.
    """
    raise ValueError(f"non-finite JSON constant {token!r} is not allowed")


def _finite_float(token):
    """``parse_float`` hook: refuse a numeric literal that overflows to infinity.

    ``parse_constant`` only catches the ``Infinity`` word; a plain numeric token
    with a huge exponent (``1e400``) is valid JSON syntax but overflows an IEEE
    double to ``inf`` without going through it. Rejecting the overflow too keeps
    the non-finite guarantee complete. The check runs only on tokens the parser
    already treats as floats, so integers and small floats are unaffected.
    """
    value = float(token)
    if value == _POS_INF or value == -_POS_INF:
        raise ValueError(f"non-finite JSON number {token!r} overflows to infinity")
    return value


def _scan_json_depth(data, limit):
    """Return the maximum structural nesting depth of *data*, stopping early.

    Brackets inside string literals do not count, and backslash escapes are
    honoured, so the result matches what the parser would actually nest. The
    scan returns as soon as the depth exceeds ``limit`` (so a hostile payload
    is rejected after only a few thousand bytes), and it never recurses, so it
    cannot itself be the crash it is guarding against.

    Every byte that cannot change nesting depth or open/close a string literal
    is deleted at C speed by :meth:`bytes.translate` before the Python-level
    loop runs, so a legit multi-megabyte model is scanned in well under a
    second while brackets buried in string values are still counted correctly.
    """
    if isinstance(data, str):
        data = data.encode("utf-8", "surrogatepass")
    residue = bytes(data).translate(_IDENTITY_TABLE, _NON_STRUCTURAL)
    depth = 0
    max_depth = 0
    in_string = False
    escaped = False
    for byte in residue:
        if in_string:
            if escaped:
                escaped = False
            elif byte == 0x5C:  # backslash
                escaped = True
            elif byte == 0x22:  # closing quote
                in_string = False
            continue
        if byte == 0x22:  # opening quote
            in_string = True
        elif byte == 0x5B or byte == 0x7B:  # '[' or '{'
            depth += 1
            if depth > max_depth:
                max_depth = depth
                if max_depth > limit:
                    return max_depth
        elif byte == 0x5D or byte == 0x7D:  # ']' or '}'
            depth -= 1
    return max_depth


def safe_json_loads(
    data,
    *,
    max_depth=JSON_MAX_DEPTH,
    max_bytes=JSON_MAX_BYTES,
    context="NLTK JSON",
):
    """Parse ``data`` (``str`` or ``bytes``) with a size and nesting-depth bound.

    This is a drop-in replacement for :func:`json.loads` for untrusted or
    only-partly-trusted resources (model files, data resources, tweet lines).
    It refuses an over-large or over-deep document *before* handing it to the
    recursive C decoder, so a malicious payload raises a bounded ``ValueError``
    instead of exhausting memory or overflowing the C stack. Giant integers are
    still bounded by the interpreter's ``sys.get_int_max_str_digits()`` default
    during :func:`json.loads`.
    """
    if not isinstance(data, (str, bytes, bytearray)):
        # Fail with a clear type error at the chokepoint rather than deep inside
        # the size/scan path (where a list of small ints, say, would otherwise
        # slip through ``len`` and ``bytes()`` before ``json.loads`` rejects it).
        raise TypeError(f"{context}: expected str or bytes, got {type(data).__name__}")
    # Measure size and scan depth on the UTF-8 byte view so the cap is a true
    # byte cap: a non-ASCII str has more UTF-8 bytes than code points, and
    # counting code points would let an oversized payload slip past the limit.
    raw = data.encode("utf-8", "surrogatepass") if isinstance(data, str) else data
    size = len(raw)
    if size > max_bytes:
        raise ValueError(
            f"{context}: JSON document is {size} bytes, over the "
            f"{max_bytes}-byte limit"
        )
    depth = _scan_json_depth(raw, max_depth)
    if depth > max_depth:
        raise ValueError(
            f"{context}: JSON nesting depth exceeds the maximum allowed "
            f"({max_depth})"
        )
    # Reject every non-finite value: the NaN/Infinity/-Infinity words via
    # parse_constant, and a numeric literal that overflows to inf via
    # parse_float, so no non-finite value reaches a model weight or a tweet.
    return json.loads(
        data, parse_constant=_reject_non_finite, parse_float=_finite_float
    )


def safe_json_load(
    fp,
    *,
    max_depth=JSON_MAX_DEPTH,
    max_bytes=JSON_MAX_BYTES,
    context="NLTK JSON",
):
    """Read a JSON document from a file-like object under the same bounds.

    Reads at most ``max_bytes`` (plus one probe byte) so a gigantic file cannot
    be slurped into memory before it is rejected, then defers to
    :func:`safe_json_loads`. When the stream exposes a binary ``buffer`` the read
    is taken from it so the cap bounds bytes rather than characters (a text
    stream's ``read(n)`` counts code points, and one non-ASCII code point is
    several UTF-8 bytes); a text stream without a buffer falls back to a
    character read and :func:`safe_json_loads` still enforces the cap on the
    encoded byte length. Works with both text and binary streams.
    """
    # Prefer the binary buffer so the byte cap bounds the read itself.
    reader = getattr(fp, "buffer", fp)
    data = reader.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError(f"{context}: JSON resource exceeds the {max_bytes}-byte limit")
    return safe_json_loads(
        data, max_depth=max_depth, max_bytes=max_bytes, context=context
    )


def register_tag(cls):
    """
    Decorates a class to register it's json tag.
    """
    json_tags[TAG_PREFIX + getattr(cls, "json_tag")] = cls
    return cls


class JSONTaggedEncoder(json.JSONEncoder):
    def default(self, obj):
        obj_tag = getattr(obj, "json_tag", None)
        if obj_tag is None:
            return super().default(obj)
        obj_tag = TAG_PREFIX + obj_tag
        obj = obj.encode_json_obj()
        return {obj_tag: obj}


class JSONTaggedDecoder(json.JSONDecoder):
    #: Maximum nesting depth for decoded JSON objects.
    #: Prevents denial of service from deeply nested payloads.
    MAX_DECODE_DEPTH = 200

    #: Upper bound (bytes) on a document handed to the tagged decoder, matching
    #: ``safe_json_loads`` so this path is size-bounded as well as depth-bounded.
    MAX_DECODE_BYTES = JSON_MAX_BYTES

    def __init__(self, **kwargs):
        # Reject non-finite values by default (NaN/Infinity words and numeric
        # overflow to inf), matching safe_json_loads; a caller may still override
        # parse_constant / parse_float explicitly.
        kwargs.setdefault("parse_constant", _reject_non_finite)
        kwargs.setdefault("parse_float", _finite_float)
        super().__init__(**kwargs)

    def decode(self, s):
        # Bound size, then nesting, BEFORE ``super().decode`` runs the recursive
        # C accelerator, which can overflow the C stack (an uncatchable segfault,
        # not a ``RecursionError``) before ``decode_obj``'s Python check runs.
        # Measure on the UTF-8 byte view so the cap counts bytes, not code points.
        raw = s.encode("utf-8", "surrogatepass") if isinstance(s, str) else s
        size = len(raw)
        if size > self.MAX_DECODE_BYTES:
            raise ValueError(
                f"JSON document is {size} bytes, over the "
                f"{self.MAX_DECODE_BYTES}-byte limit"
            )
        if _scan_json_depth(raw, self.MAX_DECODE_DEPTH) > self.MAX_DECODE_DEPTH:
            raise ValueError(
                f"JSON nesting depth exceeds maximum allowed ({self.MAX_DECODE_DEPTH})"
            )
        try:
            return self.decode_obj(super().decode(s))
        except RecursionError:
            raise ValueError("JSON nesting too deep to decode safely")

    @classmethod
    def decode_obj(cls, obj, _depth=0):
        if _depth > cls.MAX_DECODE_DEPTH:
            raise ValueError(
                f"JSON nesting depth exceeds maximum allowed ({cls.MAX_DECODE_DEPTH})"
            )
        # Decode nested objects first.
        if isinstance(obj, dict):
            obj = {key: cls.decode_obj(val, _depth + 1) for (key, val) in obj.items()}
        elif isinstance(obj, list):
            obj = list(cls.decode_obj(val, _depth + 1) for val in obj)
        # Check if we have a tagged object.
        if not isinstance(obj, dict) or len(obj) != 1:
            return obj
        obj_tag = next(iter(obj.keys()))
        if not obj_tag.startswith("!"):
            return obj
        if obj_tag not in json_tags:
            raise ValueError("Unknown tag", obj_tag)
        obj_cls = json_tags[obj_tag]
        return obj_cls.decode_json_obj(obj[obj_tag])


__all__ = [
    "register_tag",
    "json_tags",
    "JSONTaggedEncoder",
    "JSONTaggedDecoder",
    "safe_json_load",
    "safe_json_loads",
    "JSON_MAX_DEPTH",
    "JSON_MAX_BYTES",
]
