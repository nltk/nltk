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

#: Hard cap on the *structural* nesting depth we will hand to the C JSON
#: decoder. CPython's C accelerator recurses in C, so when a process has
#: raised its recursion limit a deeply nested document overflows the C stack
#: and segfaults the interpreter (an uncatchable crash) instead of raising a
#: bounded ``RecursionError``. We therefore reject over-deep input *before*
#: parsing. 2000 sits far above any real NLTK artifact (model weights nest 2
#: deep, tagsets 2, tweets a handful) and far below the C-stack limit at which
#: the accelerator crashes.
JSON_MAX_DEPTH = 2000

#: Upper bound (in bytes) on a JSON document loaded from an NLTK resource.
#: 200 MiB clears the largest shipped model (the Russian perceptron weights are
#: about 30 MB) with headroom while refusing an unbounded-memory payload. It is
#: deliberately generous: the depth guard above, not this size guard, is what
#: neutralises the crash primitive; this one only bounds memory and, together
#: with the interpreter's ``int_max_str_digits`` default, the giant-integer
#: conversion cost.
JSON_MAX_BYTES = 200 * 1024 * 1024

# Keep only the six bytes that can change structural nesting depth or open and
# close a string literal; everything else is deleted at C speed before the
# Python-level scan, so a legit multi-megabyte model is scanned in well under a
# second while brackets buried in string values are still counted correctly.
_STRUCTURAL_BYTES = b'"\\[]{}'
_IDENTITY_TABLE = bytes(range(256))
_NON_STRUCTURAL = bytes(i for i in range(256) if i not in _STRUCTURAL_BYTES)


def _scan_json_depth(data, limit):
    """Return the maximum structural nesting depth of *data*, stopping early.

    Brackets inside string literals do not count, and backslash escapes are
    honoured, so the result matches what the parser would actually nest. The
    scan returns as soon as the depth exceeds ``limit`` (so a hostile payload
    is rejected after only a few thousand bytes), and it never recurses, so it
    cannot itself be the crash it is guarding against.
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
    size = len(data)
    if size > max_bytes:
        raise ValueError(
            f"{context}: JSON document is {size} bytes, over the "
            f"{max_bytes}-byte limit"
        )
    depth = _scan_json_depth(data, max_depth)
    if depth > max_depth:
        raise ValueError(
            f"{context}: JSON nesting depth exceeds the maximum allowed "
            f"({max_depth})"
        )
    return json.loads(data)


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
    :func:`safe_json_loads`. Works with both text and binary streams.
    """
    data = fp.read(max_bytes + 1)
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

    def decode(self, s):
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
