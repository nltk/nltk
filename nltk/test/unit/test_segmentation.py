import multiprocessing
import os
import traceback

import pytest

from nltk.metrics.segmentation import pk, windowdiff


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


def test_negative_window_width_rejected():
    """A negative window width fails fast instead of raising IndexError mid-loop."""
    with pytest.raises(ValueError, match="Window width k should not be negative"):
        windowdiff("0000", "0000", -1)
    with pytest.raises(ValueError, match="Window width k should not be negative"):
        pk("0000", "0000", -1)


def test_pk_rejects_unequal_length():
    """pk rejects unequal-length inputs (like windowdiff) instead of IndexError."""
    with pytest.raises(ValueError, match="Segmentations have unequal length"):
        pk("000", "0000", 2)
    with pytest.raises(ValueError, match="Segmentations have unequal length"):
        pk("0000", "000", 2)


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


def test_pk_reference_values():
    """Reference values from the pk docstring (Beeferman's Pk)."""
    assert f"{pk('0100' * 100, '1' * 400, 2):.2f}" == "0.50"
    assert f"{pk('0100' * 100, '0' * 400, 2):.2f}" == "0.50"
    assert pk("0100" * 100, "0100" * 100, 2) == 0.0


def test_pk_basic_and_default_window():
    """pk on identical/disjoint inputs, and with the derived default window."""
    assert pk("0001000", "0001000", 3) == 0.0
    assert pk("000", "111", 2) == 1.0
    # k defaults to ~half the average reference segment length.
    assert pk("0100" * 100, "0100" * 100) == 0.0


def _windowdiff_worker(n):
    """Run windowdiff on a large half-window input; exit 0 ok, 3 on error."""
    try:
        seg = [0] * n
        windowdiff(seg, seg, n // 2, boundary=1)
        os._exit(0)
    except BaseException:
        traceback.print_exc()
        os._exit(3)


def _pk_worker(n):
    """Run pk on a large half-window input; exit 0 ok, 3 on error."""
    try:
        seg = [0] * n
        pk(seg, seg, n // 2, boundary=1)
        os._exit(0)
    except BaseException:
        traceback.print_exc()
        os._exit(3)


def _finishes_within(target, n, deadline=30):
    """Run target(n) in a spawned process; return (finished, exitcode)."""
    ctx = multiprocessing.get_context("spawn")
    proc = ctx.Process(target=target, args=(n,))
    proc.start()
    proc.join(deadline)
    if proc.is_alive():
        proc.terminate()
        proc.join()
        return False, None
    return True, proc.exitcode


def test_windowdiff_is_linear_not_quadratic():
    """A large half-window input must finish quickly (linear), not tie up a core.

    Run in a spawned process with a hard deadline: the incremental aligner
    returns in milliseconds, while the previous O(n*k) version needs over a
    minute at this size, so a regression is terminated instead of burning CPU.
    """
    finished, exitcode = _finishes_within(_windowdiff_worker, 200_000)
    assert finished, "windowdiff did not finish in time: quadratic blow-up regressed"
    assert exitcode == 0, f"windowdiff worker failed (exit {exitcode})"


def test_pk_is_linear_not_quadratic():
    """Same linearity guard for the pk metric (identical per-position loop)."""
    finished, exitcode = _finishes_within(_pk_worker, 200_000)
    assert finished, "pk did not finish in time: quadratic blow-up regressed"
    assert exitcode == 0, f"pk worker failed (exit {exitcode})"


def test_pk_boundary_free_reference_does_not_divide_by_zero():
    """A boundary-free reference must not crash pk's default-window derivation.

    With no window size and a reference that contains no boundary symbol,
    ``ref.count(boundary)`` is 0; pk previously raised an uncaught
    ``ZeroDivisionError`` (CWE-369). It now derives a window and computes a score.
    """
    # Identical boundary-free segmentations -> perfect agreement, no crash.
    assert pk("0" * 100, "0" * 100) == 0.0
    # A hyp that introduces a boundary still yields a valid score in [0, 1].
    score = pk("0" * 100, "0" * 50 + "1" + "0" * 49)
    assert 0.0 <= score <= 1.0


def test_pk_default_window_unchanged_for_segmented_reference():
    """The derived default window matches the historical formula when the
    reference has boundaries.

    Uses a case where the score is not trivially 0 (ref != hyp), so the
    assertion would fail if the default-``k`` derivation ever changed.
    """
    ref = "0100" * 100
    hyp = "1" * 400
    # Historical default: round(len(ref) / (ref.count(boundary) * 2)).
    k = int(round(len(ref) / (ref.count("1") * 2.0)))
    assert k == 2
    default_score = pk(ref, hyp)
    assert default_score != 0.0  # non-trivial case: a changed window would differ
    assert default_score == pk(ref, hyp, k)
