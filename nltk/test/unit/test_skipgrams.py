import unittest

from nltk.util import skipgrams


class TestSkipgrams(unittest.TestCase):
    """Unit tests for nltk.util.skipgrams, including CVE-2026-14595 mitigation."""

    def test_skipgrams_basic(self):
        """Test standard skipgram generation with benign inputs."""
        tokens = ["Insurgents", "killed", "in", "ongoing", "fighting"]
        result = list(skipgrams(tokens, 2, 2))
        expected = [
            ("Insurgents", "killed"),
            ("Insurgents", "in"),
            ("Insurgents", "ongoing"),
            ("killed", "in"),
            ("killed", "ongoing"),
            ("killed", "fighting"),
            ("in", "ongoing"),
            ("in", "fighting"),
            ("ongoing", "fighting"),
        ]
        self.assertEqual(result, expected)

    def test_skipgrams_combinatorial_dos_mitigation(self):
        """Verify that explosive (n, k) parameters raise ValueError (CVE-2026-14595)."""
        tokens = [f"t{i}" for i in range(60)]

        # n=7, k=30 yields math.comb(36, 6) = 1,947,792 combinations per window (> 1,000,000 limit)
        gen = skipgrams(tokens, n=7, k=30)

        with self.assertRaises(ValueError) as ctx:
            # Use next() instead of list().
            # If the fix is missing, this yields the first item instantly and fails the test.
            # If the fix is present, it instantly raises our ValueError.
            # This prevents the CI pipeline from hanging if a regression occurs!
            next(gen)

        self.assertIn("exceed the maximum allowed combinations", str(ctx.exception))
