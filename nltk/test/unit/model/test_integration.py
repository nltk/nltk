# Natural Language Toolkit: Language Model Unit Tests
#
# Copyright (C) 2001-2016 NLTK Project
# Author: Ilia Kurenkov <ilia.kurenkov@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT
import unittest

from nltk.model import build_vocabulary, count_ngrams
from nltk.model.util import mask_oov_words_in_corpus

@unittest.skip("Pending overhaul of the interfaces.")
class ModelFuncsTests(unittest.TestCase):
    """Tests for module functions.

    They are essentially integration tests.
    """

    def test_build_vocabulary(self):
        vocab = build_vocabulary(2, 'zabcfdegadbew')
        assert "a" in vocab
        assert "c" not in vocab

    def test_build_vocabulary_multiple_texts(self):
        vocab = build_vocabulary(2, 'zabcfdegadbew', "abcdeadbe")
        assert "a" in vocab
        assert "c" in vocab
        assert "g" not in vocab

    def test_build_vocabulary_no_texts(self):
        vocab = build_vocabulary(2)
        assert "a" not in vocab
        assert "z" not in vocab

    def test_count_ngrams(self):
        vocab = build_vocabulary(2, 'abcdead')
        normalized = mask_oov_words_in_corpus(['abcfdezgadbew'], vocab)
        counter = count_ngrams(2, vocab, normalized)

        bigrams = counter.ngrams[2]

        self.assertEqual(bigrams[("a",)]['b'], 0)
        self.assertEqual(bigrams[("a",)]['d'], 1)
        self.assertEqual(bigrams[("<s>",)]['a'], 1)

    def test_count_ngrams_multiple_texts(self):
        vocab_text = ("the cow jumped over the blue moon . "
                      "blue river jumped over the rainbow .")
        vocab = build_vocabulary(2, vocab_text.split())

        text1 = mask_oov_words_in_corpus(['zabcfdegadbew'], vocab)
        text2 = mask_oov_words_in_corpus(["blue moon".split(),
                                          "over the rainbow".split()], vocab)
        counter = count_ngrams(2, vocab, text1, text2)

        bigrams = counter.ngrams[2]

        self.assertEqual(bigrams[("blue",)]['river'], 0)
        self.assertEqual(bigrams[("blue",)]['<UNK>'], 1)
        self.assertEqual(bigrams[("over",)]['the'], 1)

    def test_count_ngrams_kwargs(self):
        vocab_text = ("the cow jumped over the blue moon . "
                      "blue river jumped over the rainbow .")
        vocab = build_vocabulary(2, vocab_text.split())

        text = ["blue moon".split(), "over the rainbow".split()]
        counter = count_ngrams(2, vocab, text, left_pad_symbol="TEST")

        self.assertEqual(counter.ngrams[2][("TEST",)]["blue"], 1)

    def test_count_grams_bad_kwarg(self):
        vocab_text = ("the cow jumped over the blue moon . "
                      "blue river jumped over the rainbow .")
        vocab = build_vocabulary(2, vocab_text.split())

        text = ["blue moon".split()]
        with self.assertRaises(TypeError) as exc_info:
            count_ngrams(2, vocab, text, dummy_kwarg="TEST")

        expected_error_msg = "ngrams() got an unexpected keyword argument 'dummy_kwarg'"
        self.assertEqual(expected_error_msg, str(exc_info.exception))
