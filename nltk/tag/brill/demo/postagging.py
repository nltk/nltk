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
import os

import random
import yaml
import time

from nltk import tag
from nltk.corpus import treebank

from nltk.tag.brill.erroranalysis import error_list
from nltk.tag.brill.template import Template
from nltk.tag.brill.application.postagging import Word, Tag

def demo():
    postag()

def demo_repr_rule_format():
    postag(ruleformat="repr")

def demo_verbose_rule_format():
    postag(ruleformat="verbose")

def demo_multiposition_template():
    #for contiguous ranges, a 2-arg form giving inclusive end
    # points can also be used: Tag(-3, -1)
    postag(templates=[Template(Tag([-3,-2,-1]))])

def demo_multifeature_template():
    postag(templates=[Template(Word([0]), Tag([-2,-1]))])

def demo_template_statistics():
    postag(incremental_stats=True, template_stats=True)

def demo_generated_templates():
    #Template.expand and Feature.expand are class methods facilitating
    #generating large amounts of templates -- see their documentation
    #note -- training with 500 templates can easily fill all available
    #even on relatively small corpora
    wordtpls = Word.expand([-1,0,1], [1,2], excludezero=False)
    tagtpls = Tag.expand([-2,-1,0,1], [1,2], excludezero=True)
    templates = list(Template.expand([wordtpls, tagtpls], combinations=(1,3)))
    print("Generated {0} templates for transformation-based learning".format(len(templates)))
    postag(templates=templates, incremental_stats=True, template_stats=True)

def demo_learning_curve():
    #requires matplotlib
    postag(incremental_stats=True, learning_curve_output="learningcurve.png")

def demo_error_analysis():
    postag(error_output="errors.txt")

def demo_serialize_tagger():
    postag(rule_output="rules.yaml")

def demo_brillorig_training():
    #much slower, only for demonstration
    postag(training_algorithm="brillorig", min_score=10)

def postag(
    templates=None,
    tagged_data=None,
    num_sents=1000,
    max_rules=300,
    min_score=3,
    train=0.8,
    trace=3,
    randomize=False,
    ruleformat="str",
    incremental_stats=False,
    template_stats=False,
    error_output=None,
    rule_output=None,
    learning_curve_output=None,
    learning_curve_take=300,
    baseline_backoff_tagger=None,
    training_algorithm = "fast",
    separate_baseline_data=True,
    cache_baseline_tagger=None):
    """
    Brill Tagger Demonstration
    :param templates: how many sentences of training and testing data to use
    :type templates: list of Template

    :param tagged_data: maximum number of rule instances to create
    :type tagged_data: C{int}

    :param num_sents: how many sentences of training and testing data to use
    :type num_sents: C{int}

    :param max_rules: maximum number of rule instances to create
    :type max_rules: C{int}

    :param min_score: the minimum score for a rule in order for it to be considered
    :type min_score: C{int}

    :param train: the fraction of the the corpus to be used for training (1=all)
    :type train: C{float}

    :param trace: the level of diagnostic tracing output to produce (0-4)
    :type trace: C{int}

    :param randomize: whether the training data should be a random subset of the corpus
    :type randomize: C{bool}

    :param ruleformat: rule output format, one of "str", "repr", "verbose"
    :type ruleformat: C{str}

    :param incremental_stats: if true, will tag incrementally and collect stats for each rule (rather slow)
    :type incremental_stats: C{bool}

    :param template_stats: if true, will print per-template statistics collected in training and (optionally) testing
    :type template_stats: C{bool}

    :param error_output: the file where errors will be saved
    :type error_output: C{string}

    :param rule_output: the file where the learned brill tagger will be saved
    :type rule_output: C{string}

    :param learning_curve_output: filename of plot of learning curve(s) (train and also test, if available)
    :type learning_curve_output: C{string}

    :param learning_curve_take: how many rules plotted
    :type learning_curve_take: C{int}

    :param baseline_backoff_tagger: the file where rules will be saved
    :type baseline_backoff_tagger: tagger

    :param training_algorithm: at present, only "fast" or "brillorig"
    :type training_algorithm: C{string}

    :param separate_baseline_data: use a fraction of the training data exclusively for training baseline
    :type separate_baseline_data: C{bool}

    :param cache_baseline_tagger: cache baseline tagger to this file (only interesting as a temporary workaround to get
                                  deterministic output from the baseline unigram tagger between python versions)
    :type cache_baseline_tagger: C{string}


    """

    # defaults
    if training_algorithm == "fast":
        from nltk.tag.brill.trainer.fast import TaggerTrainer
    else:
        from nltk.tag.brill.trainer.brillorig import TaggerTrainer
    baseline_backoff_tagger = baseline_backoff_tagger or REGEXP_TAGGER
    if templates is None:
        ## pre-built template sets taken from typical systems or publications
        from nltk.tag.brill.demo import postagging_templates
        ## for instance:
        templates = postagging_templates.fntbl37()

    (training_data, baseline_data, gold_data, testing_data) = \
       _demo_prepare_data(tagged_data, train, num_sents, randomize, separate_baseline_data)

    # creating (or reloading from cache) a baseline tagger (unigram tagger)
    # this is just a mechanism for getting deterministic output from the baseline between
    # python versions
    if cache_baseline_tagger:
        if not os.path.exists(cache_baseline_tagger):
            baseline_tagger = tag.UnigramTagger(baseline_data, backoff=baseline_backoff_tagger)
            with open(cache_baseline_tagger, 'w') as print_rules:
                yaml.dump(baseline_tagger, print_rules)
            print("Trained baseline tagger, wrote yaml to {0}".format(cache_baseline_tagger))
        with open(cache_baseline_tagger, "r") as print_rules:
            baseline_tagger= yaml.load(print_rules)
            print("Reloaded YAML-serialized tagger from {0}".format(cache_baseline_tagger))
    else:
        baseline_tagger = tag.UnigramTagger(baseline_data, backoff=baseline_backoff_tagger)
        print("Trained baseline tagger")
    if gold_data:
        print("    Accuracy on test set: {0:0.4f}".format(baseline_tagger.evaluate(gold_data)))

    # creating a Brill tagger
    tbrill = time.time()
    trainer = TaggerTrainer(baseline_tagger, templates, trace, ruleformat=ruleformat)
    print("Training brill tagger...")
    brill_tagger = trainer.train(training_data, max_rules, min_score)
    print("Trained brill tagger in {0:0.2f} seconds".format(time.time() - tbrill))
    if gold_data:
        print("    Accuracy on test set: %.4f" % brill_tagger.evaluate(gold_data))

    # printing the learned rules, if learned silently
    if trace == 1:
        print("\nLearned rules: ")
        for (ruleno, rule) in enumerate(brill_tagger.rules(),1):
            print("{0:4d} {1:s}".format(ruleno, rule.format(ruleformat)))


    # printing template statistics (optionally including comparison with the training data)
    # note: if not separate_baseline_data, then baseline accuracy will be artificially high
    if  incremental_stats:
        print("Incrementally tagging the test data, collecting individual rule statistics")
        (taggedtest, teststats) = brill_tagger.batch_tag_incremental(testing_data, gold_data)
        print("    Rule statistics collected")
        trainstats = brill_tagger.train_stats()
        if template_stats:
            brill_tagger.print_template_statistics(teststats)
        if learning_curve_output:
            _demo_plot(learning_curve_output, teststats, trainstats, take=learning_curve_take)
            print("Wrote plot of learning curve to {0}".format(learning_curve_output))
    else:
        print("Tagging the test data")
        taggedtest = brill_tagger.batch_tag(testing_data)
        if template_stats:
            brill_tagger.print_template_statistics()

    # writing error analysis to file
    if error_output is not None:
        with open(error_output, 'w') as f:
            f.write('Errors for Brill Tagger %r\n\n' % rule_output)
            for e in error_list(gold_data, taggedtest):
                f.write(e+'\n')
        print("Wrote tagger errors including context to {0}".format(error_output))

    # serializing the tagger to a yaml file and reloading (just to see it works)
    if rule_output is not None:
        with open(rule_output, 'w') as print_rules:
            yaml.dump(brill_tagger, print_rules)
        print("Wrote YAML-serialized tagger to {0}".format(rule_output))
        del brill_tagger
        with open(rule_output, "r") as print_rules:
            brill_tagger = yaml.load(print_rules)
        print("Reloaded YAML-serialized tagger from {0}".format(rule_output))

def _demo_prepare_data(tagged_data, train, num_sents, randomize, separate_baseline_data):
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
    if not separate_baseline_data:
        baseline_data = training_data
    else:
        bl_cutoff = len(training_data) // 3
        (baseline_data, training_data) = (training_data[:bl_cutoff], training_data[bl_cutoff:])
    (trainseqs, traintokens) = corpus_size(training_data)
    (testseqs, testtokens) = corpus_size(testing_data)
    (bltrainseqs, bltraintokens) = corpus_size(baseline_data)
    print("Read testing data ({0:d} sents/{1:d} wds)".format(testseqs, testtokens))
    print("Read training data ({0:d} sents/{1:d} wds)".format(trainseqs, traintokens))
    print("Read baseline data ({0:d} sents/{1:d} wds) {2:s}".format(
        bltrainseqs, bltraintokens, "" if separate_baseline_data else "[reused the training set]"))
    return (training_data, baseline_data, gold_data, testing_data)


def _demo_plot(learning_curve_output, teststats, trainstats=None, take=None):
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


def corpus_size(seqs):
    return (len(seqs), sum(len(x) for x in seqs))
