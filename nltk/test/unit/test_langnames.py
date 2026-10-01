import unittest
import warnings

from nltk.langnames import lang2q, langcode, langname, q2name, q2tag, tag2q


class TestTag2Q(unittest.TestCase):
    def test_known_tag(self):
        self.assertEqual(tag2q("nds-u-sd-demv"), "Q4289225")

    def test_unknown_tag(self):
        self.assertIsNone(tag2q("zzzz-unknown-tag"))

    def test_empty_string(self):
        self.assertIsNone(tag2q(""))

    def test_unknown_tag_strict(self):
        with self.assertRaises(LookupError):
            tag2q("zzzz-unknown-tag", strict=True)

    def test_known_tag_strict(self):
        self.assertEqual(tag2q("nds-u-sd-demv", strict=True), "Q4289225")


class TestQ2Tag(unittest.TestCase):
    def test_known_qcode(self):
        self.assertEqual(q2tag("Q4289225"), "nds-u-sd-demv")

    def test_unknown_qcode(self):
        self.assertIsNone(q2tag("Q0000000"))

    def test_empty_string(self):
        self.assertIsNone(q2tag(""))

    def test_unknown_qcode_strict(self):
        with self.assertRaises(LookupError):
            q2tag("Q0000000", strict=True)

    def test_known_qcode_strict(self):
        self.assertEqual(q2tag("Q4289225", strict=True), "nds-u-sd-demv")


class TestQ2Name(unittest.TestCase):
    def test_known_full(self):
        self.assertEqual(q2name("Q4289225"), "Low German: Mecklenburg-Vorpommern")

    def test_known_short(self):
        self.assertEqual(q2name("Q4289225", "short"), "Low German")

    def test_unknown_qcode(self):
        self.assertIsNone(q2name("Q0000000"))

    def test_empty_string(self):
        self.assertIsNone(q2name(""))

    def test_unknown_qcode_strict(self):
        with self.assertRaises(LookupError):
            q2name("Q0000000", strict=True)

    def test_known_qcode_strict(self):
        self.assertEqual(
            q2name("Q4289225", strict=True), "Low German: Mecklenburg-Vorpommern"
        )


class TestLang2Q(unittest.TestCase):
    def test_known_language(self):
        self.assertEqual(lang2q("Low German"), "Q25433")

    def test_unknown_language(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.assertIsNone(lang2q("NonexistentLanguage"))

    def test_empty_string(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.assertIsNone(lang2q(""))

    def test_unknown_language_strict(self):
        with self.assertRaises(LookupError):
            lang2q("NonexistentLanguage", strict=True)

    def test_known_language_strict(self):
        self.assertEqual(lang2q("Low German", strict=True), "Q25433")


class TestLangName(unittest.TestCase):
    def test_known_tag(self):
        self.assertEqual(
            langname("ca-Latn-ES-valencia"), "Catalan: Latin: Spain: Valencian"
        )

    def test_known_tag_short(self):
        self.assertEqual(langname("ca-Latn-ES-valencia", typ="short"), "Catalan")

    def test_retired_code(self):
        self.assertEqual(langname("fri"), "Western Frisian")

    def test_unknown_code(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.assertIsNone(langname("zzz"))

    def test_none_input(self):
        self.assertIsNone(langname(None))

    def test_unknown_code_strict(self):
        with self.assertRaises(LookupError):
            langname("zzz", strict=True)

    def test_none_input_strict(self):
        with self.assertRaises(LookupError):
            langname(None, strict=True)

    def test_known_tag_strict(self):
        self.assertEqual(
            langname("ca-Latn-ES-valencia", strict=True),
            "Catalan: Latin: Spain: Valencian",
        )


class TestLangCode(unittest.TestCase):
    def test_known_name(self):
        self.assertEqual(langcode("Modern Greek (1453-)"), "el")

    def test_known_name_3letter(self):
        self.assertEqual(langcode("Modern Greek (1453-)", typ=3), "ell")

    def test_retired_name(self):
        self.assertEqual(langcode("Western Frisian"), "fy")

    def test_unknown_name(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.assertIsNone(langcode("NotARealLanguage"))

    def test_unknown_name_strict(self):
        with self.assertRaises(LookupError):
            langcode("NotARealLanguage", strict=True)

    def test_known_name_strict(self):
        self.assertEqual(langcode("Modern Greek (1453-)", strict=True), "el")


if __name__ == "__main__":
    unittest.main()
