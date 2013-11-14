# -*- coding: utf-8 -*-


# Natural Language Toolkit: Brill Tagger
#
# Copyright (C) 2001-2013 NLTK Project
# Authors: Christopher Maloof <cjmaloof@gradient.cis.upenn.edu>
#          Edward Loper <edloper@gmail.com>
#          Steven Bird <stevenbird1@gmail.com>
#          Marcus Uneson <marcus.uneson@gmail.com>
# URL: <http://nltk.org/>
# For license information, see  LICENSE.TXT
from __future__ import print_function

import random
import yaml

from nltk.tag.brill.trainer.fast import FastBrillTaggerTrainer
from nltk.tag.brill.nltk2.postagging import ProximateTagsRule, ProximateWordsRule
from nltk.tag.brill.nltk2.template import ProximateTokensTemplate
from nltk.tag.brill.erroranalysis import error_list

######################################################################
# Demonstration
######################################################################

def demo(num_sents=2000, max_rules=200, min_score=3,
         error_output="errors.out", rule_output="rules.yaml",
         randomize=False, train=.8, trace=3):
    """
    Brill Tagger Demonstration

    :param num_sents: how many sentences of training and testing data to use
    :type num_sents: int
    :param max_rules: maximum number of rule instances to create
    :type max_rules: int
    :param min_score: the minimum score for a rule in order for it to
        be considered
    :type min_score: int
    :param error_output: the file where errors will be saved
    :type error_output: str
    :param rule_output: the file where rules will be saved
    :type rule_output: str
    :param randomize: whether the training data should be a random subset
        of the corpus
    :type randomize: bool
    :param train: the fraction of the the corpus to be used for training
        (1=all)
    :type train: float
    :param trace: the level of diagnostic tracing output to produce (0-4)
    :type trace: int
    """

    from nltk.corpus import treebank
    from nltk import tag
    from nltk.tag import brill

    nn_cd_tagger = tag.RegexpTagger([(r'^-?[0-9]+(.[0-9]+)?$', 'CD'),
                                     (r'.*', 'NN')])

    # train is the proportion of data used in training; the rest is reserved
    # for testing.
    print("Loading tagged data... ")
    tagged_data = treebank.tagged_sents()
    num_sents = min(num_sents, len(tagged_data))
    if randomize:
        random.seed(len(tagged_data))
        random.shuffle(tagged_data)
    cutoff = int(num_sents*train)
    training_data = tagged_data[:cutoff]
    gold_data = tagged_data[cutoff:num_sents]
    testing_data = [[t[0] for t in sent] for sent in gold_data]
    print("Done loading.")

    # Unigram tagger
    print("Training unigram tagger:")
    unigram_tagger = tag.UnigramTagger(training_data,
                                       backoff=nn_cd_tagger)
    if gold_data:
        print("    [accuracy: %f]" % unigram_tagger.evaluate(gold_data))

    # Bigram tagger
    print("Training bigram tagger:")
    bigram_tagger = tag.BigramTagger(training_data,
                                     backoff=unigram_tagger)
    if gold_data:
        print("    [accuracy: %f]" % bigram_tagger.evaluate(gold_data))

    # Brill tagger
    templates = [
      brill.SymmetricProximateTokensTemplate(ProximateTagsRule, (1,1)),
      brill.SymmetricProximateTokensTemplate(ProximateTagsRule, (2,2)),
      brill.SymmetricProximateTokensTemplate(ProximateTagsRule, (1,2)),
      brill.SymmetricProximateTokensTemplate(ProximateTagsRule, (1,3)),
      brill.SymmetricProximateTokensTemplate(ProximateWordsRule, (1,1)),
      brill.SymmetricProximateTokensTemplate(ProximateWordsRule, (2,2)),
      brill.SymmetricProximateTokensTemplate(ProximateWordsRule, (1,2)),
      brill.SymmetricProximateTokensTemplate(ProximateWordsRule, (1,3)),
      ProximateTokensTemplate(ProximateTagsRule, (-1, -1), (1,1)),
      ProximateTokensTemplate(ProximateWordsRule, (-1, -1), (1,1)),
      ]
    trainer = FastBrillTaggerTrainer(bigram_tagger, templates, trace)
    #trainer = brill.BrillTaggerTrainer(u, templates, trace)
    brill_tagger = trainer.train(training_data, max_rules, min_score)

    if gold_data:
        print(("\nBrill accuracy: %f" % brill_tagger.evaluate(gold_data)))

    if trace <= 1:
        print("\nRules: ")
        for rule in brill_tagger.rules():
            print(rule)

    print_rules = file(rule_output, 'w')
    yaml.dump(brill_tagger, print_rules)
    print_rules.close()

    testing_data = brill_tagger.batch_tag(testing_data)
    error_file = file(error_output, 'w')
    error_file.write('Errors for Brill Tagger %r\n\n' % rule_output)
    for e in error_list(gold_data, testing_data):
        error_file.write(e+'\n')
    error_file.close()
    print(("Done; rules and errors saved to %s and %s." %
           (rule_output, error_output)))
