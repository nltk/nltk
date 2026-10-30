import unittest

from nltk.classify.weka import ARFF_Formatter


class TestARFFInjection(unittest.TestCase):
    def test_acyclic_labels(self):
        """Control: normal labels should produce a valid ARFF header."""
        featuresets = [
            ({"f": "benign"}, "legit"),
            ({"f": "payload"}, "malicious"),
        ]
        formatter = ARFF_Formatter.from_train(featuresets)
        arff = formatter.format(featuresets)

        # No injection should occur
        self.assertNotIn("@ATTRIBUTE injected", arff)
        self.assertNotIn("@DATA\n0,owned", arff)

        # Both labels should appear in the header
        self.assertIn("'legit'", arff)
        self.assertIn("'malicious'", arff)

        # Exactly two @ATTRIBUTE lines: one for 'f', one for '-label-'
        attr_lines = [
            line for line in arff.splitlines() if line.startswith("@ATTRIBUTE")
        ]
        self.assertEqual(len(attr_lines), 2)

    def test_self_referential_label_injection(self):
        """A self‑referential label (closing brace, newline, @ATTRIBUTE, @DATA, %) should be sanitised."""
        malicious = "safe}\n@ATTRIBUTE injected NUMERIC\n@DATA\n0,owned\n%"
        featuresets = [
            ({"f": "benign"}, "legit"),
            ({"f": "payload"}, malicious),
        ]
        formatter = ARFF_Formatter.from_train(featuresets)
        arff = formatter.format(featuresets)

        # Injected directives should be absent
        self.assertNotIn("@ATTRIBUTE injected NUMERIC", arff)
        self.assertNotIn("@DATA\n0,owned", arff)

        # The sanitized label should appear in the header (safe characters only)
        self.assertIn("'safe ATTRIBUTE injected NUMERIC DATA 0owned '", arff)
        self.assertIn("'legit'", arff)

        # Exactly two @ATTRIBUTE lines
        attr_lines = [
            line for line in arff.splitlines() if line.startswith("@ATTRIBUTE")
        ]
        self.assertEqual(len(attr_lines), 2)

    def test_mutual_referential_labels(self):
        """
        Multiple malicious labels that could cross‑reference should each be sanitised
        independently, and no extra @DATA or @ATTRIBUTE directives should be injected.
        """
        malicious1 = "classA}\n@ATTRIBUTE injected1 NUMERIC"
        malicious2 = "classB}\n@ATTRIBUTE injected2 NUMERIC"
        featuresets = [
            ({"f": "x"}, malicious1),
            ({"f": "y"}, malicious2),
        ]
        formatter = ARFF_Formatter.from_train(featuresets)
        arff = formatter.format(featuresets)

        # No injected directives should appear outside the sanitised labels
        self.assertNotIn("@ATTRIBUTE injected1", arff)
        self.assertNotIn("@ATTRIBUTE injected2", arff)

        # Sanitized versions should appear in the header
        self.assertIn("'classA ATTRIBUTE injected1 NUMERIC'", arff)
        self.assertIn("'classB ATTRIBUTE injected2 NUMERIC'", arff)

        # Exactly two @ATTRIBUTE lines: one for 'f', one for '-label-'
        attr_lines = [
            line for line in arff.splitlines() if line.startswith("@ATTRIBUTE")
        ]
        self.assertEqual(len(attr_lines), 2)

        # Exactly one @DATA section (the legitimate one)
        data_lines = [line for line in arff.splitlines() if line.startswith("@DATA")]
        self.assertEqual(len(data_lines), 1, "Should have exactly one @DATA section")


if __name__ == "__main__":
    unittest.main()
