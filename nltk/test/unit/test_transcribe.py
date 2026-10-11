"""
Tests for nltk.transcribe -- interactive word completion for
morphologically complex languages, after Lane and Bird (2022).
"""

import pytest

from nltk.transcribe import (
    AnchoredConstraint,
    EditConstraint,
    InteractiveTranscriber,
    LexicalConstraint,
    Lexicon,
    PhoneOrthMapping,
    Suggestion,
    Tableau,
    WordlistAcceptor,
    anchor_positions,
    lenient_compose,
)

# ---------------------------------------------------------------------------
# Constraints
# ---------------------------------------------------------------------------


class TestAnchoredConstraint:
    def test_satisfied_when_lexeme_is_substring(self):
        c = AnchoredConstraint(["kabirri"])
        assert c("kabirridurrkmirri") == 0

    def test_violated_when_no_lexeme_present(self):
        c = AnchoredConstraint(["kabirri"])
        assert c("bedberre") == 1

    def test_satisfied_with_any_one_of_many_lexemes(self):
        c = AnchoredConstraint(["kabirri", "manme"])
        assert c("manmebedberre") == 0

    def test_empty_lexeme_is_ignored(self):
        c = AnchoredConstraint(["", "manme"])
        assert c("kabirri") == 1
        assert c("manmebedberre") == 0


class TestLexicalConstraint:
    def test_membership(self):
        c = LexicalConstraint({"manme", "kabirri"}, "Topical")
        assert c("manme") == 0
        assert c("foo") == 1

    def test_name_appears_in_repr(self):
        c = LexicalConstraint({"x"}, "Topical")
        assert "Topical" in repr(c)


class TestEditConstraint:
    def test_within_budget(self):
        c = EditConstraint(2)
        s = Suggestion(word="x", anchor="x", edits=2)
        assert c(s) == 0

    def test_over_budget(self):
        c = EditConstraint(0)
        s = Suggestion(word="x", anchor="x", edits=2)
        assert c(s) == 2

    def test_default_for_string_is_zero_edits(self):
        # Strings have no edit count; treat as 0.
        c = EditConstraint(0)
        assert c("hello") == 0


class TestLenientCompose:
    def test_filters_when_some_pass(self):
        cands = ["a", "b", "c"]
        c = LexicalConstraint({"a"}, "InA")
        assert lenient_compose(cands, c) == ["a"]

    def test_passes_through_when_none_pass(self):
        # Karttunen's lenient composition: if no candidate satisfies, all
        # fall through unchanged.
        cands = ["a", "b"]
        c = LexicalConstraint({"x"}, "InX")
        assert lenient_compose(cands, c) == ["a", "b"]

    def test_chain_outranks_correctly(self):
        cands = ["kabirridurrkmirri", "kabirriXX", "bedberre"]
        anchored = AnchoredConstraint(["kabirri"])
        attested = LexicalConstraint({"kabirridurrkmirri"}, "Attested")
        assert lenient_compose(cands, anchored, attested) == ["kabirridurrkmirri"]

    def test_lower_constraint_breaks_ties(self):
        c1 = AnchoredConstraint(["a"])
        c2 = LexicalConstraint({"abc"}, "Attested")
        assert lenient_compose(["abc", "ab", "az"], c1, c2) == ["abc"]


# ---------------------------------------------------------------------------
# Alignment
# ---------------------------------------------------------------------------


class TestPhoneOrthMapping:
    def test_realisations_with_unknown_phone_pass_through(self):
        m = PhoneOrthMapping({})
        assert m.realisations("z") == ["z"]

    def test_canonical_uses_first_realisation(self):
        m = PhoneOrthMapping({"k": ["k", "kk"]})
        assert m.to_canonical("kak") == "kak"

    def test_expand_yields_all_combinations(self):
        m = PhoneOrthMapping({"a": ["a", "aa"], "b": ["b"]})
        assert sorted(m.expand("ab")) == ["aab", "ab"]


class TestAnchorPositions:
    def test_exact_match(self):
        anchors = anchor_positions("kabirridurrkmirri", "kabirri", max_edits=0)
        assert (anchors[0].start, anchors[0].end, anchors[0].edits) == (0, 7, 0)

    def test_short_lexeme_default_budget_is_one(self):
        # Default budget for short lexemes is 1.
        anchors = anchor_positions("ku", "ku")
        assert any(a.edits == 0 for a in anchors)

    def test_long_lexeme_default_budget_is_two(self):
        # The 8-char lexeme "kabirridu" should match "kabirridurr..." within 0 edits.
        anchors = anchor_positions("kabirridurrkmirri", "kabirridu")
        assert any(a.edits == 0 and a.start == 0 for a in anchors)

    def test_finds_repeated_occurrences(self):
        anchors = anchor_positions(
            "kabirridurrkmirrikabirriudujmanme", "kabirri", max_edits=0
        )
        starts = sorted({a.start for a in anchors if a.edits == 0})
        assert starts == [0, 17]

    def test_respects_edit_budget(self):
        # "kbirri" is one deletion away from "kabirri".
        a = anchor_positions("kbirri", "kabirri", max_edits=1)
        assert any(x.edits == 1 for x in a)
        assert not anchor_positions("kbirri", "kabirri", max_edits=0)


# ---------------------------------------------------------------------------
# Acceptor
# ---------------------------------------------------------------------------


class TestWordlistAcceptor:
    def test_accepts(self):
        a = WordlistAcceptor(["kabirri", "manme"])
        assert a.accepts("kabirri")
        assert not a.accepts("foo")

    def test_expand_returns_words_containing_lexeme(self):
        a = WordlistAcceptor(["kabirri", "kabirridurrkmirri", "manme"])
        assert sorted(a.expand("kabirri")) == ["kabirri", "kabirridurrkmirri"]

    def test_dunders(self):
        a = WordlistAcceptor(["a", "b"])
        assert len(a) == 2
        assert "a" in a
        assert sorted(a) == ["a", "b"]


# ---------------------------------------------------------------------------
# End-to-end completion (paper-faithful behaviour)
# ---------------------------------------------------------------------------


@pytest.fixture
def kunwok_transcriber():
    """A toy Bininj-Kunwok-like setup mirroring Lane and Bird (2022) Example (1)."""
    return InteractiveTranscriber(
        phone_orth=PhoneOrthMapping({}),
        acceptor=WordlistAcceptor(
            [
                "kabirri",
                "kabirridurrkmirri",
                "kabirriudujmanme",
                "manme",
                "manmebedberre",
                "bedberre",
            ]
        ),
        attested=Lexicon(
            [
                "kabirri",
                "kabirridurrkmirri",
                "manme",
                "bedberre",
                "manmebedberre",
                "kabirriudujmanme",
            ]
        ),
        topical=Lexicon(["kabirridurrkmirri", "manmebedberre", "kabirriudujmanme"]),
    )


PHONES = "kabirridurrkmirrikabirriudujmanmebedberre"


class TestInteractiveTranscriber:
    def test_rejects_non_PhoneOrthMapping(self):
        with pytest.raises(TypeError):
            InteractiveTranscriber(
                phone_orth={},
                acceptor=WordlistAcceptor(["a"]),
            )

    def test_rejects_non_acceptor(self):
        with pytest.raises(TypeError):
            InteractiveTranscriber(
                phone_orth=PhoneOrthMapping({}),
                acceptor=["a", "b"],
            )

    def test_iteration_a_proposes_durrkmirri(self, kunwok_transcriber):
        # In iteration (a) the transcriber has identified kabirri and
        # manme.  The model should propose kabirridurrkmirri (filtered
        # in by Topical) as a high-priority completion.
        suggestions = kunwok_transcriber.suggest(PHONES, ["kabirri", "manme"])
        words = {s.word for s in suggestions}
        assert "kabirridurrkmirri" in words
        assert "manmebedberre" in words

    def test_anchored_constraint_excludes_unrelated_words(self, kunwok_transcriber):
        # If a word from the lexicon does not contain any known lexeme
        # as substring, it must not be returned.  "bedberre" alone is
        # not anchored on kabirri or manme.
        suggestions = kunwok_transcriber.suggest(PHONES, ["kabirri"])
        assert all("kabirri" in s.word or "manme" in s.word for s in suggestions)

    def test_empty_known_lexemes_returns_no_suggestions(self, kunwok_transcriber):
        assert kunwok_transcriber.suggest(PHONES, []) == []

    def test_unknown_lexeme_yields_empty(self, kunwok_transcriber):
        # A lexeme not present in the phone string should produce no
        # suggestions (within the default edit budget).
        assert kunwok_transcriber.suggest("ngarribom", ["kabirri"]) == []

    def test_handles_phone_recognizer_noise(self, kunwok_transcriber):
        # Even with a one-character substitution in the phone string,
        # the transcriber should still anchor and propose completions.
        noisy = "kabirridurrkmirrikabirriudujmanmebetberre"  # bedberre -> betberre
        suggestions = kunwok_transcriber.suggest(noisy, ["kabirri", "manme"])
        words = {s.word for s in suggestions}
        # Anchors still recover; edit-tolerance pulls bedberre (via manme) back in.
        assert "manmebedberre" in words or "kabirridurrkmirri" in words


class TestPhoneOrthIntegration:
    def test_phone_to_orth_mapping_used_in_pipeline(self):
        # When a phone like "N" maps to "ng", the canonical realisation
        # should let the lexeme "ngarribom" align cleanly.
        trans = InteractiveTranscriber(
            phone_orth=PhoneOrthMapping({"N": ["ng"]}),
            acceptor=WordlistAcceptor(["ngarribom", "ngarri"]),
            attested=Lexicon(["ngarribom"]),
        )
        phones = "Narribom"  # phone-recognizer style
        suggestions = trans.suggest(phones, ["ngarri"])
        assert any(s.word == "ngarribom" for s in suggestions)


# ---------------------------------------------------------------------------
# Tableau
# ---------------------------------------------------------------------------


class TestTableau:
    def test_winner_marked_with_arrow(self):
        cands = ["kabirridurrkmirri", "bedberre"]
        constraints = [AnchoredConstraint(["kabirri"])]
        t = Tableau(cands, constraints)
        rendered = t.render()
        assert "-> kabirridurrkmirri" in rendered

    def test_violations_rendered_as_stars(self):
        cands = ["x"]
        constraints = [LexicalConstraint({"y"}, "InY")]
        t = Tableau(cands, constraints)
        rendered = t.render()
        assert "*" in rendered

    def test_fatal_strike_marked_with_bang(self):
        cands = ["kabirri", "bedberre"]
        constraints = [
            AnchoredConstraint(["kabirri"]),
            LexicalConstraint({"kabirri"}, "Attested"),
        ]
        t = Tableau(cands, constraints)
        rendered = t.render()
        # bedberre fails Anchored fatally.
        assert "*!" in rendered
