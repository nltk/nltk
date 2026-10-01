"""
Test Aline algorithm for aligning phonetic sequences
"""

from nltk.metrics import aline


def test_aline():
    result = aline.align("θin", "tenwis")
    expected = [[("θ", "t"), ("i", "e"), ("n", "n")]]

    assert result == expected

    result = aline.align("jo", "ʒə")
    expected = [[("j", "ʒ"), ("o", "ə")]]

    assert result == expected

    result = aline.align("pematesiweni", "pematesewen")
    expected = [
        [
            ("p", "p"),
            ("e", "e"),
            ("m", "m"),
            ("a", "a"),
            ("t", "t"),
            ("e", "e"),
            ("s", "s"),
            ("i", "e"),
            ("w", "w"),
            ("e", "e"),
            ("n", "n"),
        ]
    ]

    assert result == expected

    result = aline.align("tuwθ", "dentis")
    expected = [[("t", "t"), ("u", "i"), ("w", "-"), ("θ", "s")]]

    assert result == expected


def test_aline_delta():
    """
    Test aline for computing the difference between two segments
    """
    assert aline.delta("p", "q") == 20.0
    assert aline.delta("a", "A") == 0.0


class TestAlineEdgeCases:
    def test_identical_strings(self):
        """Aligning identical strings should produce perfect 1-to-1 mapping."""
        result = aline.align("pat", "pat")
        assert result == [[("p", "p"), ("a", "a"), ("t", "t")]]

    def test_invalid_segment_raises(self):
        """Unknown segments should raise ValueError, not KeyError."""
        try:
            aline.align("p", "!")
            assert False, "Expected ValueError"
        except ValueError:
            pass
        try:
            aline.align("☺", "t")
            assert False, "Expected ValueError"
        except ValueError:
            pass

    def test_single_char(self):
        """Single characters should align."""
        result = aline.align("p", "p")
        assert result == [[("p", "p")]]

    def test_single_char_different(self):
        """Different single consonants should still align."""
        result = aline.align("p", "t")
        assert result == [[("p", "t")]]

    def test_single_vowel(self):
        """Single vowels should align."""
        result = aline.align("a", "e")
        assert result == [[("a", "e")]]


# ---------------------------------------------------------
# Feature matrix correctness
# ---------------------------------------------------------


class TestFeatureMatrix:
    """Verify IPA feature assignments match phonetic definitions."""

    def test_all_consonants_in_feature_matrix(self):
        """Every consonant in the consonants list should be in feature_matrix."""
        for c in aline.consonants:
            assert (
                c in aline.feature_matrix
            ), f"Consonant {c!r} missing from feature_matrix"

    def test_all_vowels_in_feature_matrix(self):
        """Every vowel (place='vowel' entry) should be a valid key."""
        for v in aline.vowels:
            assert v in aline.feature_matrix, f"Vowel {v!r} missing from feature_matrix"

    def test_no_trailing_spaces_in_consonants(self):
        """No consonant entry should have trailing whitespace."""
        for c in aline.consonants:
            assert c == c.strip(), f"Consonant {c!r} has trailing whitespace"

    def test_no_trailing_spaces_in_vowels(self):
        """No vowel entry should have trailing whitespace."""
        for v in aline.vowels:
            assert v == v.strip(), f"Vowel {v!r} has trailing whitespace"

    def test_no_trailing_spaces_in_feature_matrix_keys(self):
        """No feature_matrix key should have trailing whitespace."""
        for k in aline.feature_matrix:
            assert k == k.strip(), f"Feature matrix key {k!r} has trailing whitespace"

    def test_consonants_not_vowel_place(self):
        """No consonant should have place='vowel'."""
        for c in aline.consonants:
            assert (
                aline.feature_matrix[c]["place"] != "vowel"
            ), f"Consonant {c!r} has place='vowel'"

    def test_vowels_have_vowel_place(self):
        """All vowels in feature_matrix should have place='vowel'."""
        for v in aline.vowels:
            assert (
                aline.feature_matrix[v]["place"] == "vowel"
            ), f"Vowel {v!r} has place={aline.feature_matrix[v]['place']!r}"

    # IPA rounding checks
    def test_unrounded_vowels(self):
        """Vowels that are unrounded in IPA should have round='minus'."""
        unrounded = ["i", "e", "ɛ", "a", "ɯ", "ɘ", "ɜ", "ɐ", "ɑ", "ʌ", "ɤ"]
        for v in unrounded:
            if v in aline.feature_matrix:
                assert (
                    aline.feature_matrix[v]["round"] == "minus"
                ), f"IPA unrounded vowel {v!r} has round={aline.feature_matrix[v]['round']!r}"

    def test_rounded_vowels(self):
        """Vowels that are rounded in IPA should have round='plus'."""
        rounded = ["o", "u", "y", "ɒ", "ɵ", "ʏ", "ʊ"]
        for v in rounded:
            if v in aline.feature_matrix:
                assert (
                    aline.feature_matrix[v]["round"] == "plus"
                ), f"IPA rounded vowel {v!r} has round={aline.feature_matrix[v]['round']!r}"

    # IPA height checks
    def test_close_mid_vowels(self):
        """Close-mid vowels should have high='mid', not 'high'."""
        close_mid = ["ɘ", "ɵ"]
        for v in close_mid:
            if v in aline.feature_matrix:
                assert (
                    aline.feature_matrix[v]["high"] == "mid"
                ), f"Close-mid vowel {v!r} has high={aline.feature_matrix[v]['high']!r}"


class TestScoringFunctions:
    def test_delta_identical_consonants(self):
        """Identical consonants should have delta = 0."""
        assert aline.delta("p", "p") == 0.0
        assert aline.delta("t", "t") == 0.0
        assert aline.delta("s", "s") == 0.0

    def test_delta_identical_vowels(self):
        """Identical vowels should have delta = 0."""
        assert aline.delta("a", "a") == 0.0
        assert aline.delta("i", "i") == 0.0

    def test_delta_similar_consonants(self):
        """Similar consonants (same place) should have small delta."""
        # p and b differ only in voicing
        d_pb = aline.delta("p", "b")
        # p and k differ in place
        d_pk = aline.delta("p", "k")
        assert d_pb < d_pk

    def test_delta_symmetric(self):
        """Delta should be symmetric: delta(a,b) == delta(b,a)."""
        assert aline.delta("p", "t") == aline.delta("t", "p")
        assert aline.delta("a", "o") == aline.delta("o", "a")
        assert aline.delta("s", "ʃ") == aline.delta("ʃ", "s")

    def test_sigma_skip_negative(self):
        """sigma_skip should return a negative value (penalty)."""
        assert aline.sigma_skip("p") < 0
        assert aline.sigma_skip("a") < 0

    def test_sigma_sub_identical(self):
        """Substituting identical segments should give max score."""
        score_identical = aline.sigma_sub("p", "p")
        score_different = aline.sigma_sub("p", "t")
        assert score_identical > score_different

    def test_sigma_exp_returns_value(self):
        """sigma_exp should return a numeric value without error."""
        result = aline.sigma_exp("a", ("p", "b"))
        assert isinstance(result, (int, float))

    def test_V_vowel_gt_consonant(self):
        """V() for a vowel should be >= V() for a consonant."""
        # V(p) for vowel uses C_vwl, for consonant returns 0
        v_vowel = aline.V("a")
        v_consonant = aline.V("p")
        assert v_vowel >= v_consonant

    def test_R_returns_list(self):
        """R() should return relevant features for the segment pair."""
        # R takes two segments and returns the relevant feature list
        r_consonants = aline.R("p", "t")
        r_vowels = aline.R("a", "e")
        assert isinstance(r_consonants, list)
        assert isinstance(r_vowels, list)
        assert len(r_consonants) > 0
        assert len(r_vowels) > 0


class TestAlignmentProperties:
    def test_alignment_not_empty(self):
        """Alignment of non-empty strings should produce non-empty result."""
        result = aline.align("pat", "kat")
        assert len(result) > 0
        assert len(result[0]) > 0

    def test_alignment_returns_list_of_lists(self):
        """align() should return a list of alignment lists."""
        result = aline.align("pa", "ta")
        assert isinstance(result, list)
        assert isinstance(result[0], list)
        assert isinstance(result[0][0], tuple)
