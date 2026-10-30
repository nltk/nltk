import tempfile
import unittest
from pathlib import Path

from nltk.parse.stanford import StanfordParser


class TestStanfordParserSecurity(unittest.TestCase):
    def setUp(self):
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
        when a token contains embedded newlines or carriage returns.
        """
        parser = StanfordParser(
            path_to_jar=str(self.fake_parser_jar),
            path_to_models_jar=str(self.fake_models_jar),
        )
        parser._execute = lambda cmd, input_data, verbose: "(ROOT (S (NN dummy)))\n\n"

        for malicious_char in ["\n", "\r"]:
            # Testing both \n and \r
            malicious_batch = [["ATTACKER", f"safe{malicious_char}INJECTED"]]
            # Also verify it works with generators
            malicious_gen = (sent for sent in malicious_batch)

            with self.assertRaises(ValueError):
                list(parser.parse_sents(malicious_gen))

    def test_raw_parse_sents_rejects_newlines(self):
        """
        Verify that raw_parse_sents also rejects newline/CR-bearing sentences.
        """
        parser = StanfordParser(
            path_to_jar=str(self.fake_parser_jar),
            path_to_models_jar=str(self.fake_models_jar),
        )
        parser._execute = lambda cmd, input_data, verbose: "(ROOT (S (NN dummy)))\n\n"

        for malicious_char in ["\n", "\r"]:
            malicious_sentences = [f"ATTACKER safe{malicious_char}INJECTED"]
            malicious_gen = (sent for sent in malicious_sentences)

            with self.assertRaises(ValueError):
                list(parser.raw_parse_sents(malicious_gen))

    def test_tagged_parse_sents_rejects_newlines(self):
        """
        Verify that tagged_parse_sents rejects newline/CR-bearing words or tags.
        """
        parser = StanfordParser(
            path_to_jar=str(self.fake_parser_jar),
            path_to_models_jar=str(self.fake_models_jar),
        )
        parser._execute = lambda cmd, input_data, verbose: "(ROOT (S (NN dummy)))\n\n"

        for malicious_char in ["\n", "\r"]:
            malicious_batch = [
                [("ATTACKER", "NN"), (f"safe{malicious_char}INJECTED", "NN")]
            ]
            malicious_gen = (sent for sent in malicious_batch)

            with self.assertRaises(ValueError):
                list(parser.tagged_parse_sents(malicious_gen))
