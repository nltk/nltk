# -*- coding: utf-8 -*-
# Natural Language Toolkit: Transformation-based learning
#
# Copyright (C) 2001-2013 NLTK Project
# Author: Marcus Uneson <marcus.uneson@gmail.com>
#   based on previous (nltk2) version by
#   Christopher Maloof, Edward Loper, Steven Bird
# URL: <http://nltk.org/>
# For license information, see  LICENSE.TXT

from __future__ import print_function, division

from collections import defaultdict
import textwrap

from nltk.tag.util import untag
from nltk.tag.brill import BrillTagger

######################################################################
## Original Brill Tagger Trainer
######################################################################

class BrillTaggerTrainer(object):
    """
    A trainer for tbl taggers, superseded by nltk.tag.brill_trainer.BrillTaggerTrainer

    :param deterministic: If true, then choose between rules that
        have the same score by picking the one whose __repr__
        is lexicographically smaller.  If false, then just pick the
        first rule we find with a given score -- this will depend
        on the order in which keys are returned from dictionaries,
        and so may not be the same from one run to the next.  If
        not specified, treat as true iff trace > 0.
    """

    def __init__(self, initial_tagger, templates, trace=0,
                 deterministic=None, ruleformat="str"):
        if deterministic is None:
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
        *min_score*, and each of which has accuracy not lower than
        *min_acc*.

        #imports
        >>> from nltk.tbl.template import Template
        >>> from nltk.tag.brill import Pos, Word
        >>> from nltk.tag import RegexpTagger
        >>> from nltk.tag.brill_trainer_orig import BrillTaggerTrainer

        #some data
        >>> from nltk.corpus import treebank
        >>> training_data = treebank.tagged_sents()[:100]
        >>> baseline_data = treebank.tagged_sents()[100:200]
        >>> gold_data = treebank.tagged_sents()[200:300]
        >>> testing_data = [untag(s) for s in gold_data]

        >>> backoff = RegexpTagger([
        ... (r'^-?[0-9]+(.[0-9]+)?$', 'CD'),   # cardinal numbers
        ... (r'(The|the|A|a|An|an)$', 'AT'),   # articles
        ... (r'.*able$', 'JJ'),                # adjectives
        ... (r'.*ness$', 'NN'),                # nouns formed from adjectives
        ... (r'.*ly$', 'RB'),                  # adverbs
        ... (r'.*s$', 'NNS'),                  # plural nouns
        ... (r'.*ing$', 'VBG'),                # gerunds
        ... (r'.*ed$', 'VBD'),                 # past tense verbs
        ... (r'.*', 'NN')                      # nouns (default)
        ... ])

        >>> baseline = backoff #see NOTE1

        >>> baseline.evaluate(gold_data) #doctest: +ELLIPSIS
        0.2450142...

        #templates
        >>> Template._cleartemplates() #clear any templates created in earlier tests
        >>> templates = [Template(Pos([-1])), Template(Pos([-1]), Word([0]))]

        #construct a BrillTaggerTrainer
        >>> tt = BrillTaggerTrainer(baseline, templates, trace=3)
        >>> tagger1 = tt.train(training_data, max_rules=10)
        TBL train (orig) (seqs: 100; tokens: 2417; tpls: 2; min score: 2; min acc: None)
        <BLANKLINE>
                   B      |
           S   F   r   O  |        Score = Fixed - Broken
           c   i   o   t  |  R     Fixed = num tags changed incorrect -> correct
           o   x   k   h  |  u     Broken = num tags changed correct -> incorrect
           r   e   e   e  |  l     Other = num tags changed incorrect -> incorrect
           e   d   n   r  |  e
        ------------------+-------------------------------------------------------
         132 132   0   0  | AT->DT if Pos:NN@[-1]
          85  85   0   0  | NN->, if Pos:NN@[-1] & Word:,@[0]
          69  69   0   0  | NN->. if Pos:NN@[-1] & Word:.@[0]
          51  51   0   0  | NN->IN if Pos:NN@[-1] & Word:of@[0]
          47  63  16 161  | NN->IN if Pos:NNS@[-1]
          33  33   0   0  | NN->TO if Pos:NN@[-1] & Word:to@[0]
          26  26   0   0  | IN->. if Pos:NNS@[-1] & Word:.@[0]
          24  24   0   0  | IN->, if Pos:NNS@[-1] & Word:,@[0]
          22  27   5  24  | NN->-NONE- if Pos:VBD@[-1]
          17  17   0   0  | NN->CC if Pos:NN@[-1] & Word:and@[0]



        >>> tagger1.rules()[1:3]
        (Rule('001', 'NN', ',', [(Pos([-1]),'NN'), (Word([0]),',')]), Rule('001', 'NN', '.', [(Pos([-1]),'NN'), (Word([0]),'.')]))


        >>> train_stats = tagger1.train_stats()
        >>> [train_stats[stat] for stat in ['initialerrors', 'finalerrors', 'rulescores']]
        [1775, 1269, [132, 85, 69, 51, 47, 33, 26, 24, 22, 17]]


        ##FIXME: the following test fails -- why?
        #
        #>>> tagger1.print_template_statistics(printunused=False)
        #TEMPLATE STATISTICS (TRAIN)  2 templates, 10 rules)
        #TRAIN (   3163 tokens) initial  2358 0.2545 final:  1719 0.4565
        ##ID | Score (train) |  #Rules     | Template
        #--------------------------------------------
        #001 |   404   0.632 |   7   0.700 | Template(Pos([-1]),Word([0]))
        #000 |   235   0.368 |   3   0.300 | Template(Pos([-1]))
        #<BLANKLINE>
        #<BLANKLINE>

        >>> tagger1.evaluate(gold_data) # doctest: +ELLIPSIS
        0.43996...

        >>> (tagged, test_stats) = tagger1.batch_tag_incremental(testing_data, gold_data)


        >>> tagged[33][12:] == [('foreign', 'IN'), ('debt', 'NN'), ('of', 'IN'), ('$', 'NN'), ('64', 'CD'),
        ... ('billion', 'NN'), ('*U*', 'NN'), ('--', 'NN'), ('the', 'DT'), ('third-highest', 'NN'), ('in', 'NN'),
        ... ('the', 'DT'), ('developing', 'VBG'), ('world', 'NN'), ('.', '.')]
        True


        >>> [test_stats[stat] for stat in ['initialerrors', 'finalerrors', 'rulescores']]
        [1855, 1376, [100, 85, 67, 58, 27, 36, 27, 16, 31, 32]]

        ##a high-accuracy tagger
        >>> tagger2 = tt.train(training_data, max_rules=10, min_acc=0.99)
        TBL train (orig) (seqs: 100; tokens: 2417; tpls: 2; min score: 2; min acc: 0.99)
        <BLANKLINE>
                   B      |
           S   F   r   O  |        Score = Fixed - Broken
           c   i   o   t  |  R     Fixed = num tags changed incorrect -> correct
           o   x   k   h  |  u     Broken = num tags changed correct -> incorrect
           r   e   e   e  |  l     Other = num tags changed incorrect -> incorrect
           e   d   n   r  |  e
        ------------------+-------------------------------------------------------
         132 132   0   0  | AT->DT if Pos:NN@[-1]
          85  85   0   0  | NN->, if Pos:NN@[-1] & Word:,@[0]
          69  69   0   0  | NN->. if Pos:NN@[-1] & Word:.@[0]
          51  51   0   0  | NN->IN if Pos:NN@[-1] & Word:of@[0]
          36  36   0   0  | NN->TO if Pos:NN@[-1] & Word:to@[0]
          26  26   0   0  | NN->. if Pos:NNS@[-1] & Word:.@[0]
          24  24   0   0  | NN->, if Pos:NNS@[-1] & Word:,@[0]
          19  19   0   6  | NN->VB if Pos:TO@[-1]
          18  18   0   0  | CD->-NONE- if Pos:NN@[-1] & Word:0@[0]
          18  18   0   0  | NN->CC if Pos:NN@[-1] & Word:and@[0]


        >>> tagger2.evaluate(gold_data) # doctest: +ELLIPSIS
        0.44159544...

        >>> tagger2.rules()[2:4]
        (Rule('001', 'NN', '.', [(Pos([-1]),'NN'), (Word([0]),'.')]), Rule('001', 'NN', 'IN', [(Pos([-1]),'NN'), (Word([0]),'of')]))

        #NOTE1: (!!FIXME) A far better baseline uses nltk.tag.UnigramTagger,
        #with a RegexpTagger only as backoff. For instance,
        #>>> baseline = UnigramTagger(baseline_data, backoff=backoff)
        #However, as of Nov 2013, nltk.tag.UnigramTagger does not yield consistent results
        #between python versions. The simplistic backoff above is a workaround to make doctests
        #get consistent input.

        :param train_sents: training data
        :type train_sents: list(list(tuple))
        :param max_rules: output at most max_rules rules
        :type max_rules: int
        :param min_score: stop training when no rules better than min_score can be found
        :type min_score: int
        :param min_acc: discard any rule with lower accuracy than min_acc
        :type min_acc: float or None
        :return: the learned tagger
        :rtype: BrillTagger


        :param train_sents: training data
        :type train_sents: list(list(tuple))
        :param max_rules: output at most max_rules rules
        :type max_rules: int
        :param min_score: stop training when no rules better than min_score can be found
        :type min_score: int
        :param min_acc: discard any rule with lower accuracy than min_acc
        :type min_acc: float or None
        :return: the learned tagger
        :rtype: BrillTagger

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
            is a tbl rule and ``fixscore`` is the number of tokens
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


if __name__ == "__main__":
    import doctest
    doctest.testmod(optionflags=doctest.NORMALIZE_WHITESPACE)

