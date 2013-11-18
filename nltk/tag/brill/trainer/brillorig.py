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

from collections import defaultdict
import textwrap

from nltk.tag.util import untag
from nltk.tag.brill.tagger import BrillTagger

######################################################################
## Brill Tagger Trainer
######################################################################

class TaggerTrainer(object):
    """
    A trainer for brill taggers.

    :param deterministic: If true, then choose between rules that
        have the same score by picking the one whose __repr__
        is lexicographically smaller.  If false, then just pick the
        first rule we find with a given score -- this will depend
        on the order in which keys are returned from dictionaries,
        and so may not be the same from one run to the next.  If
        not specified, treat as true iff trace > 0.
    """

    def __init__(self, initial_tagger, templates, trace=0,
                 deterministic=False, ruleformat="str"):
        if not deterministic:
            deterministic = (trace > 0)
        self._initial_tagger = initial_tagger
        self._templates = templates
        self._trace = trace
        self._deterministic = deterministic
        self._ruleformat = ruleformat

    #////////////////////////////////////////////////////////////
    # Training
    #////////////////////////////////////////////////////////////

    def train(self, train_sents, max_rules=200, min_score=2, min_acc=None):
        """
        Trains the Brill tagger on the corpus *train_sents*,
        producing at most *max_rules* transformations, each of which
        reduces the net number of errors in the corpus by at least
        *min_score*.

        :type train_sents: list(list(tuple))
        :param train_sents: The corpus of tagged sentences
        :type max_rules: int
        :param max_rules: The maximum number of transformations to be created
        :type min_score: int
        :param min_score: The minimum acceptable net error reduction
            that each transformation must produce in the corpus.
        """

        # Create a new copy of the training corpus, and run the
        # initial tagger on it.  We will progressively update this
        # test corpus to look more like the training corpus.
        test_sents = [self._initial_tagger.tag(untag(sent))
                      for sent in train_sents]
        trainstats = {}
        trainstats['min_acc'] = min_acc
        trainstats['min_score'] = min_score
        trainstats['tokencount'] = sum(len(t) for t in test_sents)
        trainstats['sequencecount'] = len(test_sents)
        trainstats['templatecount'] = len(self._templates)
        trainstats['rulescores'] = []
        trainstats['initialerrors'] = sum(tag[1] != truth[1]
                                                    for paired in zip(test_sents, train_sents)
                                                    for (tag, truth) in zip(*paired))
        trainstats['initialacc'] = 1 - trainstats['initialerrors']/trainstats['tokencount']
        if self._trace > 0:
            print("TBL train (orig) (seqs: {sequencecount}; tokens: {tokencount}; "
                  "tpls: {templatecount}; min score: {min_score}; min acc: {min_acc})".format(**trainstats))

        if self._trace > 2:
            self._trace_header()

        # Look for useful rules.
        rules = []
        try:
            while len(rules) < max_rules:
                (rule, score, fixscore) = self._best_rule(test_sents,
                                                          train_sents, min_acc=min_acc)
                if rule is None or score < min_score:
                    if self._trace > 1:
                        print('Insufficient improvement; stopping')
                    break
                else:
                    # Add the rule to our list of rules.
                    rules.append(rule)
                    trainstats['rulescores'].append(score)
                    # Use the rules to update the test corpus.  Keep
                    # track of how many times the rule applied (k).
                    k = 0
                    for sent in test_sents:
                        k += len(rule.apply(sent))
                    # Display trace output.
                    if self._trace > 1:
                        self._trace_rule(rule, score, fixscore, k)
        # The user can also cancel training manually:
        except KeyboardInterrupt:
            print("Training stopped manually -- %d rules found" % len(rules))

        trainstats['finalerrors'] = trainstats['initialerrors'] - sum(trainstats['rulescores'])
        trainstats['finalacc'] = 1 - trainstats['finalerrors']/trainstats['tokencount']
        # Create and return a tagger from the rules we found.
        return BrillTagger(self._initial_tagger, rules, trainstats)

    #////////////////////////////////////////////////////////////
    # Finding the best rule
    #////////////////////////////////////////////////////////////

    # Finds the rule that makes the biggest net improvement in the corpus.
    # Returns a (rule, score) pair.
    def _best_rule(self, test_sents, train_sents, min_acc):
        # Create a dictionary mapping from each tag to a list of the
        # indices that have that tag in both test_sents and
        # train_sents (i.e., where it is correctly tagged).
        correct_indices = defaultdict(list)
        for sentnum, sent in enumerate(test_sents):
            for wordnum, tagged_word in enumerate(sent):
                if tagged_word[1] == train_sents[sentnum][wordnum][1]:
                    tag = tagged_word[1]
                    correct_indices[tag].append( (sentnum, wordnum) )

        # Find all the rules that correct at least one token's tag,
        # and the number of tags that each rule corrects (in
        # descending order of number of tags corrected).
        rules = self._find_rules(test_sents, train_sents)

        # Keep track of the current best rule, and its score.
        best_rule, best_score, best_fixscore = None, 0, 0

        # Consider each rule, in descending order of fixscore (the
        # number of tags that the rule corrects, not including the
        # number that it breaks).
        for (rule, fixscore) in rules:
            # The actual score must be <= fixscore; so if best_score
            # is bigger than fixscore, then we already have the best
            # rule.
            if best_score > fixscore or (best_score == fixscore and
                                         not self._deterministic):
                return best_rule, best_score, best_fixscore

            # Calculate the actual score, by decrementing score (initialized
            # to fixscore once for each tag that the rule changes to an incorrect
            # value.
            score = fixscore
            if rule.original_tag in correct_indices:
                for (sentnum, wordnum) in correct_indices[rule.original_tag]:
                    if rule.applies(test_sents[sentnum], wordnum):
                        score -= 1
                        # If the rule accuracy goes below min_acc,
                        # this rule is not eligible; so move on

                        if min_acc is not None and fixscore/(2*fixscore-score) < min_acc:
                            break
                        # If the score goes below best_score, then we know
                        # that this isn't the best rule; so move on
                        if score < best_score or (score == best_score and
                                                  not self._deterministic):
                            break

            # If the actual score is better than the best score, then
            # update best_score and best_rule.
            if (( min_acc is None or                          #IF: either no threshold for accuracy,
                  fixscore/(2*fixscore-score) >= min_acc) and #or accuracy good enough AND
                ( score > best_score or                       #(score is higher than current leader OR
                  (score == best_score and                    #score is same as leader, but this
                   self._deterministic and                    #rule sorts before it when determinism
                   repr(rule) < repr(best_rule)))):           # is asked for): THEN update...
                best_rule, best_score, best_fixscore = rule, score, fixscore

        # Return the best rule, and its score.
        return best_rule, best_score, best_fixscore

    def _find_rules(self, test_sents, train_sents):
        """
        Find all rules that correct at least one token's tag in *test_sents*.

        :return: A list of tuples ``(rule, fixscore)``, where rule
            is a brill rule and ``fixscore`` is the number of tokens
            whose tag the rule corrects.  Note that ``fixscore`` does
            *not* include the number of tokens whose tags are changed
            to incorrect values.
        """

        # Create a list of all indices that are incorrectly tagged.
        error_indices = []
        for sentnum, sent in enumerate(test_sents):
            for wordnum, tagged_word in enumerate(sent):
                if tagged_word[1] != train_sents[sentnum][wordnum][1]:
                    error_indices.append( (sentnum, wordnum) )

        # Create a dictionary mapping from rules to their positive-only
        # scores.
        rule_score_dict = defaultdict(int)
        for (sentnum, wordnum) in error_indices:
            test_sent = test_sents[sentnum]
            train_sent = train_sents[sentnum]
            for rule in self._find_rules_at(test_sent, train_sent, wordnum):
                rule_score_dict[rule] += 1

        # Convert the dictionary into a list of (rule, score) tuples,
        # sorted in descending order of score.
        return sorted(rule_score_dict.items(),
                      key=lambda rule_score: -rule_score[1])

    def _find_rules_at(self, test_sent, train_sent, i):
        """
        :rtype: set
        :return: the set of all rules (based on the templates) that
            correct token *i*'s tag in *test_sent*.
        """
        applicable_rules = set()
        if test_sent[i][1] != train_sent[i][1]:
            correct_tag = train_sent[i][1]
            for template in self._templates:
                new_rules = template.applicable_rules(test_sent, i,
                                                      correct_tag)
                applicable_rules.update(new_rules)

        return applicable_rules

    #////////////////////////////////////////////////////////////
    # Tracing
    #////////////////////////////////////////////////////////////

    def _trace_header(self):
        print("""
           B      |
   S   F   r   O  |        Score = Fixed - Broken
   c   i   o   t  |  R     Fixed = num tags changed incorrect -> correct
   o   x   k   h  |  u     Broken = num tags changed correct -> incorrect
   r   e   e   e  |  l     Other = num tags changed incorrect -> incorrect
   e   d   n   r  |  e
------------------+-------------------------------------------------------
        """.rstrip())

    def _trace_rule(self, rule, score, fixscore, numchanges):
        rulestr = rule.format(self._ruleformat)

        if self._trace > 2:
            print(('%4d%4d%4d%4d ' % (score, fixscore, fixscore-score,
                                      numchanges-fixscore*2+score)), '|', end=' ')
            print(textwrap.fill(rulestr, initial_indent=' '*20, width=79,
                                subsequent_indent=' '*18+'|   ').strip())
        else:
            print(rulestr)

#backwards compatibility
BrillTaggerTrainer = TaggerTrainer
