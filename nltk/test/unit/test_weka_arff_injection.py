import unittest

from nltk.classify.weka import ARFF_Formatter


class TestARFFInjection(unittest.TestCase):
    def test_label_injection_prevented(self):
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

        # Sanitized label should appear in the header (safe characters only)
        self.assertIn("'safe", arff)  # label starts with 'safe' (the '}' is removed)
        self.assertIn("'legit'", arff)  # legitimate label remains intact

        # There should be exactly two @ATTRIBUTE lines: one for 'f' and one for '-label-'
        attr_lines = [
            line for line in arff.splitlines() if line.startswith("@ATTRIBUTE")
        ]
        self.assertEqual(len(attr_lines), 2)


if __name__ == "__main__":
    unittest.main()
