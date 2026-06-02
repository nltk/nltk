"""
Tests for nltk.pos_tag
"""

import io
import unittest
import unittest.mock

from nltk import pos_tag, word_tokenize
from nltk.help import brown_tagset, claws5_tagset, upenn_tagset

UPENN_TAGSET_DOLLAR_TEST = """$: dollar
    $ -$ --$ A$ C$ HK$ M$ NZ$ S$ U.S.$ US$
PRP$: pronoun, possessive
    her his mine my our ours their thy your
WP$: WH-pronoun, possessive
    whose
"""

BROWN_TAGSET_NNS_TEST = """NNS: noun, plural, common
    irregularities presentments thanks reports voters laws legislators
    years areas adjustments chambers $100 bonds courts sales details raises
    sessions members congressmen votes polls calls ...
"""

CLAW5_TAGSET_VHD_TEST = """VHD: past tense form of the verb "HAVE"
    had, 'd
"""


class TestPosTag(unittest.TestCase):
    def test_pos_tag_eng(self):
        text = "John's big idea isn't all that bad."
        expected_tagged = [
            ("John", "NNP"),
            ("'s", "POS"),
            ("big", "JJ"),
            ("idea", "NN"),
            ("is", "VBZ"),
            ("n't", "RB"),
            ("all", "PDT"),
            ("that", "DT"),
            ("bad", "JJ"),
            (".", "."),
        ]
        assert pos_tag(word_tokenize(text)) == expected_tagged

    def test_pos_tag_eng_universal(self):
        text = "John's big idea isn't all that bad."
        expected_tagged = [
            ("John", "NOUN"),
            ("'s", "PRT"),
            ("big", "ADJ"),
            ("idea", "NOUN"),
            ("is", "VERB"),
            ("n't", "ADV"),
            ("all", "DET"),
            ("that", "DET"),
            ("bad", "ADJ"),
            (".", "."),
        ]
        assert pos_tag(word_tokenize(text), tagset="universal") == expected_tagged

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def check_stdout(self, tagset, query_regex, expected_output, mock_stdout):
        tagset(query_regex)
        self.assertEqual(mock_stdout.getvalue(), expected_output)

    def test_tagsets_upenn(self):
        self.check_stdout(upenn_tagset, r".*\$", UPENN_TAGSET_DOLLAR_TEST)

    def test_tagsets_brown(self):
        self.check_stdout(brown_tagset, r"NNS", BROWN_TAGSET_NNS_TEST)

    def test_tagsets_claw5(self):
        self.check_stdout(claws5_tagset, r"VHD", CLAW5_TAGSET_VHD_TEST)

    def test_pos_tag_rus(self):
        text = "Илья оторопел и дважды перечитал бумажку."
        expected_tagged = [
            ("Илья", "S"),
            ("оторопел", "V"),
            ("и", "CONJ"),
            ("дважды", "ADV"),
            ("перечитал", "V"),
            ("бумажку", "S"),
            (".", "NONLEX"),
        ]
        assert pos_tag(word_tokenize(text), lang="rus") == expected_tagged

    def test_pos_tag_rus_universal(self):
        text = "Илья оторопел и дважды перечитал бумажку."
        expected_tagged = [
            ("Илья", "NOUN"),
            ("оторопел", "VERB"),
            ("и", "CONJ"),
            ("дважды", "ADV"),
            ("перечитал", "VERB"),
            ("бумажку", "NOUN"),
            (".", "."),
        ]
        assert (
            pos_tag(word_tokenize(text), tagset="universal", lang="rus")
            == expected_tagged
        )

    def test_pos_tag_rus_universal_mapping_does_not_require_ru_rnc_new_map_file(self):
        """
        Regression test for #2434: some environments crash when requesting universal
        tags for Russian due to an attempted lookup of ru-rnc-new.map, which is not
        shipped in the universal_tagset data package. Ensure the code works even
        when that mapping file is missing, and ensure the mapping cache is
        not pre-initialized by previous tests.
        """
        from collections import defaultdict

        import nltk.tag.mapping as mapping
        from nltk.data import normalize_resource_url

        text = "Илья оторопел и дважды перечитал бумажку."
        expected_tagged = [
            ("Илья", "NOUN"),
            ("оторопел", "VERB"),
            ("и", "CONJ"),
            ("дважды", "ADV"),
            ("перечитал", "VERB"),
            ("бумажку", "NOUN"),
            (".", "."),
        ]

        # Save & replace the global mapping cache so earlier tests cannot mask this.
        saved_mappings = mapping._MAPPINGS
        try:
            mapping._MAPPINGS = defaultdict(
                lambda: defaultdict(lambda: defaultdict(lambda: "UNK"))
            )

            # In current published nltk_data, ru-rnc-new.map is not shipped.
            # (We intentionally don't assert on the error message text here.)
            with self.assertRaises(LookupError):
                mapping.load(
                    normalize_resource_url(
                        "nltk:taggers/universal_tagset/ru-rnc-new.map"
                    ),
                    format="text",
                )

            assert (
                pos_tag(word_tokenize(text), tagset="universal", lang="rus")
                == expected_tagged
            )
        finally:
            mapping._MAPPINGS = saved_mappings

    def test_pos_tag_unknown_lang(self):
        text = "모르겠 습니 다"
        self.assertRaises(NotImplementedError, pos_tag, word_tokenize(text), lang="kor")
        # Test for default kwarg, `lang=None`
        self.assertRaises(NotImplementedError, pos_tag, word_tokenize(text), lang=None)

    def test_unspecified_lang(self):
        # Tries to force the lang='eng' option.
        text = "모르겠 습니 다"
        expected_but_wrong = [("모르겠", "JJ"), ("습니", "NNP"), ("다", "NN")]
        assert pos_tag(word_tokenize(text)) == expected_but_wrong
