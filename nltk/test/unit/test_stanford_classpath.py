import os
import unittest
from unittest.mock import patch

from nltk.parse.stanford import GenericStanfordParser


class TestStanfordClasspathOrder(unittest.TestCase):
    """Unit tests to verify classpath construction order in GenericStanfordParser (CVE-2026-14582)."""

    @patch("nltk.parse.stanford.find_jar_iter")
    @patch("nltk.parse.stanford.find_jars_within_path")
    def test_model_jar_appended_at_end(self, mock_find_jars, mock_find_jar_iter):
        # find_jar_iter returns an iterable (generator/list) of paths.
        # We must return a LIST for each call, otherwise max() iterates over the string's characters!
        mock_find_jar_iter.side_effect = [
            ["/opt/stanford/stanford-parser.jar"],  # 1st call: stanford_jar
            ["/untrusted/stanford-parser-4.2.0-models.jar"],  # 2nd call: model_jar
        ]

        # Mock additional supporting jars found in the stanford directory
        mock_find_jars.return_value = [
            "/opt/stanford/stanford-parser.jar",
            "/opt/stanford/slf4j-api.jar",
        ]

        # Initialize the parser
        parser = GenericStanfordParser(
            path_to_jar="/opt/stanford/stanford-parser.jar",
            path_to_models_jar="/untrusted/stanford-parser-4.2.0-models.jar",
        )

        # Verify classpath elements
        classpath = parser._classpath

        # The model jar must NOT be the first element (which would allow class shadowing)
        self.assertNotEqual(
            classpath[0],
            "/untrusted/stanford-parser-4.2.0-models.jar",
            "Vulnerability present: untrusted model_jar is prepended to the classpath.",
        )

        # The model jar MUST be at the very end of the classpath tuple
        self.assertEqual(
            classpath[-1],
            "/untrusted/stanford-parser-4.2.0-models.jar",
            "Expected model_jar to be appended at the end of the classpath.",
        )

        # Trusted jar/supporting paths should appear before the model jar
        self.assertIn("/opt/stanford/stanford-parser.jar", classpath[:-1])
