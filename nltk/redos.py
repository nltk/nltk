# Natural Language Toolkit: ReDoS backstop for caller-supplied patterns
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org>
# For license information, see LICENSE.TXT

r"""
A wall-clock backstop for NLTK code paths that compile *caller-supplied*
regular expressions or tag patterns.

Several public APIs accept a pattern from the caller and run it over
(possibly attacker-controlled) text:

* :class:`nltk.tokenize.RegexpTokenizer` / ``regexp_tokenize`` -- ``pattern``
* :class:`nltk.tag.RegexpTagger` -- the ``regexp`` of each ``(regexp, tag)`` pair
* :func:`nltk.tgrep.tgrep_compile` -- the ``/regex/`` node literal in a query
* :class:`nltk.chunk.regexp.RegexpChunkRule` and its ``ChunkRule`` / ``StripRule``
  / ``UnChunkRule`` / ``MergeRule`` / ``SplitRule`` subclasses -- the tag pattern

A crafted pattern (e.g. ``(a+)+$`` or ``(a|a)*$``) can trigger catastrophic
backtracking and pin a CPU core indefinitely -- a denial of service
(CWE-1333). This module centralises a single, tested defence used by all of
those sinks, in two layers:

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

import regex

__all__ = ["DEFAULT_TIMEOUT", "TimedPattern", "compile"]

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
    compiled = regex.compile(src, flags)
    return TimedPattern(compiled, timeout)
