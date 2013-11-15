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

from __future__ import print_function, division

from collections import defaultdict, Counter
import yaml

from nltk.tag.api import TaggerI
from nltk.tag.brill import template

######################################################################
## The Brill Tagger
######################################################################

class BrillTagger(TaggerI, yaml.YAMLObject):
    """
    Brill's transformational rule-based tagger.  Brill taggers use an
    initial tagger (such as ``tag.DefaultTagger``) to assign an initial
    tag sequence to a text; and then apply an ordered list of
    transformational rules to correct the tags of individual tokens.
    These transformation rules are specified by the ``BrillRule``
    interface.

    Brill taggers can be created directly, from an initial tagger and
    a list of transformational rules; but more often, Brill taggers
    are created by learning rules from a training corpus, using either
    ``BrillTaggerTrainer`` or ``FastBrillTaggerTrainer``.
    """

    yaml_tag = '!nltk.BrillTagger'
    def __init__(self, initial_tagger, rules, training_stats=None):
        """
        :param initial_tagger: The initial tagger
        :type initial_tagger: TaggerI

        :param rules: An ordered list of transformation rules that
            should be used to correct the initial tagging.
        :type rules: list(BrillRule)

        :param training_stats: A dictionary of statistics collected
            during training, for possible later use
        :type rules: dict

        """
        self._initial_tagger = initial_tagger
        self._rules = tuple(rules)
        self._training_stats = training_stats

    def rules(self):
        return self._rules

    def train_stats(self, statistic=None):
        if statistic is None:
            return self._training_stats
        else:
            return self._training_stats.get(statistic)

    def tag(self, tokens):
        # Inherit documentation from TaggerI

        # Run the initial tagger.
        tagged_tokens = self._initial_tagger.tag(tokens)

        # Create a dictionary that maps each tag to a list of the
        # indices of tokens that have that tag.
        tag_to_positions = defaultdict(set)
        for i, (token, tag) in enumerate(tagged_tokens):
            tag_to_positions[tag].add(i)

        # Apply each rule, in order.  Only try to apply rules at
        # positions that have the desired original tag.
        for rule in self._rules:
            # Find the positions where it might apply
            positions = tag_to_positions.get(rule.original_tag, [])
            # Apply the rule at those positions.
            changed = rule.apply(tagged_tokens, positions)
            # Update tag_to_positions with the positions of tags that
            # were modified.
            for i in changed:
                tag_to_positions[rule.original_tag].remove(i)
                tag_to_positions[rule.replacement_tag].add(i)

        return tagged_tokens

    def print_template_statistics(self, testscores=None, printunused=True):
        tids = [r.templateid for r in self._rules]
        trainscores = self.train_stats('rulescores')
        assert len(trainscores) == len(tids), "corrupt statistics: " \
            "{} train scores for {} rules".format(trainscores, tids)
        template_counts = Counter(tids)
        weighted_traincounts = Counter()
        for (tid, score) in zip(tids, trainscores):
            weighted_traincounts[tid] += score
        tottrainscores = sum(trainscores)

        def print_train_stats():
            print("TEMPLATE TRAINING STATISTICS ({} templates, {} rules)".format(len(template_counts),len(tids)))
            head = "#ID | Score (train)  | #Rules (train) | Template"
            print(head, "\n", "-" * len(head), sep="")
            for (tid, trainscore) in weighted_traincounts.most_common():
                s = "{:s} |  {:5d}   {:.3f} |   {:4d}   {:.3f} | {:s}".format(
                 tid,
                 trainscore,
                 trainscore/tottrainscores,
                 template_counts[tid],
                 template_counts[tid]/len(tids),
                 template.Template.ALLTEMPLATES[int(tid)])
                print(s)

        def print_testtrain_stats():
            print("TEMPLATE TRAINING STATISTICS ({} templates, {} rules)".format(len(template_counts),len(tids)))
            weighted_testcounts = Counter()
            for (tid, score) in zip(tids, testscores):
                weighted_testcounts[tid] += score
            tottestscores = sum(testscores)
            head = "#ID | Score (test)  | Score (train)  | #Rules (train) | Template"
            print(head, "\n", "-" * len(head), sep="")
            for (tid, testscore) in weighted_testcounts.most_common():
                s = "{:s} | {:5d}  {:6.3f} |   {:4d}   {:.3f} |   {:4d}   {:.3f} | {:s}".format(
                 tid,
                 testscore,
                 testscore/tottestscores,
                 weighted_traincounts[tid],
                 weighted_traincounts[tid]/tottrainscores,
                 template_counts[tid],
                 template_counts[tid]/len(tids),
                 template.Template.ALLTEMPLATES[int(tid)])
                print(s)

        def print_unused_templates():
            usedtpls = set([int(tid) for tid in tids])
            unused = [(tid, tpl) for (tid, tpl) in enumerate(template.Template.ALLTEMPLATES) if tid not in usedtpls]
            print("UNUSED TEMPLATES ({})".format(len(unused)))
            for (tid, tpl) in unused:
                print("{:03d} {:s}".format(tid, tpl))

        if testscores is None:
            print_train_stats()
        else:
            print_testtrain_stats()
        print()
        if printunused:
            print_unused_templates()
        print()

    def batch_tag_incremental(self, sequences, gold):
        """
        Tags by applying each rule to the entire corpus (rather than all rules to a
        single sequence). The point is to collect statistics on the test set for
        individual rules.

        NOTE: This is inefficient (does not build any index, so will traverse the entire
        corpus N times for N rules) -- usually you would not care about statistics for
        individual rules and thus use batch_tag() instead

        :param sequences: lists of token sequences (sentences, in some applications) to be tagged
        :type sequences: list of list of strings
        :param gold: the gold standard
        :type gold: list of list of strings
        :returns: tuple of (tagged_sequences, list of rule scores)
        """
        def counterrors(xs):
            return sum(t[1] != g[1]
                       for pair in zip(xs, gold)
                          for (t, g) in zip(*pair))
        testing_stats = {}
        testing_stats['tokencount'] = sum(len(t) for t in sequences)
        testing_stats['sequencecount'] = len(sequences)
        tagged_tokenses = [self._initial_tagger.tag(tokens) for tokens in sequences]
        testing_stats['initialerrors'] = counterrors(tagged_tokenses)
        # Apply each rule to the entire corpus, in order
        errors = [testing_stats['initialerrors']]
        for rule in self._rules:
            for tagged_tokens in tagged_tokenses:
                rule.apply(tagged_tokens)
            errors.append(counterrors(tagged_tokenses))
        testing_stats['rulescores'] = [err0 - err1 for (err0, err1) in zip(errors, errors[1:])]
        return (tagged_tokenses, testing_stats)

