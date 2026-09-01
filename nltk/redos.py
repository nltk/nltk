# Natural Language Toolkit: ReDoS backstop for caller-supplied patterns
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org>
# For license information, see LICENSE.TXT

r"""
The single point every regular expression in NLTK routes through, so that a
catastrophically backtracking or oversized pattern cannot become a denial of
service (CWE-1333 / CWE-400).

Every regex in the library is applied to input that can be attacker controlled
-- a corpus file, a caller-supplied pattern, a token stream -- so ``re`` is used
nowhere directly. Instead code calls :func:`compile` for a reusable pattern, or
the ``re``-compatible module helpers (:func:`match`, :func:`search`, :func:`sub`,
:func:`split`, :func:`findall`, :func:`finditer`, :func:`fullmatch`,
:func:`subn`) for an inline call. The guard ``tools/check_all_regex_through_redos.py``
enforces that policy in CI. Historically only a handful of *caller-supplied*
sinks routed through here (``RegexpTokenizer``, ``RegexpTagger``,
``tgrep_compile``, the ``RegexpChunkRule`` family); making it universal means one
audited defence covers the whole surface.

A crafted pattern (e.g. ``(a+)+$`` or ``(a|a)*$``) can trigger catastrophic
backtracking and pin a CPU core indefinitely. This module centralises a single,
tested defence in two layers:

1. **Compile with the third-party ``regex`` engine** instead of the stdlib
   ``re``. Its optimiser collapses a large class of catastrophic patterns
   -- notably nested quantifiers over the *same* sub-expression such as
   ``(a+)+$`` -- to linear time outright, so those "attacks" finish in
   microseconds and never reach the timeout.

2. **Run every match under a wall-clock ``timeout``**. The optimiser does *not*
   cover every shape -- an alternation of identical branches such as
   ``(a|a)*`` (and the equivalent ``<a|a>*`` chunk tag pattern) still
   backtracks exponentially in *both* ``re`` and ``regex``. The timeout is
   therefore a *mandatory* backstop, not a nicety: when it trips, an
   actionable :class:`TimeoutError` is raised instead of hanging the process.

Rewriting the pattern to be linear (atomic groups / possessive quantifiers)
was evaluated and rejected: it does *not* defuse the identical-branch
alternation, and it silently changes match semantics for legitimate greedy
patterns such as ``<.*>*<NN>``. A bounded timeout is the only defence that is
both complete and behaviour-preserving for arbitrary caller patterns.

Usage::

    from nltk import redos
    rx = redos.compile(pattern, flags)      # -> a TimedPattern
    rx.findall(text)                         # runs under DEFAULT_TIMEOUT
    rx.search(text, timeout=1.0)             # per-call override

``TimedPattern`` quacks like the subset of ``re.Pattern`` these sinks use
(``findall`` / ``finditer`` / ``split`` / ``search`` / ``match`` / ``fullmatch``
/ ``sub`` / ``subn`` plus attribute access such as ``.pattern`` and ``.flags``),
so it is a drop-in replacement for a compiled pattern at those call sites.
"""

import functools
import re as _re

import regex

__all__ = [
    "DEFAULT_TIMEOUT",
    "MAX_PATTERN_LENGTH",
    "MAX_NESTING_DEPTH",
    "MAX_REPEAT_PRODUCT",
    "TimedPattern",
    "error",
    "check_pattern",
    "compile",
    "source_of",
    "reharden",
    # re-compatible module-level helpers (route every inline call through redos)
    "match",
    "fullmatch",
    "search",
    "findall",
    "finditer",
    "split",
    "sub",
    "subn",
]

#: Wall-clock seconds any single caller-supplied-pattern match may run before it
#: is abandoned with :class:`TimeoutError`. Legitimate tokenizing / tagging /
#: chunking of even large inputs finishes in well under a second, so this is
#: roughly a thousand-fold head-room for real use while still capping a crafted
#: pattern's CPU burn. It is deliberately far below a naive "just make it large"
#: value (e.g. 60s): in a denial-of-service the busy-wait window *is* the damage,
#: so a shorter cap is strictly safer. Set a call's ``timeout`` to ``None`` to
#: disable the limit for a trusted pattern.
DEFAULT_TIMEOUT = 5.0

#: Sentinel so ``timeout=None`` (disable) is distinguishable from "use the
#: module default", and so a later ``nltk.redos.DEFAULT_TIMEOUT = ...`` still
#: takes effect for calls that did not pass an explicit timeout.
_UNSET = object()


class error(_re.error):
    """Raised for a pattern redos refuses or the engine rejects.

    A subclass of :class:`re.error` so that call sites which move from ``re`` to
    redos and still ``except re.error:`` keep working -- the ``regex`` engine
    redos wraps raises its own ``regex.error`` that is *not* a ``re.error``, so
    :func:`compile` normalises an engine compile failure to this type.
    """


#: Max length of a regex SOURCE :func:`compile` hands to the engine. Compile time
#: scales with length and no match-time cap can help (compilation runs first), so
#: an oversized source is refused as a compile-time DoS (CWE-1333 / CWE-400).
MAX_PATTERN_LENGTH = 100_000

#: Max group-nesting depth. The engine's parser recurses per group (and per
#: nested character-class set), so a deeply nested source raises RecursionError (a
#: crash, a native stack overflow on some builds); a legitimate pattern is shallow.
MAX_NESTING_DEPTH = 100

#: Max expansion of a counted repetition. The engine expands ``(group){n}`` into
#: n copies at compile time and nested counts multiply, so an unbounded product
#: blows up compile; a legitimate pattern's counts multiply to a small number.
MAX_REPEAT_PRODUCT = 100_000

#: How far :func:`check_pattern` looks for the ``}`` closing a ``{`` when deciding
#: whether it opens a quantifier. A real ``{m,n}`` body is a few digits and a
#: comma; scanning to the end of the source for every ``{`` was itself O(n**2) on
#: a run of unclosed braces (a DoS in the guard). A brace with no ``}`` within
#: this window is treated as a literal ``{`` -- and any count long enough to fall
#: outside it is astronomically larger than MAX_REPEAT_PRODUCT, so nothing real is
#: missed. This also avoids ``int()``-ing a giant digit run (CPython's
#: 4300-digit limit) out of an attacker-supplied body.
_MAX_QUANTIFIER_SPAN = 64

#: Longest pattern the module-level helpers cache. The cache mirrors ``re``'s
#: pattern cache for NLTK's own (small, constant) patterns; bounding the cached
#: length keeps an attacker who funnels many distinct large patterns through the
#: helpers from pinning ~MAX_PATTERN_LENGTH * cache-size bytes of memory.
_MAX_CACHE_PATTERN_LEN = 2_000


class TimedPattern:
    """A compiled :mod:`regex` pattern whose match operations are bounded by a
    wall-clock timeout.

    Every exposed match method runs the underlying engine with ``timeout=`` and
    re-raises a bare :class:`TimeoutError` as an actionable one naming the
    offending pattern. Any other attribute (``pattern``, ``flags``, ``groups``,
    ``groupindex``, ...) is delegated to the wrapped pattern, so instances are a
    drop-in for a compiled pattern at NLTK's regex sinks.
    """

    __slots__ = ("_rx", "_timeout")

    def __init__(self, compiled, timeout=_UNSET):
        self._rx = compiled
        self._timeout = timeout

    # -- internals ---------------------------------------------------------

    def _resolve(self, timeout):
        if timeout is _UNSET:
            timeout = self._timeout
        if timeout is _UNSET:
            timeout = DEFAULT_TIMEOUT
        return timeout

    def _fail(self, timeout):
        return TimeoutError(
            f"regular-expression match exceeded its {timeout}s time limit; the "
            f"pattern {self._rx.pattern!r} may be pathological for this input "
            f"(catastrophic backtracking / ReDoS). Pass timeout=None to disable "
            f"the limit for a trusted pattern."
        )

    # -- match API (timeout-guarded) --------------------------------------

    def search(self, string, *args, timeout=_UNSET, **kwargs):
        t = self._resolve(timeout)
        try:
            return self._rx.search(string, *args, timeout=t, **kwargs)
        except TimeoutError:
            raise self._fail(t) from None

    def match(self, string, *args, timeout=_UNSET, **kwargs):
        t = self._resolve(timeout)
        try:
            return self._rx.match(string, *args, timeout=t, **kwargs)
        except TimeoutError:
            raise self._fail(t) from None

    def fullmatch(self, string, *args, timeout=_UNSET, **kwargs):
        t = self._resolve(timeout)
        try:
            return self._rx.fullmatch(string, *args, timeout=t, **kwargs)
        except TimeoutError:
            raise self._fail(t) from None

    def findall(self, string, *args, timeout=_UNSET, **kwargs):
        t = self._resolve(timeout)
        try:
            return self._rx.findall(string, *args, timeout=t, **kwargs)
        except TimeoutError:
            raise self._fail(t) from None

    def split(self, string, *args, timeout=_UNSET, **kwargs):
        t = self._resolve(timeout)
        try:
            return self._rx.split(string, *args, timeout=t, **kwargs)
        except TimeoutError:
            raise self._fail(t) from None

    def sub(self, repl, string, *args, timeout=_UNSET, **kwargs):
        t = self._resolve(timeout)
        try:
            return self._rx.sub(repl, string, *args, timeout=t, **kwargs)
        except TimeoutError:
            raise self._fail(t) from None

    def subn(self, repl, string, *args, timeout=_UNSET, **kwargs):
        t = self._resolve(timeout)
        try:
            return self._rx.subn(repl, string, *args, timeout=t, **kwargs)
        except TimeoutError:
            raise self._fail(t) from None

    def finditer(self, string, *args, timeout=_UNSET, **kwargs):
        # ``regex.finditer`` is lazy: the timeout is enforced as items are
        # pulled, so the guard must wrap the *iteration*, not just the call.
        t = self._resolve(timeout)
        try:
            yield from self._rx.finditer(string, *args, timeout=t, **kwargs)
        except TimeoutError:
            raise self._fail(t) from None

    # -- transparent delegation for everything else -----------------------

    def __getattr__(self, name):
        # Only reached for attributes not defined above. Do NOT delegate dunder
        # lookups (pickle/copy/etc.) -- delegating those to the wrapped pattern
        # would make the wrapper masquerade as the pattern in confusing ways.
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        return getattr(self._rx, name)

    def __eq__(self, other):
        # Two wrappers are equal when they guard the same source pattern under
        # the same flags and timeout. Without this, instances fall back to
        # identity, so an object that has been round-tripped (e.g. a
        # ``RegexpTagger`` serialised to and from JSON, which re-compiles its
        # patterns) never compares equal to the original.
        if not isinstance(other, TimedPattern):
            return NotImplemented
        return (
            self._rx.pattern == other._rx.pattern
            and self._rx.flags == other._rx.flags
            and self._timeout == other._timeout
        )

    def __hash__(self):
        return hash((self._rx.pattern, self._rx.flags, self._timeout))

    def __repr__(self):
        return f"TimedPattern({self._rx.pattern!r}, timeout={self._timeout!r})"


def compile(pattern, flags=0, timeout=_UNSET):
    r"""Compile ``pattern`` with the :mod:`regex` engine and wrap it so every
    match runs under a wall-clock timeout.

    :param pattern: a regular-expression string, or an already-compiled
        ``re``/``regex`` pattern (its ``.pattern`` is re-compiled with
        ``regex``), or an existing :class:`TimedPattern` (returned as-is with
        the requested timeout).
    :param flags: regex flags (stdlib ``re`` flag constants are accepted).
    :param timeout: default wall-clock limit for matches on the returned
        pattern; ``None`` disables it. Omit to use :data:`DEFAULT_TIMEOUT` at
        match time (so a later change to that module attribute still applies).
    :rtype: TimedPattern
    """
    if isinstance(pattern, TimedPattern):
        if timeout is _UNSET:
            return pattern
        return TimedPattern(pattern._rx, timeout)
    # Accept a pre-compiled ``re``/``regex`` pattern by re-compiling its source.
    src = getattr(pattern, "pattern", pattern)
    check_pattern(src)
    try:
        compiled = regex.compile(src, flags)
    except regex.error as exc:
        # Normalise the engine's error to a re.error subclass so callers that
        # catch re.error still work after moving off the stdlib module.
        raise error(str(exc)) from exc
    return TimedPattern(compiled, timeout)


@functools.lru_cache(maxsize=1024)
def _cached_compile(src, flags):
    """Compile-and-wrap with a cache, mirroring :mod:`re`'s internal pattern
    cache so the module-level helpers below do not re-check and re-compile a
    constant pattern on every call. The returned :class:`TimedPattern` uses the
    default (unset) timeout, so it still honours a later change to
    :data:`DEFAULT_TIMEOUT` at match time."""
    return compile(src, flags)


def _coerce(pattern, flags):
    """Return a :class:`TimedPattern` for the ``re``-style helpers below.

    A string is compiled (and cached); an already-compiled ``TimedPattern`` is
    used as-is; any other pre-compiled pattern is re-hardened via
    :func:`compile`. This makes ``redos.match(p, s)`` a drop-in for
    ``re.match(p, s)`` while forcing every pattern through the DoS guards.
    """
    if isinstance(pattern, TimedPattern):
        return pattern
    if isinstance(pattern, str) and len(pattern) <= _MAX_CACHE_PATTERN_LEN:
        return _cached_compile(pattern, flags)
    return compile(pattern, flags)


# ---------------------------------------------------------------------------
# ``re``-compatible module-level helpers. Every regex in NLTK routes through one
# of these (or :func:`compile`) instead of ``re``/``regex`` directly, so both
# the compile-time refusal (:func:`check_pattern`) and the wall-clock match
# timeout apply everywhere (CWE-1333 / CWE-400). Signatures mirror :mod:`re`.
# ---------------------------------------------------------------------------


def match(pattern, string, flags=0):
    return _coerce(pattern, flags).match(string)


def fullmatch(pattern, string, flags=0):
    return _coerce(pattern, flags).fullmatch(string)


def search(pattern, string, flags=0):
    return _coerce(pattern, flags).search(string)


def findall(pattern, string, flags=0):
    return _coerce(pattern, flags).findall(string)


def finditer(pattern, string, flags=0):
    return _coerce(pattern, flags).finditer(string)


def split(pattern, string, maxsplit=0, flags=0):
    return _coerce(pattern, flags).split(string, maxsplit)


def sub(pattern, repl, string, count=0, flags=0):
    return _coerce(pattern, flags).sub(repl, string, count)


def subn(pattern, repl, string, count=0, flags=0):
    return _coerce(pattern, flags).subn(repl, string, count)


def _repeat_min(spec):
    """The minimum repeat count of a ``{...}`` quantifier body, or ``None`` if it
    is not a valid quantifier (a literal brace). The engine expands the *minimum*
    required copies, so that count (not the upper bound) drives compile blow-up."""
    spec = spec.strip()
    if "," in spec:
        lo = spec.split(",", 1)[0].strip()
        return 0 if lo == "" else (int(lo) if lo.isdigit() else None)
    return int(spec) if spec.isdigit() else None


def check_pattern(src):
    """Refuse a regex source that is a compile-time DoS before it reaches any
    engine: over-long, too deeply nested (parser recursion / stack overflow), or
    with a counted repetition whose expansion is too large. Raises ``ValueError``.

    Call this before compiling a caller-supplied pattern with ``re``/``regex``
    directly (:func:`compile` already calls it). ``src`` is the pattern string
    (``str``/``bytes``); a non-string is ignored so the engine can validate it."""
    if isinstance(src, (bytes, bytearray)):
        scan = bytes(src).decode("latin-1")
    elif isinstance(src, str):
        scan = src
    else:
        return  # not a string source: let the engine validate / raise
    if len(scan) > MAX_PATTERN_LENGTH:
        raise ValueError(
            f"regex source is {len(scan)} chars (> {MAX_PATTERN_LENGTH}); refusing "
            "to compile a pattern that large (CWE-1333 compile-time DoS)"
        )
    depth_msg = (
        f"regex nests groups / classes more than {MAX_NESTING_DEPTH} deep; refusing "
        "to compile (CWE-1333 parser recursion / stack overflow)"
    )
    repeat_msg = (
        f"regex counted repetition expands beyond {MAX_REPEAT_PRODUCT} copies; "
        "refusing to compile (CWE-1333 compile-time blow-up)"
    )
    depth = 0  # combined group ``(`` + character-class ``[`` nesting
    class_depth = 0  # > 0 while inside a character class
    cost = [0]  # per-group accumulated expansion; cost[-1] is the current group
    last = 0  # expansion of the most recent atom / group, for a trailing ``{m,n}``
    i = 0
    n = len(scan)
    while i < n:
        ch = scan[i]
        if ch == "\\":  # an escape: the next char is one literal atom
            i += 2
            if not class_depth:
                cost[-1] += 1
                last = 1
            continue
        if class_depth:
            if ch == "[":
                class_depth += 1
                depth += 1
                if depth > MAX_NESTING_DEPTH:
                    raise ValueError(depth_msg)
            elif ch == "]":
                class_depth -= 1
                depth -= 1
                if class_depth == 0:  # the whole class counts as one atom
                    cost[-1] += 1
                    last = 1
            i += 1
            continue
        if ch == "[":
            class_depth = 1
            depth += 1
            if depth > MAX_NESTING_DEPTH:
                raise ValueError(depth_msg)
        elif ch == "(":
            depth += 1
            if depth > MAX_NESTING_DEPTH:
                raise ValueError(depth_msg)
            cost.append(0)
        elif ch == ")":
            if depth:
                depth -= 1
            if len(cost) > 1:
                c = cost.pop()
                cost[-1] += c
                last = c
        elif ch == "{":
            # Only scan a small window for the closing ``}``: a real quantifier
            # body is short, and scanning to end-of-source per ``{`` was O(n**2)
            # (see ``_MAX_QUANTIFIER_SPAN``).
            j = scan.find("}", i + 1, i + 1 + _MAX_QUANTIFIER_SPAN)
            if j == -1:
                # No ``}`` in the window. If a digit follows, this is a count too
                # long to be anything but a giant repetition -- refuse it (rather
                # than let the engine int() a huge digit run); otherwise it is a
                # literal ``{``.
                if i + 1 < n and scan[i + 1].isdigit():
                    raise ValueError(repeat_msg)
                m = None
            else:
                m = _repeat_min(scan[i + 1 : j])
            if m is None:  # a literal brace, not a quantifier
                cost[-1] += 1
                last = 1
            else:
                mult = max(1, m)
                cost[-1] += last * (mult - 1)
                last *= mult
                if last > MAX_REPEAT_PRODUCT or cost[-1] > MAX_REPEAT_PRODUCT:
                    raise ValueError(repeat_msg)
                i = j + 1
                continue
        elif ch in "*+?":
            pass  # an unbounded loop, not expanded at compile time
        elif ch == "|":
            last = 0
        else:  # an ordinary atom
            cost[-1] += 1
            last = 1
        i += 1
    if cost[0] > MAX_REPEAT_PRODUCT:
        raise ValueError(repeat_msg)


def source_of(pattern):
    """The trusted source string of a ``str`` / compiled ``re`` / ``regex`` /
    :class:`TimedPattern`. Raises :class:`ValueError` for a pattern object that
    exposes no string source, so an unbounded one cannot be rebuilt from it."""
    if isinstance(pattern, str):
        return pattern
    src = getattr(pattern, "pattern", None)
    if isinstance(src, (bytes, bytearray)):
        src = bytes(src).decode("latin-1")
    if isinstance(src, str):
        return src
    raise ValueError(
        "regex pattern object exposes no string source; refusing to rebuild an "
        "unbounded pattern from it"
    )


def reharden(pattern, flags=0):
    """Re-derive a fresh, wall-clock-capped :class:`TimedPattern` from ``pattern``'s
    SOURCE, discarding any existing wrapper. Unlike :func:`compile`, an incoming
    ``TimedPattern`` is never returned as-is, so a disabled cap cannot survive."""
    return compile(source_of(pattern), flags)
