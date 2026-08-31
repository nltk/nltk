# Natural Language Toolkit: tests for redos.source_of / redos.reharden
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Re-deriving a trusted, capped pattern from an untrusted reconstructed one.
``source_of`` extracts only the source string; ``reharden`` recompiles it under
a fresh wall-clock cap, so a disabled/absent cap on the input cannot survive."""

import re

import pytest
import regex

from nltk import redos
from nltk.redos import _UNSET, TimedPattern

CATASTROPHIC = r"(a|a)*$"


def test_source_of_string_is_itself():
    assert redos.source_of("a+b*") == "a+b*"


def test_source_of_compiled_regex():
    assert redos.source_of(regex.compile("[0-9]+")) == "[0-9]+"


def test_source_of_stdlib_re():
    assert redos.source_of(re.compile("x?y")) == "x?y"


def test_source_of_timedpattern_even_with_cap_disabled():
    tp = TimedPattern(regex.compile(CATASTROPHIC), timeout=None)
    assert redos.source_of(tp) == CATASTROPHIC


def test_source_of_bytes_pattern_is_decoded():
    assert redos.source_of(regex.compile(b"ab+")) == "ab+"


def test_source_of_sourceless_raises():
    with pytest.raises(ValueError):
        redos.source_of(object())


def test_reharden_string_is_capped():
    tp = redos.reharden("a+")
    assert isinstance(tp, TimedPattern)
    assert tp._timeout is _UNSET  # -> DEFAULT_TIMEOUT applies at match time


def test_reharden_discards_a_disabled_cap():
    hostile = TimedPattern(regex.compile(CATASTROPHIC), timeout=None)
    fresh = redos.reharden(hostile)
    assert isinstance(fresh, TimedPattern)
    assert fresh is not hostile
    assert fresh._timeout is _UNSET  # the disabled cap did NOT survive


def test_compile_returns_disabled_cap_as_is_but_reharden_does_not():
    """The exact reason reharden exists: compile short-circuits on a TimedPattern
    and hands the uncapped wrapper straight back; reharden rebuilds from source."""
    hostile = TimedPattern(regex.compile(CATASTROPHIC), timeout=None)
    assert redos.compile(hostile) is hostile
    assert redos.compile(hostile)._timeout is None  # cap still disabled
    assert redos.reharden(hostile)._timeout is _UNSET  # cap restored


def test_reharden_preserves_matching_behaviour():
    tp = redos.reharden(regex.compile("[0-9]+"))
    assert tp.match("123") is not None
    assert tp.match("abc") is None


def test_reharden_sourceless_raises():
    with pytest.raises(ValueError):
        redos.reharden(object())
