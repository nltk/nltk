import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import nltk.data
from nltk.corpus.reader.mte import MTECorpusReader


class TestMTETokenStateIsolation(unittest.TestCase):
    def test_lazy_tag_filter_isolation(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <TEI xmlns="https://www.tei-c.org/ns/1.0">
          <text><body><div><div><p><s>
            <w ana="Ncmsn" lemma="secret">NOUN_SECRET</w>
            <w ana="Vmip3s" lemma="public">VERB_PUBLIC</w>
          </s></p></div></div></body></text>
        </TEI>
        """
        with TemporaryDirectory() as d:
            root = Path(d)
            (root / "sample.xml").write_text(xml, encoding="utf-8")

            # Temporarily authorize this directory in NLTK's sandbox
            nltk.data.path.append(str(root))

            try:
                reader = MTECorpusReader(str(root), ["sample.xml"])
                nouns_baseline = [("NOUN_SECRET", "Ncmsn")]
                verbs_baseline = [("VERB_PUBLIC", "Vmip3s")]

                # Create lazy view for nouns
                victim_view = reader.tagged_words(tags="N")

                # Interleave request overriding the filter state
                attacker_view = reader.tagged_words(tags="V")

                # Consume views
                victim_result = list(victim_view)
                attacker_result = list(attacker_view)

                self.assertEqual(
                    victim_result, nouns_baseline, "Shared state corruption detected!"
                )
                self.assertEqual(attacker_result, verbs_baseline)
            finally:
                # Clean up global state regardless of test outcome
                if str(root) in nltk.data.path:
                    nltk.data.path.remove(str(root))


if __name__ == "__main__":
    unittest.main()
