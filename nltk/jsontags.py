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

import itertools
import json
import math
import operator

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

The C accelerator parses a document up to this depth cheaply, so a value within
the cap loads on every supported interpreter; ``safe_json_loads`` keeps it on the
C scanner (see there) rather than the pure-Python scanner, which recurses in
Python and would ``RecursionError`` a few hundred levels deep under the default
recursion limit.
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

# Keep only the five bytes that can change structural nesting depth or open and
# close a string literal; ``_scan_json_depth`` resolves escapes, then deletes
# everything else at C speed before its Python-level scan (see its docstring).
_STRUCTURAL_BYTES = b'"[]{}'
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


def _reject_non_finite_walk(obj, context="NLTK JSON"):
    """Refuse any non-finite float anywhere in an already-parsed JSON value.

    ``safe_json_loads`` parses on the C scanner (no ``parse_constant`` /
    ``parse_float`` hooks, which would force the recursive pure-Python scanner),
    so the NaN/Infinity/-Infinity words and any numeric literal that overflowed an
    IEEE double to ``inf`` are caught here instead. The walk is ITERATIVE (an
    explicit stack, never recursion), so a document nested up to JSON_MAX_DEPTH
    cannot make this check itself overflow the stack (CWE-674). Returns ``obj`` so
    it can wrap the parse in one expression.

    A container is not descended into when ``math.fsum`` adds up its members,
    or the values of its members when they are all dicts, to a finite number:
    ``fsum`` refuses a member that is no number (a string, a container, None)
    and returns inf or NaN, or raises, whenever a member is non-finite, so a
    finite sum proves that every number the walk would visit there is finite.
    Model weights are a dict of dicts of floats, so the walk then sums them in
    C instead of visiting each weight; any other container is walked as before.
    """
    stack = [obj]
    while stack:
        cur = stack.pop()
        if isinstance(cur, float):
            if not math.isfinite(cur):
                raise ValueError(
                    f"{context}: non-finite JSON number (NaN/Infinity) is not allowed"
                )
            continue
        if isinstance(cur, dict):
            members = cur.values()
        elif isinstance(cur, list):
            members = cur
        else:
            continue
        if _finite_numbers(members) or _finite_numbers(
            itertools.chain.from_iterable(map(dict.values, members))
        ):
            continue
        stack.extend(members)
    return obj


def _finite_numbers(values):
    """True only if every item of *values* is a number and ``math.fsum`` of
    them is finite, which no item that is a non-finite float allows."""
    try:
        return math.isfinite(math.fsum(values))
    except (TypeError, ValueError, OverflowError):
        return False


def _parsed_text_utf8(data):
    """The text ``json.loads`` will parse, as UTF-8 bytes.

    A ``str`` is parsed as it is. ``bytes`` are decoded first with the
    encoding ``json.detect_encoding`` picks, which is UTF-16 or UTF-32 when the
    null-byte pattern says so: a scan of those raw bytes would see a quote or a
    bracket in the high byte of an unrelated code unit (U+4E22 is ``22 4E`` in
    UTF-16-LE) and miss the real ones, so they are decoded as the parser will
    decode them. UTF-8 needs no round trip: its multi-byte sequences hold no
    ASCII byte, so the structural bytes are already where the parser sees them.
    """
    if isinstance(data, str):
        return data.encode("utf-8", "surrogatepass")
    data = bytes(data)
    encoding = json.detect_encoding(data)
    if encoding in ("utf-8", "utf-8-sig"):
        return data
    return data.decode(encoding, "surrogatepass").encode("utf-8", "surrogatepass")


def _scan_json_depth(data, limit):
    """Return the maximum structural nesting depth of *data*, stopping early.

    Brackets inside string literals do not count, and backslash escapes are
    honoured, so the result matches what the parser would actually nest. The
    scan returns as soon as the depth exceeds ``limit`` (so a hostile payload
    is rejected after only a few thousand bytes), and it never recurses, so it
    cannot itself be the crash it is guarding against.

    *data* is what the caller hands ``json.loads`` (``str`` or ``bytes``), so
    the scan sees the text the parser will (see :func:`_parsed_text_utf8`).
    Escapes are resolved before anything is deleted: a backslash escapes the
    one character after it, so each ``\\\\`` pair (an escaped backslash) and
    then each ``\\"`` pair (an escaped quote) is removed. Scanning only after
    the deletion let the backslash of ``\\n`` swallow the next structural byte,
    the string's closing quote, so every bracket up to the next quote was
    taken for string content and a document of any depth passed.

    Every byte that cannot change nesting depth or open/close a string literal
    (the backslashes left once the escapes are resolved among them) is deleted
    at C speed by :meth:`bytes.translate` before the Python-level loop runs,
    so a legit multi-megabyte model is scanned in well under a second while
    brackets buried in string values are still counted correctly.
    """
    return _utf8_depth(_parsed_text_utf8(data), limit)


def _utf8_depth(text, limit):
    """:func:`_scan_json_depth` of the parsed text already as UTF-8 bytes."""
    text = text.replace(b"\\\\", b"").replace(b'\\"', b"")
    # With no backslash left, quotes alternate open and close, so an adjacent
    # pair is an empty string or a close then an open with nothing between:
    # dropping it leaves every bracket inside or outside a string as it was.
    residue = text.translate(_IDENTITY_TABLE, _NON_STRUCTURAL).replace(b'""', b"")
    quotes = residue.count(b'"')
    if quotes <= _SPLIT_QUOTES:
        # Quotes alternate, so every other piece between them is outside any
        # string; those pieces in order are the brackets the loop counts.
        return _bracket_depth(b"".join(residue.split(b'"')[0::2]), limit)
    depth = 0
    max_depth = 0
    in_string = False
    for byte in residue:
        if byte == 0x22:  # a quote opens or closes a string literal
            in_string = not in_string
        elif in_string:
            continue
        elif byte == 0x5B or byte == 0x7B:  # '[' or '{'
            depth += 1
            if depth > max_depth:
                max_depth = depth
                if max_depth > limit:
                    return max_depth
        elif byte == 0x5D or byte == 0x7D:  # ']' or '}'
            depth -= 1
    return max_depth


#: Brackets :func:`_bracket_depth` counts per step; a document past the cap is
#: refused within one step of crossing it, as the loop refuses it there.
_DEPTH_STEP = 1 << 16
_STEP_OF = bytes.maketrans(b"[{]}", b"\x02\x02\x00\x00")
#: Most quotes left in a residue that :func:`_utf8_depth` splits on (one small
#: bytes object per piece); a residue with more takes the loop.
_SPLIT_QUOTES = 1 << 16


def _bracket_depth(residue, limit):
    """What the loop in :func:`_utf8_depth` returns for brackets that are all
    outside strings, counted at C speed: an opener is +1, a closer -1, and the
    deepest running total is the depth. Like the loop it returns the first
    depth past ``limit``."""
    depth = best = 0
    for start in range(0, len(residue), _DEPTH_STEP):
        steps = residue[start : start + _DEPTH_STEP].translate(_STEP_OF)
        totals = itertools.accumulate(
            map(operator.sub, steps, itertools.repeat(1)), initial=depth
        )
        best = max(best, max(totals))
        if best > limit and best > 0:
            return max(limit + 1, 1)
        depth += len(steps) - 2 * steps.count(0)
    return best


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
            f"{context}: JSON document is {size} bytes, over the {max_bytes}-byte limit"
        )
    depth = _utf8_depth(
        raw if isinstance(data, str) else _parsed_text_utf8(raw), max_depth
    )
    if depth > max_depth:
        raise ValueError(
            f"{context}: JSON nesting depth exceeds the maximum allowed ({max_depth})"
        )
    # Parse with the DEFAULT (C accelerator) scanner: it handles nesting up to
    # JSON_MAX_DEPTH cheaply on every interpreter. Supplying parse_constant /
    # parse_float, as this function used to, forces json.loads onto the
    # pure-Python scanner on CPython <= 3.11 (the C scanner gained hook support
    # in 3.12), and that scanner recurses in Python and raises RecursionError
    # only a few hundred levels deep under the default recursion limit -- so a
    # document within the cap crashed instead of loading. Non-finite values are
    # instead rejected AFTER the parse by an ITERATIVE walk (``_reject_non_finite``)
    # that cannot itself recurse. A RecursionError from a caller already near the
    # limit is still converted to a clean ValueError so uncontrolled recursion can
    # never escape (CWE-674), mirroring JSONTaggedDecoder.decode.
    try:
        parsed = json.loads(data)
    except RecursionError:
        raise ValueError(f"{context}: JSON nesting too deep to parse safely") from None
    return _reject_non_finite_walk(parsed, context)


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


YAML_MAX_DEPTH = 100
"""Hard cap on YAML structural nesting depth.

PyYAML's safe loader composes the node graph with ordinary Python recursion
(``Composer.compose_node`` calls itself once per nested collection), so a
document a few hundred levels deep overflows the default recursion limit and
raises an uncaught ``RecursionError`` mid-load (CWE-674). Over-deep input is
rejected during composition before that happens. 100 sits far above any real
NLTK YAML (markdown front matter nests 1 to 3, a config a handful) and well
below the recursion limit at which PyYAML crashes.
"""

YAML_MAX_NODES = 10000
"""Hard cap on the number of nodes PyYAML's safe loader may compose.

The pure-Python loader runs the implicit-type resolver on every node, which is
expensive: composing ten thousand nodes already costs a few CPU seconds, and a
flat document of a few hundred thousand nodes runs for minutes (CWE-400). The
count is checked as each node is composed, so a hostile document is refused
after a bounded amount of work rather than running unbounded. 10000 clears any
real NLTK YAML (front matter and configs hold tens of nodes) with wide headroom.
"""

YAML_MAX_BYTES = 1 * 1024 * 1024
"""Upper bound (in bytes) on a YAML document loaded from an NLTK resource.

Refused before any parsing, so an oversized file is rejected instantly instead
of being read into memory. 1 MiB is generous for NLTK YAML (no shipped resource
is YAML; markdown front matter is a few KB at most) while bounding memory; the
depth and node caps, not this one, bound the parser's CPU cost.
"""

_BOUNDED_YAML_LOADER = None


def _bounded_yaml_loader():
    """Build (once) a PyYAML ``SafeLoader`` subclass that enforces the caps.

    Defined lazily because PyYAML is an optional dependency: importing yaml at
    module load time would make every NLTK import fail where it is absent. The
    subclass counts composition depth and total node count inside the single
    recursive chokepoint (``compose_node``) and raises a bounded ``ValueError``
    the moment either cap is crossed, so the crash and the runaway parse are
    both stopped before they happen.
    """
    global _BOUNDED_YAML_LOADER
    if _BOUNDED_YAML_LOADER is not None:
        return _BOUNDED_YAML_LOADER
    import yaml

    class _BoundedSafeLoader(yaml.SafeLoader):
        def __init__(
            self,
            stream,
            *,
            context="NLTK YAML",
            max_depth=YAML_MAX_DEPTH,
            max_nodes=YAML_MAX_NODES,
        ):
            super().__init__(stream)
            self._ctx = context
            self._max_depth = max_depth
            self._max_nodes = max_nodes
            self._depth = 0
            self._nodes = 0

        def compose_node(self, parent, index):
            self._nodes += 1
            if self._nodes > self._max_nodes:
                raise ValueError(
                    f"{self._ctx}: YAML document composes more than "
                    f"{self._max_nodes} nodes"
                )
            self._depth += 1
            if self._depth > self._max_depth:
                raise ValueError(
                    f"{self._ctx}: YAML nesting depth exceeds the maximum "
                    f"allowed ({self._max_depth})"
                )
            try:
                return super().compose_node(parent, index)
            finally:
                self._depth -= 1

    _BOUNDED_YAML_LOADER = _BoundedSafeLoader
    return _BOUNDED_YAML_LOADER


def safe_yaml_loads(
    data,
    *,
    max_depth=YAML_MAX_DEPTH,
    max_nodes=YAML_MAX_NODES,
    max_bytes=YAML_MAX_BYTES,
    context="NLTK YAML",
):
    """Parse ``data`` (``str`` or ``bytes``) as YAML under size, depth and node bounds.

    Drop-in replacement for ``yaml.safe_load`` for untrusted or only-partly
    trusted resources (markdown front matter, YAML-format data resources). The
    stdlib behaviour is a denial of service: PyYAML's safe loader has no bound
    on nesting depth (a deep document raises an uncaught ``RecursionError``,
    CWE-674) or on node count (a large document runs for minutes, CWE-400). This
    refuses an over-large document before parsing and an over-deep or over-wide
    one during composition, always with a bounded ``ValueError``.
    """
    if not isinstance(data, (str, bytes, bytearray)):
        raise TypeError(f"{context}: expected str or bytes, got {type(data).__name__}")
    raw = data.encode("utf-8", "surrogatepass") if isinstance(data, str) else data
    size = len(raw)
    if size > max_bytes:
        raise ValueError(
            f"{context}: YAML document is {size} bytes, over the {max_bytes}-byte limit"
        )
    loader_cls = _bounded_yaml_loader()
    loader = loader_cls(data, context=context, max_depth=max_depth, max_nodes=max_nodes)
    try:
        return loader.get_single_data()
    except RecursionError:
        raise ValueError(f"{context}: YAML nesting too deep to parse safely") from None
    finally:
        loader.dispose()


def safe_yaml_load(
    fp,
    *,
    max_depth=YAML_MAX_DEPTH,
    max_nodes=YAML_MAX_NODES,
    max_bytes=YAML_MAX_BYTES,
    context="NLTK YAML",
):
    """Read a YAML document from a file-like object under the same bounds.

    Reads at most ``max_bytes`` (plus one probe byte) so a gigantic file cannot
    be slurped into memory before it is rejected, then defers to
    :func:`safe_yaml_loads`. Prefers the stream's binary ``buffer`` so the cap
    bounds bytes rather than characters; works with text and binary streams.
    """
    reader = getattr(fp, "buffer", fp)
    data = reader.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError(f"{context}: YAML resource exceeds the {max_bytes}-byte limit")
    return safe_yaml_loads(
        data,
        max_depth=max_depth,
        max_nodes=max_nodes,
        max_bytes=max_bytes,
        context=context,
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
        text = raw if isinstance(s, str) else _parsed_text_utf8(raw)
        if _utf8_depth(text, self.MAX_DECODE_DEPTH) > self.MAX_DECODE_DEPTH:
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
    "safe_yaml_load",
    "safe_yaml_loads",
    "JSON_MAX_DEPTH",
    "JSON_MAX_BYTES",
    "YAML_MAX_DEPTH",
    "YAML_MAX_NODES",
    "YAML_MAX_BYTES",
]
