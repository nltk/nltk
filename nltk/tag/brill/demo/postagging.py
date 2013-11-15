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
import sys

from nltk import tag
from nltk.corpus import treebank

from nltk.tag.brill.erroranalysis import error_list
from nltk.tag.brill.trainer.fast import TaggerTrainer
from nltk.tag.brill.demo import postagging_templates
from nltk.tag.brill.template import Template
from nltk.tag.brill.application.postagging import Word, Tag

def corpus_size(seqs):
    return (len(seqs), sum(len(x) for x in seqs))

def _demo_prepare_data(tagged_data, train, num_sents, randomize):
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
    training_data = tagged_data[:cutoff]
    gold_data = tagged_data[cutoff:num_sents]
    testing_data = [[t[0] for t in sent] for sent in gold_data]
    return (training_data, gold_data, testing_data)


def _demo_plot_learning_curve(learning_curve_output, trainstats, teststats, take=None):
   testcurve = [teststats['initialerrors']]
   for rulescore in teststats['rulescores']:
       testcurve.append(testcurve[-1] - rulescore)
   testcurve = [1 - x/teststats['tokencount'] for x in testcurve[:take]]

   traincurve = [trainstats['initialerrors']]
   for rulescore in trainstats['rulescores']:
       traincurve.append(traincurve[-1] - rulescore)
   traincurve = [1 - x/trainstats['tokencount'] for x in traincurve[:take]]

   import matplotlib.pyplot as plt
   r = list(range(len(testcurve)))
   plt.plot(r, testcurve, r, traincurve)
   plt.axis([None, None, None, 1.0])
   plt.savefig(learning_curve_output)


NN_CD_TAGGER = tag.RegexpTagger(
    [(r'^-?[0-9]+(.[0-9]+)?$', 'CD'),
     (r'.*', 'NN')])

REGEXP_TAGGER = tag.RegexpTagger(
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



def postag(templates=None,
           tagged_data=None,
           num_sents=1000,
           max_rules=300,
           min_score=3,
           error_output="errors.out",
           rule_output="rules.yaml",
           learning_curve_output="learningcurve.png",
           learning_curve_take=300,
           baseline_backoff_tagger=None,
           randomize=False,
           train=.8,
           trace=3,
           ruleformat="str"):
    """
    Brill Tagger Demonstration
    :param templates: how many sentences of training and testing data to use
    :type templates: L{int}

    :param tagged_data: maximum number of rule instances to create
    :type tagged_data: L{int}

    :param num_sents: how many sentences of training and testing data to use
    :type num_sents: L{int}

    :param max_rules: maximum number of rule instances to create
    :type max_rules: L{int}

    :param min_score: the minimum score for a rule in order for it to be considered
    :type min_score: L{int}

    :param error_output: the file where errors will be saved
    :type error_output: C{string}

    :param learning_curve_output: filename of plotted learning curve (train and also test, if available)
    :type learning_curve_output: C{string}

    :param learning_curve_take: how many rules plotted
    :type learning_curve_take: C{int}

    :param rule_output: the file where rules will be saved
    :type rule_output: C{string}

    :param baseline_backoff_tagger: the file where rules will be saved
    :type baseline_backoff_tagger: tagger

    :param randomize: whether the training data should be a random subset of the corpus
    :type randomize: boolean

    :param train: the fraction of the the corpus to be used for training (1=all)
    :type train: L{float}

    :param trace: the level of diagnostic tracing output to produce (0-4)
    :type trace: L{int}

    :param ruleformat: rule output format, one of "str", "repr", "verbose"
    :type ruleformat: L{str}
    """

    # defaults
    baseline_backoff_tagger = baseline_backoff_tagger or REGEXP_TAGGER
    if templates is None:
        #templates = postagging_templates.fntbl37()

        #Template.expand and Feature.expand are class methods facilitating
        #generating large amounts of templates -- see their documentation
        #note -- training can easily fill all available memory
        wordtpls = Word.expand([-1,0,1], [1,2], excludezero=False)
        tagtpls = Tag.expand([-2,-1,0,1,2], [1,2], excludezero=True)
        templates = list(Template.expand([wordtpls, tagtpls], combinations=(1,3)))
        print("generated {} templates for transformation-based learning".format(len(templates)))

    (training_data, gold_data, testing_data) = _demo_prepare_data(tagged_data, train, num_sents, randomize)
    #if we are to study the learning curve, then the baseline must be trained on separate data
    #or it will be absurdly high
    if learning_curve_output:
        baseline_cutoff = len(training_data)//3
        (baseline_data, training_data) = (training_data[:baseline_cutoff], training_data[baseline_cutoff:])
    else:
        baseline_data = training_data
    (trainseqs, traintokens) = corpus_size(training_data)
    (testseqs, testtokens) = corpus_size(testing_data)
    print("Read data (train %d sentences/%d words; test %d sentences/%d words)." % (
        trainseqs, traintokens, testseqs, testtokens))

    # creating a baseline tagger (unigram tagger)
    tuni = time.time()
    baseline_tagger = tag.UnigramTagger(baseline_data, backoff=baseline_backoff_tagger)
    print("Trained unigram tagger in {:0.1f} seconds".format(time.time() - tuni))
    if gold_data:
        print("    [accuracy on test set: %f]" % baseline_tagger.evaluate(gold_data))

    # creating a Brill tagger
    tbrill = time.time()
    trainer = TaggerTrainer(baseline_tagger, templates, trace, ruleformat=ruleformat)
    brill_tagger = trainer.train(training_data, max_rules, min_score)
    print("Trained brill tagger in {:0.1f} seconds".format(time.time() - tbrill))
    if gold_data:
        print("    [accuracy on test set: %f]" % brill_tagger.evaluate(gold_data))

    # printing the learned rules (if learned silently)
    if trace <= 1:
        print("\nLearned rules: ")
        for (ruleno, rule) in brill_tagger.rules():
            print("{:3d} {:s}".format(ruleno, rule.format(ruleformat)))

    # printing template statistics
    brill_tagger.print_template_statistics()
    (taggedtest, teststats) = brill_tagger.batch_tag_incremental(testing_data, gold_data)
    trainstats = brill_tagger.train_stats()
    brill_tagger.print_template_statistics(teststats['rulescores'])

    # plotting learning curve
    if learning_curve_output is not None:
        _demo_plot_learning_curve(learning_curve_output, trainstats, teststats, take=learning_curve_take)
        print("Wrote plot of learning curve to {}".format(learning_curve_output))

    # writing error analysis to file
    if error_output is not None:
        with open(error_output, 'w') as f:
            f.write('Errors for Brill Tagger %r\n\n' % rule_output)
            for e in error_list(gold_data, taggedtest):
                f.write(e+'\n')
        print("Wrote tagger errors including context to {}".format(error_output))

    # serializing the tagger to a yaml file
    if rule_output is not None:
        with open(rule_output, 'w') as print_rules:
            yaml.dump(brill_tagger, print_rules)
        print("Wrote YAML-serialized tagger to {}".format(rule_output))
        del brill_tagger
        with open(rule_output, "r") as print_rules:
            brill_tagger = yaml.load(print_rules)
        print("Reloaded YAML-serialized tagger from {}".format(rule_output))



def demo():
    postag()
