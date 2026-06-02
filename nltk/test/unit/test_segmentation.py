import pytest

from nltk.metrics.segmentation import windowdiff


def test_basic_functionality():
    # Identical Segmentations
    assert windowdiff("0001000", "0001000", 3) == 0.0
    assert windowdiff("111", "111", 2) == 0.0

    # Completely Different Segmentations
    assert windowdiff("000", "111", 2) == 1.0
    assert windowdiff("010101", "101010", 3) == 1.0


def test_boundary_marker_variations():
    # Different Boundary Markers
    assert windowdiff("aaaaba", "aaaaba", 3, boundary="b") == 0.0
    assert windowdiff("1110111", "1110111", 2, boundary="0") == 0.0


def test_weighted_vs_unweighted():
    # Weighted Calculation
    assert windowdiff("0001000", "0000100", 3, weighted=True) == 0.4
    assert windowdiff("1110111", "1111011", 2, weighted=True) == 0.3333333333333333

    # Unweighted Calculation
    assert windowdiff("0001000", "0000100", 3, weighted=False) == 0.4
    assert windowdiff("1110111", "1111011", 2, weighted=False) == 0.3333333333333333


def test_edge_cases():
    # Minimum Length Segmentations
    assert windowdiff("0", "0", 1) == 0.0
    assert windowdiff("1", "0", 1) == 1.0

    # Window Width Equal to Length
    assert windowdiff("000", "001", 3) == 1.0
    assert windowdiff("111", "110", 3) == 1.0


def test_error_handling():
    # Unequal Lengths
    with pytest.raises(ValueError, match="Segmentations have unequal length"):
        windowdiff("000", "0000", 2)
    with pytest.raises(ValueError, match="Segmentations have unequal length"):
        windowdiff("1111", "111", 3)

    # Window Width Greater than Length
    with pytest.raises(
        ValueError,
        match="Window width k should be smaller or equal than segmentation lengths",
    ):
        windowdiff("00", "00", 3)
    with pytest.raises(
        ValueError,
        match="Window width k should be smaller or equal than segmentation lengths",
    ):
        windowdiff("111", "111", 4)


def test_large_scale_cases():
    # Large Segmentations
    assert windowdiff("0" * 1000 + "1", "0" * 1000 + "1", 500) == 0.0
    assert windowdiff("01" * 500, "10" * 500, 100) == 0.0


def test_mixed_content_segmentations():
    # Mixed Content
    assert windowdiff("0101010101", "1010101010", 4) == 0.0
    assert windowdiff("1100110011", "0011001100", 3) == 1.0


def test_non_string_segmentations():
    # Lists as Segmentations
    assert windowdiff([0, 0, 1, 0, 0], [0, 0, 0, 1, 0], 3) == 0.0
    assert windowdiff([1, 1, 1, 0, 1], [1, 1, 0, 1, 1], 2) == 0.0


def test_boundary_marker_as_non_string():
    # Integer Boundary Markers
    assert windowdiff([0, 0, 1, 0], [0, 1, 0, 0], 2, boundary=1) == 0.6666666666666666
    assert windowdiff([1, 1, 0, 1], [1, 0, 1, 1], 3, boundary=0) == 0.0


def test_complex_patterns():
    # Complex Patterns
    assert windowdiff("001001001", "001001010", 3) == 0.14285714285714285
    assert windowdiff("111000111", "111111111", 4) == 1.0


def test_pevzner_hearst_examples():
    """Reference values from the windowdiff docstring (Pevzner & Hearst 2002)."""
    s1 = "000100000010"
    s2 = "000010000100"
    s3 = "100000010000"
    assert windowdiff(s1, s1, 3) == 0.0
    assert abs(windowdiff(s1, s2, 3) - 0.3) < 1e-6
    assert abs(windowdiff(s2, s3, 3) - 0.8) < 1e-6


def test_symmetry():
    """windowdiff(a, b, k) == windowdiff(b, a, k) for all inputs."""
    pairs = [
        ("000100000010", "000010000100", 3),
        ("100000010000", "000010000100", 3),
        ("010101", "101010", 3),
        ("0001000", "0000100", 3),
        ("1110111", "1111011", 2),
        ("001001001", "001001010", 3),
    ]
    for seg1, seg2, k in pairs:
        assert windowdiff(seg1, seg2, k) == windowdiff(seg2, seg1, k)
        assert windowdiff(seg1, seg2, k, weighted=True) == windowdiff(
            seg2, seg1, k, weighted=True
        )
