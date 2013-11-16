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

import bisect
from collections import defaultdict
import textwrap

from nltk.tag.util import untag
from nltk.tag.brill.tagger import BrillTagger

######################################################################
## Fast Brill Tagger Trainer
######################################################################

class TaggerTrainer(object):
    """
    A faster trainer for brill taggers.
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

        self._tag_positions = None
        """Mapping from tags to lists of positions that use that tag."""

        self._rules_by_position = None
        """Mapping from positions to the set of rules that are known
           to occur at that position.  Position is (sentnum, wordnum).
           Initially, this will only contain positions where each rule
           applies in a helpful way; but when we examine a rule, we'll
           extend this list to also include positions where each rule
           applies in a harmful or neutral way."""

        self._positions_by_rule = None
        """Mapping from rule to position to effect, specifying the
           effect that each rule has on the overall score, at each
           position.  Position is (sentnum, wordnum); and effect is
           -1, 0, or 1.  As with _rules_by_position, this mapping starts
           out only containing rules with positive effects; but when
           we examine a rule, we'll extend this mapping to include
           the positions where the rule is harmful or neutral."""

        self._rules_by_score = None
        """Mapping from scores to the set of rules whose effect on the
           overall score is upper bounded by that score.  Invariant:
           rulesByScore[s] will contain r iff the sum of
           _positions_by_rule[r] is s."""

        self._rule_scores = None
        """Mapping from rules to upper bounds on their effects on the
           overall score.  This is the inverse mapping to _rules_by_score.
           Invariant: ruleScores[r] = sum(_positions_by_rule[r])"""

        self._first_unknown_position = None
        """Mapping from rules to the first position where we're unsure
           if the rule applies.  This records the next position we
           need to check to see if the rule messed anything up."""


    #////////////////////////////////////////////////////////////
    # Training
    #////////////////////////////////////////////////////////////

    def train(self, train_sents, max_rules=200, min_score=2):
        # Basic idea: Keep track of the rules that apply at each position.
        # And keep track of the positions to which each rule applies.

        # Create a new copy of the training corpus, and run the
        # initial tagger on it.  We will progressively update this
        # test corpus to look more like the training corpus.
        test_sents = [list(self._initial_tagger.tag(untag(sent)))
                      for sent in train_sents]

        # Collect some statistics on the training process
        trainstats = {}
        trainstats['tokencount'] = sum(len(t) for t in test_sents)
        trainstats['sequencecount'] = len(test_sents)
        trainstats['templatecount'] = len(self._templates)
        trainstats['rulescores'] = []
        trainstats['initialerrors'] = sum(tag[1] != truth[1]
                                                    for paired in zip(test_sents, train_sents)
                                                    for (tag, truth) in zip(*paired))
        trainstats['initialacc'] = 1 - trainstats['initialerrors']/trainstats['tokencount']
        if self._trace > 0:
            print("Training Brill tagger on {sequencecount} sequences/{tokencount} "
                  "tokens and {templatecount} templates".format(**trainstats))

        # Initialize our mappings.  This will find any errors made
        # by the initial tagger, and use those to generate repair
        # rules, which are added to the rule mappings.
        if self._trace > 0: print("Finding initial useful rules...")
        self._init_mappings(test_sents, train_sents)
        if self._trace > 0: print(("    Found %d useful rules." %
                                   len(self._rule_scores)))

        # Let the user know what we're up to.
        if self._trace > 2: self._trace_header()
        elif self._trace == 1: print("Selecting rules...")

        # Repeatedly select the best rule, and add it to `rules`.
        rules = []
        try:
            while (len(rules) < max_rules):
                # Find the best rule, and add it to our rule list.
                rule = self._best_rule(train_sents, test_sents, min_score)
                if rule:
                    rules.append(rule)
                    score = self._rule_scores[rule]
                    trainstats['rulescores'].append(score)
                else:
                    break # No more good rules left!

                # Report the rule that we found.
                if self._trace > 1: self._trace_rule(rule)

                # Apply the new rule at the relevant sites
                self._apply_rule(rule, test_sents)

                # Update _tag_positions[rule.original_tag] and
                # _tag_positions[rule.replacement_tag] for the affected
                # positions (i.e., self._positions_by_rule[rule]).
                self._update_tag_positions(rule)

                # Update rules that were affected by the change.
                self._update_rules(rule, train_sents, test_sents)

        # The user can cancel training manually:
        except KeyboardInterrupt:
            print("Training stopped manually -- %d rules found" % len(rules))

        # Discard our tag position mapping & rule mappings.
        self._clean()
        trainstats['finalerrors'] = trainstats['initialerrors'] - sum(trainstats['rulescores'])
        trainstats['finalacc'] = 1 - trainstats['finalerrors']/trainstats['tokencount']
        # Create and return a tagger from the rules we found.
        return BrillTagger(self._initial_tagger, rules, trainstats)

    def _init_mappings(self, test_sents, train_sents):
        """
        Initialize the tag position mapping & the rule related
        mappings.  For each error in test_sents, find new rules that
        would correct them, and add them to the rule mappings.
        """
        self._tag_positions = defaultdict(list)
        self._rules_by_position = defaultdict(set)
        self._positions_by_rule = defaultdict(dict)
        self._rules_by_score = defaultdict(set)
        self._rule_scores = defaultdict(int)
        self._first_unknown_position = defaultdict(int)
        # Scan through the corpus, initializing the tag_positions
        # mapping and all the rule-related mappings.
        for sentnum, sent in enumerate(test_sents):
            for wordnum, (word, tag) in enumerate(sent):

                # Initialize tag_positions
                self._tag_positions[tag].append( (sentnum,wordnum) )

                # If it's an error token, update the rule-related mappings.
                correct_tag = train_sents[sentnum][wordnum][1]
                if tag != correct_tag:
                    for rule in self._find_rules(sent, wordnum, correct_tag):
                        self._update_rule_applies(rule, sentnum, wordnum,
                                                  train_sents)

    def _clean(self):
        self._tag_positions = None
        self._rules_by_position = None
        self._positions_by_rule = None
        self._rules_by_score = None
        self._rule_scores = None
        self._first_unknown_position = None

    def _find_rules(self, sent, wordnum, new_tag):
        """
        Use the templates to find rules that apply at index *wordnum*
        in the sentence *sent* and generate the tag *new_tag*.
        """
        for template in self._templates:
            for rule in template.applicable_rules(sent, wordnum, new_tag):
                yield rule

    def _update_rule_applies(self, rule, sentnum, wordnum, train_sents):
        """
        Update the rule data tables to reflect the fact that
        *rule* applies at the position *(sentnum, wordnum)*.
        """
        pos = sentnum, wordnum

        # If the rule is already known to apply here, ignore.
        # (This only happens if the position's tag hasn't changed.)
        if pos in self._positions_by_rule[rule]:
            return

        # Update self._positions_by_rule.
        correct_tag = train_sents[sentnum][wordnum][1]
        if rule.replacement_tag == correct_tag:
            self._positions_by_rule[rule][pos] = 1
        elif rule.original_tag == correct_tag:
            self._positions_by_rule[rule][pos] = -1
        else: # was wrong, remains wrong
            self._positions_by_rule[rule][pos] = 0

        # Update _rules_by_position
        self._rules_by_position[pos].add(rule)

        # Update _rule_scores.
        old_score = self._rule_scores[rule]
        self._rule_scores[rule] += self._positions_by_rule[rule][pos]

        # Update _rules_by_score.
        self._rules_by_score[old_score].discard(rule)
        self._rules_by_score[self._rule_scores[rule]].add(rule)

    def _update_rule_not_applies(self, rule, sentnum, wordnum):
        """
        Update the rule data tables to reflect the fact that *rule*
        does not apply at the position *(sentnum, wordnum)*.
        """
        pos = sentnum, wordnum

        # Update _rule_scores.
        old_score = self._rule_scores[rule]
        self._rule_scores[rule] -= self._positions_by_rule[rule][pos]

        # Update _rules_by_score.
        self._rules_by_score[old_score].discard(rule)
        self._rules_by_score[self._rule_scores[rule]].add(rule)

        # Update _positions_by_rule
        del self._positions_by_rule[rule][pos]
        self._rules_by_position[pos].remove(rule)

        # Optional addition: if the rule now applies nowhere, delete
        # all its dictionary entries.

    def _best_rule(self, train_sents, test_sents, min_score):
        """
        Find the next best rule.  This is done by repeatedly taking a
        rule with the highest score and stepping through the corpus to
        see where it applies.  When it makes an error (decreasing its
        score) it's bumped down, and we try a new rule with the
        highest score.  When we find a rule which has the highest
        score *and* which has been tested against the entire corpus, we
        can conclude that it's the next best rule.
        """
        if self._rules_by_score == {}:
            return None
        max_score = max(self._rules_by_score)

        while max_score >= min_score:
            best_rules = list(self._rules_by_score[max_score])
            if self._deterministic:
                best_rules.sort(key=repr)
            for rule in best_rules:
                positions = self._tag_positions[rule.original_tag]

                unk = self._first_unknown_position.get(rule, (0,-1))
                start = bisect.bisect_left(positions, unk)

                for i in range(start, len(positions)):
                    sentnum, wordnum = positions[i]
                    if rule.applies(test_sents[sentnum], wordnum):
                        self._update_rule_applies(rule, sentnum, wordnum,
                                                  train_sents)
                        if self._rule_scores[rule] < max_score:
                            self._first_unknown_position[rule] = (sentnum,
                                                                  wordnum+1)
                            break # The update demoted the rule.

                if self._rule_scores[rule] == max_score:
                    self._first_unknown_position[rule] = (len(train_sents)+1,0)
                    return rule

            # We demoted all the rules with score==max_score.
            assert not self._rules_by_score[max_score]
            del self._rules_by_score[max_score]
            if len(self._rules_by_score) == 0: return None
            max_score = max(self._rules_by_score)

        # We reached the min-score threshold.
        return None

    def _apply_rule(self, rule, test_sents):
        """
        Update *test_sents* by applying *rule* everywhere where its
        conditions are met.
        """
        update_positions = set(self._positions_by_rule[rule])
        old_tag = rule.original_tag
        new_tag = rule.replacement_tag

        if self._trace > 3: self._trace_apply(len(update_positions))

        # Update test_sents.
        for (sentnum, wordnum) in update_positions:
            text = test_sents[sentnum][wordnum][0]
            test_sents[sentnum][wordnum] = (text, new_tag)

    def _update_tag_positions(self, rule):
        """
        Update _tag_positions to reflect the changes to tags that are
        made by *rule*.
        """
        # Update the tag index.
        for pos in self._positions_by_rule[rule]:
            # Delete the old tag.
            old_tag_positions = self._tag_positions[rule.original_tag]
            old_index = bisect.bisect_left(old_tag_positions, pos)
            del old_tag_positions[old_index]
            # Insert the new tag.
            new_tag_positions = self._tag_positions[rule.replacement_tag]
            bisect.insort_left(new_tag_positions, pos)

    def _update_rules(self, rule, train_sents, test_sents):
        """
        Check if we should add or remove any rules from consideration,
        given the changes made by *rule*.
        """
        # Collect a list of all positions that might be affected.
        neighbors = set()
        for sentnum, wordnum in self._positions_by_rule[rule]:
            for template in self._templates:
                n = template.get_neighborhood(test_sents[sentnum], wordnum)
                neighbors.update([(sentnum, i) for i in n])

        # Update the rules at each position.
        num_obsolete = num_new = num_unseen = 0
        for sentnum, wordnum in neighbors:
            test_sent = test_sents[sentnum]
            correct_tag = train_sents[sentnum][wordnum][1]

            # Check if the change causes any rule at this position to
            # stop matching; if so, then update our rule mappings
            # accordingly.
            old_rules = set(self._rules_by_position[sentnum, wordnum])
            for old_rule in old_rules:
                if not old_rule.applies(test_sent, wordnum):
                    num_obsolete += 1
                    self._update_rule_not_applies(old_rule, sentnum, wordnum)

            # Check if the change causes our templates to propose any
            # new rules for this position.
            site_rules = set()
            for template in self._templates:
                for new_rule in template.applicable_rules(test_sent, wordnum,
                                                          correct_tag):
                    if new_rule not in old_rules:
                        num_new += 1
                        if new_rule not in self._rule_scores:
                            num_unseen += 1
                        old_rules.add(new_rule)
                        self._update_rule_applies(new_rule, sentnum,
                                                  wordnum, train_sents)

            # We may have caused other rules to match here, that are
            # not proposed by our templates -- in particular, rules
            # that are harmful or neutral.  We therefore need to
            # update any rule whose first_unknown_position is past
            # this rule.
            for new_rule, pos in self._first_unknown_position.items():
                if pos > (sentnum, wordnum):
                    if new_rule not in old_rules:
                        num_new += 1
                        if new_rule.applies(test_sent, wordnum):
                            self._update_rule_applies(new_rule, sentnum,
                                                      wordnum, train_sents)

        if self._trace > 3:
            self._trace_update_rules(num_obsolete, num_new, num_unseen)

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

    def _trace_rule(self, rule):
        assert self._rule_scores[rule] == \
               sum(self._positions_by_rule[rule].values())

        changes = self._positions_by_rule[rule].values()
        num_changed = len(changes)
        num_fixed = len([c for c in changes if c==1])
        num_broken = len([c for c in changes if c==-1])
        num_other = len([c for c in changes if c==0])
        score = self._rule_scores[rule]

        rulestr = rule.format(self._ruleformat)
        if self._trace > 2:
            print('%4d%4d%4d%4d  |' % (score,num_fixed,num_broken,num_other), end=' ')
            print(textwrap.fill(rulestr, initial_indent=' '*20,
                                subsequent_indent=' '*18+'|   ').strip())
        else:
            print(rulestr)

    def _trace_apply(self, num_updates):
        prefix = ' '*18+'|'
        print(prefix)
        print(prefix, 'Applying rule to %d positions.' % num_updates)

    def _trace_update_rules(self, num_obsolete, num_new, num_unseen):
        prefix = ' '*18+'|'
        print(prefix, 'Updated rule tables:')
        print(prefix, ('  - %d rule applications removed' % num_obsolete))
        print(prefix, ('  - %d rule applications added (%d novel)' %
                       (num_new, num_unseen)))
        print(prefix)

#backwards compatibility
FastBrillTaggerTrainer = TaggerTrainer

