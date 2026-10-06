import unittest

from nltk.corpus import ieer


class TestIEER(unittest.TestCase):
    def test_parsed_docs(self):
        docs = ieer.parsed_docs("APW_19980314")
        self.assertEqual(len(docs), 23)
        self.assertEqual(docs[0].docno, "APW19980314.0391")

    def test_docs_does_not_contain_empty_strings(self):
        docs = list(ieer.docs())
        # The corpus has 94 valid documents in total
        self.assertEqual(len(docs), 94)
        # Ensure there are no trailing empty documents/strings resulting from EOF misbehavior
        self.assertTrue(all(bool(doc.strip()) for doc in docs))
