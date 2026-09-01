# Natural Language Toolkit: redos chokepoint-safety tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""``nltk.redos`` is the single point every regex in the library routes through,
so the module itself must not be attackable. These tests attack redos directly:

* :func:`redos.check_pattern` must not itself be a DoS (it runs on *every*
  pattern) -- a run of unclosed ``{`` used to rescan to end-of-source per brace,
  which is O(n**2), and a giant ``{999...}`` count made it ``int()`` a digit run
  past CPython's limit. Both are now refused/bounded in linear time.
* The ``re``-compatible module helpers must match ``re`` semantics AND put every
  pattern through the guards; the compile cache must be memory-bounded.
* Compile failures must surface as a ``re.error`` subclass so a call site that
  moved off ``re`` and still ``except re.error:`` keeps working (the ``regex``
  engine's own ``regex.error`` is *not* a ``re.error``).
* The extra features the ``regex`` engine has over stdlib ``re`` -- recursion
  ``(?R)``, fuzzy matching ``{e<=n}``, back-references, conditionals,
  variable-length look-behind -- are additional attack surface, so each must be
  bounded (by the wall-clock timeout) or handled, never hang or crash.

Why the ``regex`` engine at all: stdlib ``re`` has NO match timeout, so a
catastrophically backtracking pattern hangs the interpreter with no way to stop
it (``re.compile(r"(.*a){25}z").search("a"*44)`` never returns). ``regex``
linearises many such patterns outright and, crucially, accepts ``timeout=`` for
the ones it does not -- that timeout is redos's actual guarantee.
"""

import re
import time

import pytest

from nltk import redos


def _elapsed(fn):
    start = time.perf_counter()
    try:
        fn()
    except Exception:
        pass
    return time.perf_counter() - start


# ==========================================================================
# check_pattern must not be a DoS itself (it runs on every pattern)
# ==========================================================================


class TestCheckPatternSelfDoS:
    def test_unclosed_brace_run_is_linear(self):
        # Pre-fix: `scan.find("}", i+1)` per `{` rescanned to end -> O(n**2).
        # Now the scan is windowed, so a run of `{` is linear.
        t1 = _elapsed(lambda: redos.check_pattern("{" * 25000))
        t4 = _elapsed(lambda: redos.check_pattern("{" * 100000))  # 4x
        assert t4 < 8 * t1 + 0.2

    def test_giant_count_is_refused_cleanly(self):
        # A `{` followed by a digit run too long to close in the window is a
        # giant repetition; refuse it as a ValueError rather than int()-ing a
        # huge digit string (which raised the confusing int-str-limit error).
        with pytest.raises(ValueError):
            redos.check_pattern("a{" + "9" * 20000 + "}")

    def test_literal_brace_not_a_quantifier_is_allowed(self):
        # `{` not opening a quantifier (no digit / no close) stays a literal.
        redos.check_pattern(r"a\{b")  # escaped brace
        redos.check_pattern("a{b}c")  # non-numeric body -> literal
        assert redos.compile("a{b}c").match("a{b}c") is not None

    def test_real_counted_repeat_bomb_still_refused(self):
        # ``(?:xyz){40000}`` (body 3 * 39999 = 119997) is a real bomb; ``(?:xy)``
        # would be 79998 < the limit and must NOT be refused (see the
        # group-introducer tests) -- only the BODY drives the product.
        for bomb in ["(aaa){50000}", "(?:xyz){40000}", "a{50000}{50000}"]:
            with pytest.raises(ValueError):
                redos.compile(bomb)

    def test_deep_nesting_and_oversize_still_refused(self):
        with pytest.raises(ValueError):
            redos.check_pattern("(" * (redos.MAX_NESTING_DEPTH + 5))
        with pytest.raises(ValueError):
            redos.check_pattern("[" * (redos.MAX_NESTING_DEPTH + 5))
        with pytest.raises(ValueError):
            redos.check_pattern("a" * (redos.MAX_PATTERN_LENGTH + 1))


# ==========================================================================
# check_pattern must count a group's BODY, not its introducer syntax
# ==========================================================================


class TestCheckPatternGroupIntroducer:
    # A group introducer -- ``(?:``, ``(?P<name>``, ``(?=``/``(?!``, ``(?<=``/
    # ``(?<!``, ``(?>``, ``(?#comment)``, inline ``(?flags:`` -- is syntax, not
    # repeatable atoms. Counting it (the pre-fix behaviour) inflated the
    # repetition product and FALSELY refused legitimate patterns whose real
    # expansion is under the limit; only the group BODY may drive the product.
    @pytest.mark.parametrize(
        "pattern",
        [
            "(?:a){99999}",  # real product 99998 < 100000
            "(?:ab){40000}",  # 2 * 39999 = 79998
            "(?P<g>a){60000}",  # named group body is one atom
            "(?<name>a){60000}",  # regex-style named group
            "(?=abc)(?:x){50000}",  # lookahead (zero-width) + group
            "(?!no)(?:y){70000}",  # negative lookahead
            "(?<=ab)x{90000}",  # lookbehind + atom
            "(?i:abc){30000}",  # inline scoped flags
            "(?#a comment)(a){99999}",  # comment group is inert
            "(?:a){50001}",  # just over half the limit, still fine
        ],
    )
    def test_legit_introducer_patterns_accepted(self, pattern):
        # Accepted by the guard AND genuinely compilable by the engine (so these
        # are real, valid patterns the guard must not reject).
        import regex

        redos.check_pattern(pattern)  # must not raise
        assert regex.compile(pattern) is not None
        assert isinstance(redos.compile(pattern), redos.TimedPattern)

    @pytest.mark.parametrize(
        "pattern",
        [
            "(?:aaa){50000}",  # body 3 * 49999 = 149997 -> real bomb
            "(?:aa){60000}",  # 2 * 59999 = 119998
            "(?:a){200000}",  # huge count
            "(?P<g>aaaa){40000}",  # named group, body 4 * 39999
            "(?=x)(?:aaa){50000}",  # lookahead + bomb body
            "(?:(?:a){400}){400}",  # nested: 400 * 400 = 160000
            "(?:x){" + "9" * 20000 + "}",  # giant count digits
        ],
    )
    def test_bombs_with_introducers_still_refused(self, pattern):
        # The fix excludes only introducer SYNTAX; the body atoms are still
        # counted, so a genuine counted-repetition bomb wrapped in any group form
        # must STILL be refused -- no exploit leaks through.
        with pytest.raises(ValueError):
            redos.check_pattern(pattern)

    def test_many_introducers_is_linear_and_accepted(self):
        # Many sequential non-capturing groups: the introducer skip must be
        # linear (a windowed scan, not O(n**2)), and 15000 single-atom groups are
        # well under the repetition limit, so the pattern must be accepted.
        pat = "(?:a)" * 15000
        assert _elapsed(lambda: redos.check_pattern(pat)) < 1.0
        redos.check_pattern(pat)  # accepted -- no false bomb


# ==========================================================================
# re-compatible module helpers: same results, guards applied, cache bounded
# ==========================================================================


class TestModuleLevelAPI:
    def test_helpers_match_re_semantics(self):
        assert redos.match(r"(\w+)", "hi there").group(1) == "hi"
        assert redos.fullmatch(r"\d+", "123").group(0) == "123"
        assert redos.search(r"b(o)", "foo bo").group(1) == "o"
        assert redos.findall(r"\d+", "a1b22c333") == ["1", "22", "333"]
        assert [m.group() for m in redos.finditer(r"\d+", "a1b22")] == ["1", "22"]
        assert redos.split(r"\s*,\s*", "a, b ,c") == ["a", "b", "c"]
        assert redos.split(r",", "a,b,c,d", 2) == ["a", "b", "c,d"]
        assert redos.sub(r"\d", "#", "a1b2") == "a#b#"
        assert redos.sub(r"\d", "#", "a1b2c3", 2) == "a#b#c3"
        assert redos.subn(r"\d", "#", "a1b2") == ("a#b#", 2)
        assert redos.match("abc", "ABC", re.I).group() == "ABC"
        assert redos.findall("^x", "x\nx\nx", re.M) == ["x", "x", "x"]

    def test_helpers_apply_the_guards(self):
        # A compile-time bomb is refused through the helper...
        with pytest.raises(ValueError):
            redos.match("(x){999999}", "x")
        # ...and a match-time bomb is wall-clock bounded through the helper.
        with pytest.raises(TimeoutError):
            redos.search(r"(.*a){25}z", "a" * 400, flags=0)  # long enough to backtrack

    def test_compile_cache_is_length_bounded(self):
        # Long (attacker-sized) patterns must not accumulate in the cache.
        before = redos._cached_compile.cache_info().currsize
        big = "z" * (redos._MAX_CACHE_PATTERN_LEN + 1)
        for i in range(30):
            redos.match(big + str(i), "zzz")
        after = redos._cached_compile.cache_info().currsize
        assert after == before  # none of the oversize patterns were cached


# ==========================================================================
# error contract: a compile failure is a re.error subclass
# ==========================================================================


class TestErrorContract:
    def test_redos_error_is_re_error(self):
        assert issubclass(redos.error, re.error)

    def test_invalid_pattern_raises_re_error(self):
        # The regex engine's own regex.error is NOT a re.error; redos normalises
        # it so `except re.error:` keeps working after a site moves to redos.
        with pytest.raises(re.error):
            redos.compile("(unbalanced")
        with pytest.raises(re.error):
            redos.match("(?P<>bad)", "x")


# ==========================================================================
# regex-only features are extra attack surface: each must be bounded
# ==========================================================================


class TestRegexOnlySurfacesBounded:
    # These constructs do not exist in stdlib re, so they only reach the engine
    # via a caller-supplied pattern; each must be bounded, never hang/crash.
    @pytest.mark.parametrize(
        "pattern,bait",
        [
            (r"\((?:[^()]|(?R))*\)", "(" * 20000),  # recursion, catastrophic input
            (r"(a+)+\1$", "a" * 45 + "!"),  # back-reference bomb
            (r"(a)?(?(1)b|c)+$", "b" * 45 + "!"),  # conditional
            (r"(?<=a{1,5000})b", "a" * 20000),  # variable-length look-behind
            (r"(pattern){e<=5}", "x" * 4000),  # fuzzy matching
            (r"(.{20}){e<=19}", "z" * 20000),  # fuzzy over a long input
        ],
    )
    def test_bounded_or_handled(self, pattern, bait):
        # Completing quickly, or firing the timeout, are both fine; hanging past
        # a small multiple of the timeout is not.
        tp = redos.compile(pattern)
        dt = _elapsed(lambda: tp.search(bait, timeout=0.5))
        assert dt < 3.0

    def test_deep_recursion_does_not_stack_overflow(self):
        # 100k-deep balanced nesting must not crash the native stack; possessive
        # quantifiers isolate the recursion-depth question from backtracking.
        tp = redos.compile(r"\((?:[^()]++|(?R))*+\)")
        dt = _elapsed(lambda: tp.match("(" * 100000 + ")" * 100000, timeout=1.0))
        assert dt < 3.0


# ==========================================================================
# the wall-clock timeout is the guarantee: it fires on every match method
# ==========================================================================


class TestTimeoutIsTheGuarantee:
    # `(.*a){25}z` catastrophically backtracks in BOTH engines at this length;
    # stdlib re would hang forever (no timeout), so redos's cap is what saves it.
    EVIL = r"(.*a){25}z"
    BAIT = "a" * 400

    def test_every_match_method_is_bounded(self):
        # No method may hang; each either fires the timeout or fails fast.
        tp = redos.compile(self.EVIL)
        for call in (
            lambda: tp.search(self.BAIT, timeout=0.3),
            lambda: tp.match(self.BAIT, timeout=0.3),
            lambda: tp.findall(self.BAIT, timeout=0.3),
            lambda: tp.sub("x", self.BAIT, timeout=0.3),
            lambda: tp.subn("x", self.BAIT, timeout=0.3),
            lambda: tp.split(self.BAIT, timeout=0.3),
            lambda: list(tp.finditer(self.BAIT, timeout=0.3)),
        ):
            assert _elapsed(call) < 2.0

    def test_backtracking_methods_fire_the_timeout(self):
        # The methods that scan the whole input (all but anchored ``match``,
        # which fails fast here) must raise TimeoutError, proving the wall-clock
        # cap -- not luck -- is what bounds them.
        tp = redos.compile(self.EVIL)
        for call in (
            lambda: tp.search(self.BAIT, timeout=0.3),
            lambda: tp.findall(self.BAIT, timeout=0.3),
            lambda: tp.sub("x", self.BAIT, timeout=0.3),
            lambda: tp.subn("x", self.BAIT, timeout=0.3),
            lambda: tp.split(self.BAIT, timeout=0.3),
            lambda: list(tp.finditer(self.BAIT, timeout=0.3)),
        ):
            with pytest.raises(TimeoutError):
                call()

    def test_bytes_pattern_works(self):
        assert redos.compile(rb"\d+").findall(b"a1b22") == [b"1", b"22"]
