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

from __future__ import print_function, absolute_import, division

import random
import yaml
import time

from nltk import tag
from nltk.corpus import treebank

from nltk.tag.brill.erroranalysis import error_list
from nltk.tag.brill.trainer.fast import TaggerTrainer


def postag(templates,
           tagged_data=None,
           num_sents=1000,
           num_words=None,
           max_rules=5000,
           min_score=3,
           error_output="errors.out",
           rule_output="rules.yaml",
           randomize=False,
           train=.8,
           trace=3,
           ruleformat="verbose"):
    """
    Brill Tagger Demonstration

    @param num_sents: how many sentences of training and testing data to use
    @type num_sents: L{int}
    @param max_rules: maximum number of rule instances to create
    @type max_rules: L{int}
    @param min_score: the minimum score for a rule in order for it to
        be considered
    @type min_score: L{int}
    @param error_output: the file where errors will be saved
    @type error_output: C{string}
    @param rule_output: the file where rules will be saved
    @type rule_output: C{string}
    @param randomize: whether the training data should be a random subset
        of the corpus
    @type randomize: boolean
    @param train: the fraction of the the corpus to be used for training
        (1=all)
    @type train: L{float}
    @param trace: the level of diagnostic tracing output to produce (0-4)
    @type trace: L{int}
    """

    nn_cd_tagger = tag.RegexpTagger([(r'^-?[0-9]+(.[0-9]+)?$', 'CD'),
                                     (r'.*', 'NN')])

    regexp_tagger = tag.RegexpTagger(
        [(r'^-?[0-9]+(.[0-9]+)?$', 'CD'),   # cardinal numbers
         (r'(The|the|A|a|An|an)$', 'AT'),   # articles
         (r'.*able$', 'JJ'),                # adjectives
         (r'.*ness$', 'NN'),                # nouns formed from adjectives
         (r'.*ly$', 'RB'),                  # adverbs
         (r'.*s$', 'NNS'),                  # plural nouns
         (r'.*ing$', 'VBG'),                # gerunds
         (r'.*ed$', 'VBD'),                 # past tense verbs
         (r'.*', 'NN')                      # nouns (default)
    ])


    # train is the proportion of data used in training; the rest is reserved
    # for testing.
    if tagged_data is None:
        print("Loading tagged data from treebank... ")
        tagged_data = treebank.tagged_sents()
    if num_sents is None or len(tagged_data) <= num_sents:
        num_sents = len(tagged_data)
    if randomize:
        random.seed(len(tagged_data))
        random.shuffle(tagged_data)
    cutoff = int(num_sents * train)
    #unitrain = cutoff // 4
    #unitrain_data = tagged_data[:unitrain]
    training_data = tagged_data[:cutoff]
    unitrain_data = training_data
    gold_data = tagged_data[cutoff:num_sents]
    testing_data = [[t[0] for t in sent] for sent in gold_data]

    print("Read data (train %d sentences/%d words; test %d sentences/%d words)." % (
        len(training_data), sum(len(t) for t in training_data), len(testing_data), sum(len(t) for t in testing_data)))

    # Unigram tagger
    print("Training unigram tagger_1 (no backoff):")
    unigram_tagger1 = tag.UnigramTagger(unitrain_data)
    if gold_data:
        print("    [accuracy: %f]" % unigram_tagger1.evaluate(gold_data))

    print("Training unigram tagger_2 (backoff=nn_cd):")
    unigram_tagger2 = tag.UnigramTagger(unitrain_data,
                                       backoff=nn_cd_tagger)
    if gold_data:
        print("    [accuracy: %f]" % unigram_tagger2.evaluate(gold_data))

    print("Training unigram tagger_3 (backoff=regexp):")
    unigram_tagger3 = tag.UnigramTagger(unitrain_data,
                                       backoff=regexp_tagger)
    if gold_data:
        print("    [accuracy: %f]" % unigram_tagger3.evaluate(gold_data))

    unigram_tagger = unigram_tagger3

    # Bigram tagger
    print("Training bigram tagger:")
    bigram_tagger = tag.BigramTagger(unitrain_data,
                                     backoff=unigram_tagger)
    if gold_data:
        print("    [accuracy: %f]" % bigram_tagger.evaluate(gold_data))

    # Brill tagger
    t0 = time.time()
    trainer = TaggerTrainer(unigram_tagger, templates, trace, ruleformat=ruleformat)
    brill_tagger = trainer.train(training_data, max_rules, min_score)
    thattook = time.time() - t0
    print("finished training in %f seconds" % thattook)

    if gold_data:
        print("\nBrill test accuracy: %f" % brill_tagger.evaluate(gold_data))
    #if gold_data:
    #    print("\nBrill training accuracy: %f" % brill_tagger.evaluate(training_data))

    if trace <= 1:
        print("\nRules: ")
        for rule in brill_tagger.rules():
            print(str(rule))

    print_rules = open(rule_output, 'w')
    yaml.dump(brill_tagger, print_rules)
    print_rules.close()

    del brill_tagger
    print_rules = open(rule_output, "r")
    brill_tagger = yaml.load(print_rules)
    print_rules.close()

    #template statistics
    #brill_tagger.print_template_statistics()


    #testing_data2 = [[t[0] for t in sent] for sent in training_data]
    #(testing_data, ruleerrs) = brill_tagger.batch_tag_incremental(testing_data, gold_data)
    testing_data = brill_tagger.batch_tag(testing_data)
    #tokenscount = sum(len(tokens) for tokens in testing_data)
    #(_junk, ruleerrs2) = brill_tagger.batch_tag_incremental(testing_data2, training_data)
    #tokenscount2 = sum(len(tokens) for tokens in training_data)
    #r = list(range(len(ruleerrs)))
    #import matplotlib.pyplot as plt
    #plt.plot(r, [1-x/float(tokenscount) for x in ruleerrs], r, [1-y/float(tokenscount2) for y in ruleerrs2])
    #plt.axis([None, None, None, 1.0])
    #plt.savefig("learningcurve.png")
    error_file = file(error_output, 'w')
    error_file.write('Errors for Brill Tagger %r\n\n' % rule_output)
    for e in error_list(gold_data, testing_data):
        error_file.write(e+'\n')
    error_file.close()
    print ("Done; rules and errors saved to %s and %s." %
           (rule_output, error_output))


def demo():
    postag()
