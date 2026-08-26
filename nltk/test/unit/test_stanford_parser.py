import tempfile
import unittest
from pathlib import Path

from nltk.parse.stanford import StanfordParser


class TestStanfordParserSecurity(unittest.TestCase):
    def setUp(self):
        # Create temporary dummy files so os.path.isfile() passes during initialization
        self.tmp_dir = tempfile.TemporaryDirectory()
        tmp_path = Path(self.tmp_dir.name)

        self.fake_parser_jar = tmp_path / "stanford-parser.jar"
        self.fake_models_jar = tmp_path / "stanford-parser-models.jar"

        self.fake_parser_jar.write_text("dummy jar", encoding="utf-8")
        self.fake_models_jar.write_text("dummy jar", encoding="utf-8")

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_parse_sents_rejects_newlines_in_tokens(self):
        """
        Verify that StanfordParser.parse_sents() raises a ValueError
        when a token contains embedded newlines, preventing batch-boundary injection.
        """
        parser = StanfordParser(
            path_to_jar=str(self.fake_parser_jar),
            path_to_models_jar=str(self.fake_models_jar),
        )

        # Mock execution to avoid requiring an external Java / Stanford installation
        parser._execute = lambda cmd, input_data, verbose: "(ROOT (S (NN dummy)))\n\n"

        # Malicious input: token containing an embedded newline
        malicious_batch = [["ATTACKER", "safe\nINJECTED"]]

        with self.assertRaises(ValueError):
            list(parser.parse_sents(malicious_batch))

    def test_raw_parse_sents_rejects_newlines(self):
        """
        Verify that raw_parse_sents also rejects newline-bearing sentences.
        """
        parser = StanfordParser(
            path_to_jar=str(self.fake_parser_jar),
            path_to_models_jar=str(self.fake_models_jar),
        )
        parser._execute = lambda cmd, input_data, verbose: "(ROOT (S (NN dummy)))\n\n"

        malicious_sentences = ["ATTACKER safe\nINJECTED"]

        with self.assertRaises(ValueError):
            list(parser.raw_parse_sents(malicious_sentences))
