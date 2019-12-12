# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals

import unittest

from nltk.corpus import rte as rte_corpus
from nltk.classify.rte_classify import RTEFeatureExtractor, rte_features, rte_classifier

expected_from_rte_feature_extration = """
alwayson        => True
ne_hyp_extra    => 0
ne_overlap      => 1
neg_hyp         => 0
neg_txt         => 0
word_hyp_extra  => 3
word_overlap    => 3

alwayson        => True
ne_hyp_extra    => 0
ne_overlap      => 1
neg_hyp         => 0
neg_txt         => 0
word_hyp_extra  => 2
word_overlap    => 1

alwayson        => True
ne_hyp_extra    => 1
ne_overlap      => 1
neg_hyp         => 0
neg_txt         => 0
word_hyp_extra  => 1
word_overlap    => 2

alwayson        => True
ne_hyp_extra    => 1
ne_overlap      => 0
neg_hyp         => 0
neg_txt         => 0
word_hyp_extra  => 6
word_overlap    => 2

alwayson        => True
ne_hyp_extra    => 1
ne_overlap      => 0
neg_hyp         => 0
neg_txt         => 0
word_hyp_extra  => 4
word_overlap    => 0

alwayson        => True
ne_hyp_extra    => 1
ne_overlap      => 0
neg_hyp         => 0
neg_txt         => 0
word_hyp_extra  => 3
word_overlap    => 1
"""


class RTEClassifierTest(unittest.TestCase):
    # Test the feature extraction method.
    def test_rte_feature_extraction(self):
        pairs = rte_corpus.pairs(['rte1_dev.xml'])[:6]
        test_output = [
            "%-15s => %s" % (key, rte_features(pair)[key])
            for pair in pairs
            for key in sorted(rte_features(pair))
        ]
        expected_output = expected_from_rte_feature_extration.strip().split('\n')
        # Remove null strings.
        expected_output = list(filter(None, expected_output))
        self.assertEqual(test_output, expected_output)

    # Test the RTEFeatureExtractor object.
    def test_feature_extractor_object(self):
        rtepair = rte_corpus.pairs(['rte3_dev.xml'])[33]
        extractor = RTEFeatureExtractor(rtepair)
        self.assertEqual(extractor.hyp_words, {'member', 'China', 'SCO.'})
        self.assertEqual(extractor.overlap('word'), set())
        self.assertEqual(extractor.overlap('ne'), {'China'})
        self.assertEqual(extractor.hyp_extra('word'), {'member'})

    # Test the RTE classifier training.
    def test_rte_classification_without_megam(self):
        clf = rte_classifier('IIS')
        clf = rte_classifier('GIS')

    @unittest.skip("Skipping tests with dependencies on MEGAM")
    def test_rte_classification_with_megam(self):
        nltk.config_megam('/usr/local/bin/megam')
        clf = rte_classifier('megam')
        clf = rte_classifier('BFGS')
