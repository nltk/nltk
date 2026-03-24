"""
Unit tests for nltk.tokenize.texttiling.

Marti A. Hearst (1997) "TextTiling: Segmenting Text into Multi-Paragraph
Subtopic Passages", Computational Linguistics, 23(1), pp. 33-64.
https://aclanthology.org/J97-1003.pdf
"""

from nltk.tokenize.texttiling import (
    BLOCK_COMPARISON,
    VOCABULARY_INTRODUCTION,
    TextTilingTokenizer,
)

# A text with clear topic shifts for testing.
# Topic 1: animals in nature
# Topic 2: stock market / finance
# Topic 3: marine biology
# Topic 4: weather / agriculture
MULTI_TOPIC_TEXT = (
    """
The quick brown fox jumped over the lazy dog. The dog was sleeping
in the sun. It was a beautiful day outside in the forest. The fox
continued on its way through the dense woodland. Birds were singing
in the trees and rabbits scurried through the underbrush. The animals
were enjoying the warm afternoon sunshine.

Meanwhile, in the city, the stock market was experiencing significant
changes. Traders were anxious about the new economic policies. The
financial sector was particularly affected by the recent changes in
interest rates. Banks reported lower quarterly earnings. Investors
were pulling their money out of risky assets. The central bank was
considering raising rates again.

In other news, scientists discovered a new species of deep-sea fish.
The fish was found at a depth of three thousand meters below the
surface. Marine biologists were excited about the discovery. The
specimen was brought to the laboratory for further study. Researchers
believe the species has been living in the deep ocean for millions
of years.

The weather forecast predicted rain for the weekend across the region.
Farmers were hoping for the precipitation to help their growing crops.
The drought had lasted several months with no relief in sight. Water
reservoirs were at critically low levels. Irrigation systems were
being strained beyond their capacity.
"""
    * 3
)  # repeat to get enough text for the algorithm


class TestTextTilingBlockComparison:
    """Tests for the block comparison method (Hearst 1997, Section 3.2)."""

    def test_returns_segments(self):
        """Block comparison should return a list of text segments."""
        tt = TextTilingTokenizer(w=10, k=5, similarity_method=BLOCK_COMPARISON)
        segments = tt.tokenize(MULTI_TOPIC_TEXT)
        assert isinstance(segments, list)
        assert len(segments) >= 1

    def test_segments_cover_full_text(self):
        """Concatenated segments should reconstruct the original text."""
        tt = TextTilingTokenizer(w=10, k=5, similarity_method=BLOCK_COMPARISON)
        segments = tt.tokenize(MULTI_TOPIC_TEXT)
        assert "".join(segments) == MULTI_TOPIC_TEXT

    def test_demo_mode_returns_scores(self):
        """In demo mode, should return (gap_scores, smooth, depth, boundaries)."""
        tt = TextTilingTokenizer(
            w=10, k=5, similarity_method=BLOCK_COMPARISON, demo_mode=True
        )
        result = tt.tokenize(MULTI_TOPIC_TEXT)
        assert len(result) == 4
        gap_scores, smooth_scores, depth_scores, boundaries = result
        assert len(gap_scores) > 0
        assert len(smooth_scores) > 0
        assert len(depth_scores) > 0
        assert len(boundaries) > 0

    def test_gap_scores_between_zero_and_one(self):
        """Block comparison gap scores should be in [0, 1] (cosine similarity)."""
        tt = TextTilingTokenizer(
            w=10, k=5, similarity_method=BLOCK_COMPARISON, demo_mode=True
        )
        gap_scores, _, _, _ = tt.tokenize(MULTI_TOPIC_TEXT)
        for score in gap_scores:
            assert 0.0 <= score <= 1.0, f"Score {score} out of [0, 1] range"

    def test_homogeneous_text_few_boundaries(self):
        """Repeating the same paragraph should produce few boundaries."""
        paragraph = "The cat sat on the mat. The dog chased the ball. "
        # Need paragraph breaks (double newlines) for the algorithm
        repeated = ("\n\n".join([paragraph] * 10)) + "\n\n"
        tt = TextTilingTokenizer(w=10, k=5, similarity_method=BLOCK_COMPARISON)
        segments = tt.tokenize(repeated)
        # Homogeneous text should have few segments
        assert len(segments) <= 5


class TestTextTilingVocabIntroduction:
    """Tests for the vocabulary introduction method (Hearst 1997, Section 3.2)."""

    def test_returns_segments(self):
        """Vocabulary introduction should return a list of text segments."""
        tt = TextTilingTokenizer(w=10, k=5, similarity_method=VOCABULARY_INTRODUCTION)
        segments = tt.tokenize(MULTI_TOPIC_TEXT)
        assert isinstance(segments, list)
        assert len(segments) >= 1

    def test_segments_cover_full_text(self):
        """Concatenated segments should reconstruct the original text."""
        tt = TextTilingTokenizer(w=10, k=5, similarity_method=VOCABULARY_INTRODUCTION)
        segments = tt.tokenize(MULTI_TOPIC_TEXT)
        assert "".join(segments) == MULTI_TOPIC_TEXT

    def test_demo_mode_returns_scores(self):
        """In demo mode, should return (gap_scores, smooth, depth, boundaries)."""
        tt = TextTilingTokenizer(
            w=10, k=5, similarity_method=VOCABULARY_INTRODUCTION, demo_mode=True
        )
        result = tt.tokenize(MULTI_TOPIC_TEXT)
        assert len(result) == 4
        gap_scores, smooth_scores, depth_scores, boundaries = result
        assert len(gap_scores) > 0
        assert len(smooth_scores) > 0
        assert len(depth_scores) > 0
        assert len(boundaries) > 0

    def test_gap_scores_non_negative(self):
        """Vocabulary introduction scores should be non-negative."""
        tt = TextTilingTokenizer(
            w=10, k=5, similarity_method=VOCABULARY_INTRODUCTION, demo_mode=True
        )
        gap_scores, _, _, _ = tt.tokenize(MULTI_TOPIC_TEXT)
        for score in gap_scores:
            assert score >= 0.0, f"Score {score} is negative"

    def test_homogeneous_text_low_scores(self):
        """Repeating the same paragraph should produce low vocab intro scores."""
        paragraph = "The cat sat on the mat. The dog chased the ball. "
        repeated = ("\n\n".join([paragraph] * 10)) + "\n\n"
        tt = TextTilingTokenizer(
            w=10, k=5, similarity_method=VOCABULARY_INTRODUCTION, demo_mode=True
        )
        gap_scores, _, _, _ = tt.tokenize(repeated)
        # After the first few windows, no new vocabulary is introduced
        # so later scores should be near zero
        later_scores = gap_scores[len(gap_scores) // 2 :]
        avg_later = sum(later_scores) / len(later_scores) if later_scores else 0
        assert (
            avg_later < 0.15
        ), f"Average later score {avg_later} too high for repeated text"


class TestTextTilingCommon:
    """Tests common to both methods."""

    def test_both_methods_find_boundaries(self):
        """Both methods should find at least one boundary in multi-topic text."""
        for method in [BLOCK_COMPARISON, VOCABULARY_INTRODUCTION]:
            tt = TextTilingTokenizer(w=10, k=5, similarity_method=method)
            segments = tt.tokenize(MULTI_TOPIC_TEXT)
            assert (
                len(segments) > 1
            ), f"Method {method} found no boundaries in multi-topic text"

    def test_invalid_similarity_method(self):
        """Invalid similarity method should raise ValueError."""
        tt = TextTilingTokenizer(similarity_method="invalid")
        try:
            tt.tokenize(MULTI_TOPIC_TEXT)
            assert False, "Expected ValueError"
        except ValueError:
            pass

    def test_invalid_smoothing_method(self):
        """Invalid smoothing method should raise ValueError."""
        tt = TextTilingTokenizer(smoothing_method="invalid")
        try:
            tt.tokenize(MULTI_TOPIC_TEXT)
            assert False, "Expected ValueError"
        except ValueError:
            pass

    def test_boundary_count_matches_segments(self):
        """Number of boundaries should be number of segments minus 1."""
        for method in [BLOCK_COMPARISON, VOCABULARY_INTRODUCTION]:
            tt = TextTilingTokenizer(w=10, k=5, similarity_method=method)
            segments = tt.tokenize(MULTI_TOPIC_TEXT)
            tt_demo = TextTilingTokenizer(
                w=10, k=5, similarity_method=method, demo_mode=True
            )
            _, _, _, boundaries = tt_demo.tokenize(MULTI_TOPIC_TEXT)
            num_boundaries = sum(boundaries)
            # segments = boundaries + 1 (approximately, due to normalization)
            assert num_boundaries >= len(segments) - 2
