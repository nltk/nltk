# Natural Language Toolkit: Brill Tagger
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Christopher Maloof <cjmaloof@gradient.cis.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@ldc.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Brill's transformational rule-based tagger.

@group Tagger: BrillTagger
@group Rules: BrillRuleI, *Rule
@group Templates: BrillTemplateI, *Template
@group Trainers: BrillTaggerTrainer, FastBrillTaggerTrainer
"""

from nltk.tagger import TaggerI, DefaultTagger, RegexpTagger, \
     UnigramTagger, BackoffTagger, tagger_accuracy
from nltk.token import Token
from nltk.corpus import treebank

from sets import Set # for sets
import bisect        # for binary search through a subset of indices
import os            # for finding WSJ files
import pickle        # for storing/loading rule lists
import random        # for shuffling WSJ files
import sys           # for getting command-line arguments

######################################################################
## The Brill Tagger
######################################################################

class BrillTagger(TaggerI):
    """
    Brill's transformational rule-based tagger.  Brill taggers use an
    X{initial tagger} (such as L{DefaultTagger}) to assign an intial
    tag sequence to a text; and then apply an ordered list of
    transformational rules to correct the tags of individual tokens.
    These transformation rules are specified by the L{BrillRuleI}
    interface.

    Brill taggers can be created directly, from an initial tagger and
    a list of transformational rules; but more often, Brill taggers
    are created by learning rules from a training corpus, using either
    L{BrillTaggerTrainer} or L{FastBrillTaggerTrainer}.
    """
    def __init__(self, initial_tagger, rules, **property_names):
        """
        @param initial_tagger: The initial tagger
        @type initial_tagger: L{TaggerI}
        @param rules: An ordered list of transformation rules that
            should be used to correct the initial tagging.
        @type rules: C{list} of L{BrillRuleI}
        """
        self._initial_tagger = initial_tagger
        self._rules = rules
        self._property_names = property_names

    def property(self, name):
        return self._property_names.get(name, name)

    def rules(self):
        return self._rules[:]

    def tag (self, token):
        # Inherit documentation from TaggerI
        
        SUBTOKENS = self.property('SUBTOKENS')
        TAG = self.property('TAG')

        # Run the initial tagger.
        self._initial_tagger.tag(token)
        subtokens = token[SUBTOKENS]

        # Create a dictionary that maps each tag to a list of the
        # indices of tokens that have that tag.
        tag_to_positions = {}
        for i, subtoken in enumerate(subtokens):
            if subtoken[TAG] not in tag_to_positions:
                tag_to_positions[subtoken[TAG]] = Set([i])
            else:
                tag_to_positions[subtoken[TAG]].add(i)

        # Apply each rule, in order.  Only try to apply rules at
        # positions that have the desired original tag.
        for rule in self._rules:
            # Find the positions where it might apply
            positions = tag_to_positions.get(rule.original_tag(), [])
            # Apply the rule at those positions.
            changed = rule.apply_at(subtokens, positions)
            # Update tag_to_positions with the positions of tags that
            # were modified.
            for i in changed:
                tag_to_positions[rule.original_tag()].remove(i)
                if rule.replacement_tag() not in tag_to_positions:
                    tag_to_positions[rule.replacement_tag()] = Set([i])
                else:
                    tag_to_positions[rule.replacement_tag()].add(i)

######################################################################
## Brill Rules
######################################################################

class BrillRuleI:
    """
    An interface for tag transformations on a tagged corpus, as
    performed by brill taggers.  Each transformation finds all tokens
    in the corpus that are tagged with a specific X{original tag} and
    satisfy a specific X{condition}, and replaces their tags with a
    X{replacement tag}.  For any given transformation, the original
    tag, replacement tag, and condition are fixed.  Conditions may
    depend on the token under consideration, as well as any other
    tokens in the corpus.

    Brill rules must be comparable and hashable.
    """    
    def apply_to(self, tokens):
        """
        Apply this rule everywhere it applies in the corpus.  I.e.,
        for each token in the corpus that is tagged with this rule's
        original tag, and that satisfies this rule's condition, set
        its tag to be this rule's replacement tag.

        @param tokens: The tagged corpus
        @type tokens: list of Token
        @return: The indices of tokens whose tags were changed by this
            rule.
        @rtype: C{list} of C{int}
        """
        return self.apply_at(tokens, range(len(tokens)))

    def apply_at(self, tokens, positions):
        """
        Apply this rule at every position in C{positions} where it
        applies to the corpus.  I.e., for each position M{p} in
        C{positions}, if C{tokens[M{p}]} is tagged with this rule's
        original tag, and satisfies this rule's condition, then set
        its tag to be this rule's replacement tag.

        @param tokens: The tagged corpus
        @type tokens: list of Token
        @type positions: C{list} of C{int}
        @param positions: The positions where the transformation is to
            be tried.
        @return: The indices of tokens whose tags were changed by this
            rule.
        @rtype: C{int}
        """
        assert False, "BrillRuleI is an abstract interface"

    def applies(self, tokens, index):
        """
        @return: True if the rule would change the tag of 
            C{tokens[index]}, False otherwise
        @rtype: Boolean

        @param tokens: A tagged corpus
        @type tokens: list of Token
        @param index: The index to check
        @type index: int
        """
        assert False, "BrillRuleI is an abstract interface"
        
    def original_tag(self):
        """
        @return: The tag which this C{BrillRuleI} may cause to be
        replaced.
        @rtype: any
        """
        assert False, "BrillRuleI is an abstract interface"

    def replacement_tag(self):
        """
        @return: the tag with which this C{BrillRuleI} may replace
        another tag.
        @rtype: any
        """
        assert False, "BrillRuleI is an abstract interface"

    # Rules must be comparable and hashable for the algorithm to work
    def __eq__(self):
        assert False, "Brill rules must be comparable"
    def __hash__(self):
        assert False, "Brill rules must be hashable"

class ProximateTokensRule(BrillRuleI):
    """
    An abstract base class for brill rules whose condition checks for
    the presence of tokens with given properties at given ranges of
    positions, relative to the token.

    Each subclass of proximate tokens brill rule defines a method
    M{extract_property}, which extracts a specific property from the
    the token, such as its text or tag.  Each instance is
    parameterized by a set of tuples, specifying ranges of positions
    and property values to check for in those ranges:
    
      - (M{start}, M{end}, M{value})

    The brill rule is then applicable to the M{n}th token iff:
    
      - The M{n}th token is tagged with the rule's original tag; and
      - For each (M{start}, M{end}, M{value}) triple:
        - The property value of at least one token between
          M{n+start} and M{n+end} (inclusive) is M{value}.

    For example, a proximate token brill template with M{start=end=-1}
    generates rules that check just the property of the preceding
    token.  Note that multiple properties may be included in a single
    rule; the rule applies if they all hold.

    @cvar PROPERTY_NAME: The name of the property that is checked
       by this brill rule.  This variable should be overridden by
       subclasses of C{ProximateTokensRule}.
    @type PROPERTY_NAME: C{string}
    """
    PROPERTY_NAME = None

    def __init__(self, original_tag, replacement_tag, *conditions):
        """

        Construct a new brill rule that changes a token's tag from
        C{original_tag} to C{replacement_tag} if all of the properties
        specified in C{conditions} hold.

        @type conditions: C{tuple} of C{(int, int, *)}
        @param conditions: A list of 3-tuples C{(start, end, value)},
            each of which specifies that the property of at least one
            token between M{n}+C{start} and M{n}+C{end} (inclusive) is
            C{value}.
        @raise ValueError: If C{start}>C{end} for any condition.
        """
        assert self.__class__ != ProximateTokensRule, \
               "ProximateTokensRule is an abstract base class"

        self._original = original_tag
        self._replacement = replacement_tag
        self._conditions = conditions
        for (s,e,v) in conditions:
            if s>e:
                raise ValueError('Condition %s has an invalid range' %
                                 ((s,e,v),))

    def extract_property(token): # [staticmethod]
        """
        Returns some property characterizing this token, such as its
        base lexical item or its tag.

        Each implentation of this method should correspond to an
        implementation of the method with the same name in a subclass
        of L{C{ProximateTokensTemplate}}.

        @param token: The token
        @type token: Token
        @return: The property
        @rtype: any
        """
        assert False, "ProximateTokensRule is an abstract interface"
    extract_property = staticmethod(extract_property)

    def apply_at(self, tokens, positions):
        # Inherit docs from BrillRuleI

        # Find all locations where the rule is applicable
        change = []
        for i in positions:
            if self.applies(tokens, i):
                change.append(i)

        # Make the changes.  Note: this must be done in a separate
        # step from finding applicable locations, since we don't want
        # the rule to interact with itself.
        for i in change:
            tokens[i]['TAG'] = self._replacement
        
        return change

    def applies(self, tokens, index):
        # Inherit docs from BrillRuleI
        
        # Does the given token have this rule's "original tag"?
        if tokens[index]['TAG'] != self._original:
            return False
        
        # Check to make sure that every condition holds.
        for (start, end, val) in self._conditions:
            # Find the (absolute) start and end indices.
            s = max(0, index+start)
            e = min(index+end+1, len(tokens))
            
            # Look for *any* token that satisfies the condition.
            for i in range(s, e):
                if self.extract_property(tokens[i]) == val:
                    break
            else:
                # No token satisfied the condition; return false.
                return False

        # Every condition checked out, so the rule is applicable.
        return True

    def original_tag(self):
        # Inherit docs from BrillRuleI
        return self._original

    def replacement_tag(self):
        # Inherit docs from BrillRuleI
        return self._replacement

    def __eq__(self, other):
        return (other != None and 
                other.__class__ == self.__class__ and 
                self._original == other._original and 
                self._replacement == other._replacement and 
                self._conditions == other._conditions)

    def __hash__(self):
        # Needs to include extract_property in order to distinguish subclasses
        # A nicer way would be welcome.
        return hash( (self._original, self._replacement, self._conditions,
                      self.extract_property.func_code) )

    def __repr__(self):
        conditions = ' and '.join(['%s in %d...%d' % (v,s,e)
                                   for (s,e,v) in self._conditions])
        return '<%s: %s->%s if %s>' % (self.__class__.__name__,
                                       self._original, self._replacement,
                                       conditions)

    def __str__(self):
        replacement = '%s -> %s' % (self._original,
                                              self._replacement)
        if len(self._conditions) == 0:
            conditions = ''
        else:
            conditions = ' if '+ ', and '.join([self._condition_to_str(c)
                                               for c in self._conditions])
        return replacement+conditions
    
    def _condition_to_str(self, condition):
        """
        Return a string representation of the given condition.
        This helper method is used by L{__str__}.
        """
        (start, end, value) = condition
        return ('the %s of %s is %r' %
                (self.PROPERTY_NAME, self._range_to_str(start, end), value))

    def _range_to_str(self, start, end):
        """
        Return a string representation for the given range.  This
        helper method is used by L{__str__}.
        """
        if start == end == 0:
            return 'this word'
        if start == end == -1:
            return 'the preceding word'
        elif start == end == 1:
            return 'the following word'
        elif start == end and start < 0:
            return 'word i-%d' % -start
        elif start == end and start > 0:
            return 'word i+%d' % start
        else:
            if start >= 0: start = '+%d' % start
            if end >= 0: end = '+%d' % end
            return 'words i%s...i%s' % (start, end)

class ProximateTagsRule(ProximateTokensRule):
    """
    A rule which examines the tags of nearby tokens.
    @see: superclass L{C{ProximateTokensRule}} for details.
    @see: L{ProximateTagsTemplate}, which generates these rules.
    """
    PROPERTY_NAME = 'tag' # for printing.
    def extract_property(token): # [staticmethod]
        """@return: The given token's C{TAG} property."""
        return token['TAG']
    extract_property = staticmethod(extract_property)

class ProximateWordsRule(ProximateTokensRule):
    """
    A rule which examines the base types of nearby tokens.
    @see: L{C{ProximateTokensRule}} for details.
    @see: L{ProximateWordsTemplate}, which generates these rules.
    """
    PROPERTY_NAME = 'text' # for printing.
    def extract_property(token): # [staticmethod]
        """@return: The given token's C{TEXT} property."""
        return token['TEXT']
    extract_property = staticmethod(extract_property)

######################################################################
## Brill Templates
######################################################################

class BrillTemplateI:
    """
    An interface for generating lists of transformational rules that
    apply at given corpus positions.  C{BrillTemplateI} is used by the
    C{BrillTagger} training algorithms to generate candidate rules.
    """
    def __init__(self):
        raise AssertionError, "BrillTemplateI is an abstract interface"

    def applicable_rules(self, token, i, correctTag):
        """
        Return a list of the transformational rules that would correct
        the C{i}th subtoken's tag in the given token.  In particular,
        return a list of zero or more rules that would change
        C{token['SUBTOKENS'][i]['TAG']} to C{correctTag}, if applied
        to C{token}.

        If the C{i}th subtoken already has the correct tag (i.e., if
        C{token['SUBTOKENS'][i]['TAG']} == C{correctTag}), then
        C{applicable_rules} should return the empty list.
        
        @param token: The token whose subtokens are being tagged.
        @type token: L{Token}
        @param i: The index of the subtoken whose tag should be
             corrected.
        @type i: C{int}
        @param correctTag: The correct tag for the C{i}th subtoken of
            C{token}.
        @type correctTag: (any)
        @rtype: C{list} of L{BrillRuleI}
        """
        raise AssertionError, "BrillTemplateI is an abstract interface"
    
    def get_neighborhood(self, token, index):
        """
        Returns the set of indices C{i} such that
        C{applicable_rules(token, index, ...)} depends on the value of
        the C{i}th subtoken of C{token}.

        This method is used by the \"fast\" BrillTagger trainer.

        @param token: The token whose subtokens are being tagged.
        @type token: L{Token}
        @param i: The index whose neighborhood should be returned.
        @type i: C{int}
        @rtype: C{Set}
        """
        raise AssertionError, "BrillTemplateI is an abstract interface"
    
class ProximateTokensTemplate(BrillTemplateI):
    """
    An brill templates that generates a list of
    L{ProximateTokensRule}s that apply at a given corpus
    position.  In particular, each C{ProximateTokensTemplate} is
    parameterized by a proximate token brill rule class and a list of
    boundaries, and generates all rules that:
    
      - use the given brill rule class
      - use the given list of boundaries as the C{start} and C{end}
        points for their conditions
      - are applicable to the given token.
    """
    def __init__(self, rule_class, *boundaries):
        """
        Construct a template for generating proximate token brill
        rules.

        @type rule_class: C{class}
        @param rule_class: The proximate token brill rule class that
        should be used to generate new rules.  This class must be a
        subclass of L{ProximateTokensRule}.
        @type boundaries: C{tuple} of C{(int, int)}
        @param boundaries: A list of tuples C{(start, end)}, each of
            which specifies a range for which a condition should be
            created by each rule.
        @raise ValueError: If C{start}>C{end} for any boundary.
        """
        self._rule_class = rule_class
        self._boundaries = boundaries
        for (s,e) in boundaries:
            if s>e:
                raise ValueError('Boundary %s has an invalid range' %
                                 ((s,e),))

    def applicable_rules(self, tokens, index, correct_tag):
        if tokens[index]['TAG'] == correct_tag:
            return []

        # For each of this template's boundaries, Find the conditions
        # that are applicable for the given token.
        applicable_conditions = \
             [self._applicable_conditions(tokens, index, start, end)
              for (start, end) in self._boundaries]
            
        # Find all combinations of these applicable conditions.  E.g.,
        # if applicable_conditions=[[A,B], [C,D]], then this will
        # generate [[A,C], [A,D], [B,C], [B,D]].
        condition_combos = [[]]
        for conditions in applicable_conditions:
            condition_combos = [old_conditions+[new_condition]
                                for old_conditions in condition_combos
                                for new_condition in conditions]

        # Translate the condition sets into rules.
        return [self._rule_class(tokens[index]['TAG'], correct_tag, *conds)
                for conds in condition_combos]

    def _applicable_conditions(self, tokens, index, start, end):
        """
        @return: A set of all conditions for proximate token rules
        that are applicable to C{tokens[index]}, given boundaries of
        C{(start, end)}.  I.e., return a list of all tuples C{(start,
        end, M{value})}, such the property value of at least one token
        between M{index+start} and M{index+end} (inclusive) is
        M{value}.
        """
        conditions = Set()
        s = max(0, index+start)
        e = min(index+end+1, len(tokens))
        for i in range(s, e):
            value = self._rule_class.extract_property(tokens[i])
            conditions.add( (start, end, value) )
        return conditions

    def get_neighborhood(self, tokens, index):
        # inherit docs from BrillTemplateI
        neighborhood = Set([index])
        for (start, end) in self._boundaries:
            s = max(0, index+start)
            e = min(index+end+1, len(tokens))
            for i in range(s, e):
                neighborhood.add(i)

        return neighborhood

class SymmetricProximateTokensTemplate(BrillTemplateI):
    """
    Simulates two L{ProximateTokensTemplate}s which are symmetric
    across the location of the token.  For rules of the form \"If the
    M{n}th token is tagged C{A}, and any tag preceding B{or} following
    the M{n}th token by a distance between M{x} and M{y} is C{B}, and
    ... , then change the tag of the nth token from C{A} to C{C}.\"

    One C{ProximateTokensTemplate} is formed by passing in the
    same arguments given to this class's constructor: tuples
    representing intervals in which a tag may be found.  The other
    C{ProximateTokensTemplate} is constructed with the negative
    of all the arguments in reversed order.  For example, a
    C{SymmetricProximateTokensTemplate} using the pair (-2,-1) and the
    constructor C{ProximateTagsTemplate} generates the same rules as a
    C{ProximateTagsTemplate} using (-2,-1) plus a second
    C{ProximateTagsTemplate} using (1,2).

    This is useful because we typically don't want templates to
    specify only \"following\" or only \"preceding\"; we'd like our
    rules to be able to look in either direction.
    """
    def __init__(self, rule_class, *boundaries):
        """
        Construct a template for generating proximate token brill
        rules.
        
        @type rule_class: C{class}
        @param rule_class: The proximate token brill rule class that
        should be used to generate new rules.  This class must be a
        subclass of L{ProximateTokensRule}.
        @type boundaries: C{tuple} of C{(int, int)}
        @param boundaries: A list of tuples C{(start, end)}, each of
            which specifies a range for which a condition should be
            created by each rule.
        @raise ValueError: If C{start}>C{end} for any boundary.
        """
        self._ptt1 = ProximateTokensTemplate(rule_class, *boundaries)
        reversed = [(-e,-s) for (s,e) in boundaries]
        self._ptt2 = ProximateTokensTemplate(rule_class, *reversed)

    # Generates lists of a subtype of ProximateTokensRule.
    def applicable_rules(self, tokens, index, correctTag):
        """
        See L{BrillTemplateI} for full specifications.

        @rtype: list of ProximateTokensRule
        """
        return (self._ptt1.applicable_rules(tokens, index, correctTag) +
                self._ptt2.applicable_rules(tokens, index, correctTag))

    def get_neighborhood(self, tokens, index):
        # inherit docs from BrillTemplateI
        n1 = self._ptt1.get_neighborhood(tokens, index)
        n2 = self._ptt2.get_neighborhood(tokens, index)
        return n1.union(n2)

######################################################################
## Brill Tagger Trainer
######################################################################

class BrillTaggerTrainer:
    """
    A trainer for brill taggers.
    """
    def __init__(self, initial_tagger, templates, trace=0,
                 **property_names):
        self._initial_tagger = initial_tagger
        self._templates = templates
        self._trace = trace
        self._property_names = property_names

    def property(self, name):
        return self._property_names.get(name, name)

    #////////////////////////////////////////////////////////////
    # Training
    #////////////////////////////////////////////////////////////

    def train(self, train_token, max_rules=200, min_score=2):
        """
        Trains the BrillTagger on the corpus C{train_token},
        producing at most C{max_rules} transformations, each of which
        reduces the net number of errors in the corpus by at least
        C{min_score}.
        
        @type train_token: C{list} of L{Token}
        @param train_token: The corpus of tagged C{Tokens}
        @type max_rules: C{int}
        @param max_rules: The maximum number of transformations to be created
        @type min_score: C{int}
        @param min_score: The minimum acceptable net error reduction
            that each transformation must produce in the corpus.
        """
        SUBTOKENS = self.property('SUBTOKENS')
        TAG = self.property('TAG')
        if self._trace > 0: print ("Training Brill tagger on %d tokens..." %
                                   len(train_token[SUBTOKENS]))

        # Create a new copy of the training token, and run the initial
        # tagger on this.  We will progressively update this test
        # token to look more like the training token.
        test_token = train_token.exclude(TAG)
        self._initial_tagger.tag(test_token)
        
        test_subtoks = test_token[SUBTOKENS]
        train_subtoks = train_token[SUBTOKENS]

        if self._trace > 2: self._trace_header()
            
        # Look for useful rules.
        rules = []
        try:
            while len(rules) < max_rules:
                old_tags = [t[TAG] for t in test_subtoks]
                (rule, score, fixscore) = self._best_rule(test_subtoks,
                                                          train_subtoks)
                if rule is None or score < min_score:
                    if self._trace > 1:
                        print 'Insufficient improvement; stopping'
                    break
                else:
                    # Add the rule to our list of rules.
                    rules.append(rule)
                    # Use the rules to update the test token.
                    k = rule.apply_to(test_subtoks)
                    # Display trace output.
                    if self._trace > 1:
                        self._trace_rule(rule, score, fixscore, len(k))
        # The user can also cancel training manually:
        except KeyboardInterrupt: pass

        # Create and return a tagger from the rules we found.
        return BrillTagger(self._initial_tagger, rules)

    #////////////////////////////////////////////////////////////
    # Finding the best rule
    #////////////////////////////////////////////////////////////

    # Finds the rule that makes the biggest net improvement in the corpus.
    # Returns a (rule, score) pair.
    def _best_rule(self, test_subtoks, train_subtoks):
        SUBTOKENS = self.property('SUBTOKENS')
        TAG = self.property('TAG')

        # Create a dictionary mapping from each tag to a list of the
        # indices that have that tag in both test_subtoks and
        # train_subtoks (i.e., where it is correctly tagged).
        correct_indices = {}
        for i in range(len(test_subtoks)):
            if test_subtoks[i][TAG] == train_subtoks[i][TAG]:
                tag = test_subtoks[i][TAG]
                correct_indices.setdefault(tag, []).append(i)

        # Find all the rules that correct at least one token's tag,
        # and the number of tags that each rule corrects (in
        # descending order of number of tags corrected).
        rules = self._find_rules(test_subtoks, train_subtoks)

        # Keep track of the current best rule, and its score.
        best_rule, best_score, best_fixscore = None, 0, 0

        # Consider each rule, in descending order of fixscore (the
        # number of tags that the rule corrects, not including the
        # number that it breaks).
        for (rule, fixscore) in rules:
            # The actual score must be <= fixscore; so if best_score
            # is bigger than fixscore, then we already have the best
            # rule.
            if best_score >= fixscore:
                return best_rule, best_score, best_fixscore

            # Calculate the actual score, by decrementing fixscore
            # once for each tag that the rule changes to an incorrect
            # value.
            score = fixscore
            for i in correct_indices[rule.original_tag()]:
                if rule.applies(test_subtoks, i):
                    score -= 1
                    # If the score goes below best_score, then we know
                    # that this isn't the best rule; so move on:
                    if score <= best_score: break

            #print '%5d %5d %s' % (fixscore, score, rule)

            # If the actual score is better than the best score, then
            # update best_score and best_rule.
            if score > best_score:
                best_rule, best_score, best_fixscore = rule, score, fixscore

        # Return the best rule, and its score.
        return best_rule, best_score, best_fixscore

    def _find_rules(self, test_subtoks, train_subtoks):
        """
        Find all rules that correct at least one token's tag in
        C{test_subtoks}.

        @return: A list of tuples C{(rule, fixscore)}, where C{rule}
            is a brill rule and C{fixscore} is the number of tokens
            whose tag the rule corrects.  Note that C{fixscore} does
            I{not} include the number of tokens whose tags are changed
            to incorrect values.        
        """
        TAG = self.property('TAG')

        # Create a list of all indices that are incorrectly tagged.
        error_indices = [i for i in range(len(test_subtoks))
                         if (test_subtoks[i][TAG] !=
                             train_subtoks[i][TAG])]

        # Create a dictionary mapping from rules to their positive-only
        # scores.
        rule_score_dict = {}
        for i in range(len(test_subtoks)):
            rules = self._find_rules_at(test_subtoks, train_subtoks, i)
            for rule in rules:
                rule_score_dict[rule] = rule_score_dict.get(rule,0) + 1

        # Convert the dictionary into a list of (rule, score) tuples,
        # sorted in descending order of score.
        rule_score_items = rule_score_dict.items()
        temp = [(-score, rule) for (rule, score) in rule_score_items]
        temp.sort()
        return [(rule, -negscore) for (negscore, rule) in temp]

    def _find_rules_at(self, test_subtoks, train_subtoks, i):
        """
        @type: C{list} of C{Set}
        @return: the set of all rules (based on the templates) that
        correct token C{i}'s tag in C{test_subtoks}.
        """
        TAG = self.property('TAG')
        
        applicable_rules = Set()
        if test_subtoks[i][TAG] != train_subtoks[i][TAG]:
            correct_tag = train_subtoks[i][TAG]
            for template in self._templates:
                new_rules = template.applicable_rules(test_subtoks, i,
                                                      correct_tag)
                applicable_rules.update(new_rules)
                
        return applicable_rules

    #////////////////////////////////////////////////////////////
    # Tracing
    #////////////////////////////////////////////////////////////

    def _trace_header(self):
        print """
           B      |     
   S   F   r   O  |        Score = Fixed - Broken
   c   i   o   t  |  R     Fixed = num tags changed incorrect -> correct
   o   x   k   h  |  u    Broken = num tags changed correct -> incorrect
   r   e   e   e  |  l     Other = num tags changed incorrect -> incorrect
   e   d   n   r  |  e
------------------+-------------------------------------------------------
        """.rstrip()

    def _trace_rule(self, rule, score, fixscore, numchanges):
        if self._trace > 2:
            print ('%4d%4d%4d%4d ' % (score, fixscore, fixscore-score,
                                      numchanges-fixscore*2+score)), '|',
        print rule

######################################################################
## Fast Brill Tagger Trainer
######################################################################

class FastBrillTaggerTrainer:
    """
    A faster trainer for brill taggers.
    """
    def __init__(self, initial_tagger, templates, trace=0,
                 **property_names):
        self._initial_tagger = initial_tagger
        self._templates = templates
        self._trace = trace
        self._property_names = property_names

    def property(self, name):
        return self._property_names.get(name, name)

    #////////////////////////////////////////////////////////////
    # Training
    #////////////////////////////////////////////////////////////

    def train(self, train_token, max_rules=200, min_score=2):
        SUBTOKENS = self.property('SUBTOKENS')
        TAG = self.property('TAG')

        # If TESTING is true, extra computation is done to determine whether
        # each "best" rule actually reduces net error by the score it received.
        TESTING = False
        
        # Basic idea: Keep track of the rules that apply at each position.
        # And keep track of the positions to which each rule applies.

        # The set of somewhere-useful rules that apply at each position
        rulesByPosition = []
        for i in range(len(train_token[SUBTOKENS])):
            rulesByPosition.append(Set())

        # Mapping somewhere-useful rules to the positions where they apply.
        # Then maps each position to the score change the rule generates there.
        # (always -1, 0, or 1)
        positionsByRule = {}

        # Map scores to sets of rules known to achieve *at most* that score.
        rulesByScore = {0:{}}
        # Conversely, map somewhere-useful rules to their minimal scores.
        ruleScores = {}

        tagIndices = {}   # Lists of indices, mapped to by their tags

        # Maps rules to the first index in the corpus where it may not be known
        # whether the rule applies.  (Rules can't be chosen for inclusion
        # unless this value = len(corpus).  But most rules are bad, and
        # we won't need to check the whole corpus to know that.)
        # Some indices past this may actually have been checked; it just isn't
        # guaranteed.
        firstUnknownIndex = {}

        # Make entries in the rule-mapping dictionaries.
        # Should be called before _updateRuleApplies.
        def _initRule (rule):
            positionsByRule[rule] = {}
            rulesByScore[0][rule] = None
            ruleScores[rule] = 0
            firstUnknownIndex[rule] = 0

        # Takes a somewhere-useful rule which applies at index i;
        # Updates all rule data to reflect that the rule so applies.
        def _updateRuleApplies (rule, i):

            # If the rule is already known to apply here, ignore.
            # (This only happens if the position's tag hasn't changed.)
            if positionsByRule[rule].has_key(i):
                return

            if rule.replacement_tag() == train_token[SUBTOKENS][i][TAG]:
                positionsByRule[rule][i] = 1
            elif rule.original_tag() == train_token[SUBTOKENS][i][TAG]:
                positionsByRule[rule][i] = -1
            else: # was wrong, remains wrong
                positionsByRule[rule][i] = 0

            # Update rules in the other dictionaries
            del rulesByScore[ruleScores[rule]][rule]
            ruleScores[rule] += positionsByRule[rule][i]
            if not rulesByScore.has_key(ruleScores[rule]):
                rulesByScore[ruleScores[rule]] = {}
            rulesByScore[ruleScores[rule]][rule] = None
            rulesByPosition[i].add(rule)

        # Takes a rule which no longer applies at index i;
        # Updates all rule data to reflect that the rule doesn't apply.
        def _updateRuleNotApplies (rule, i):
            del rulesByScore[ruleScores[rule]][rule]
            ruleScores[rule] -= positionsByRule[rule][i]
            if not rulesByScore.has_key(ruleScores[rule]):
                rulesByScore[ruleScores[rule]] = {}
            rulesByScore[ruleScores[rule]][rule] = None

            del positionsByRule[rule][i]
            rulesByPosition[i].remove(rule)
            # Optional addition: if the rule now applies nowhere, delete
            # all its dictionary entries.

        myToken = train_token.exclude(TAG)
        self._initial_tagger.tag(myToken)
        tokens = myToken[SUBTOKENS] # [XX] ??????

        # First sort the corpus by tag, and also note where the errors are.
        errorIndices = []  # only used in initialization
        for i in range(len(myToken[SUBTOKENS])):
            tag = myToken[SUBTOKENS][i][TAG]
            if tag != train_token[SUBTOKENS][i][TAG]:
                errorIndices.append(i)
            if not tagIndices.has_key(tag):
                tagIndices[tag] = []
            tagIndices[tag].append(i)

        print "Finding useful rules..."
        # Collect all rules that fix any errors, with their positive scores.
        for i in errorIndices:
            for template in self._templates:
                # Find the templated rules that could fix the error.
                for rule in template.applicable_rules(myToken[SUBTOKENS], i,
                                                    train_token[SUBTOKENS][i][TAG]):
                    if not positionsByRule.has_key(rule):
                        _initRule(rule)
                    _updateRuleApplies(rule, i)

        print "Done initializing %i useful rules." %len(positionsByRule)

        if TESTING:
            after = -1 # bug-check only

        # Each iteration through the loop tries a new maxScore.
        maxScore = max(rulesByScore.keys())
        rules = []
        while len(rules) < max_rules and maxScore >= min_score:

            # Find the next best rule.  This is done by repeatedly taking a rule with
            # the highest score and stepping through the corpus to see where it
            # applies.  When it makes an error (decreasing its score) it's bumped
            # down, and we try a new rule with the highest score.
            # When we find a rule which has the highest score AND which has been
            # tested against the entire corpus, we can conclude that it's the next
            # best rule.

            bestRule = None
            bestRules = rulesByScore[maxScore].keys()

            for rule in bestRules:
                # Find the first relevant index at or following the first
                # unknown index.  (Only check indices with the right tag.)
                ti = bisect.bisect_left(tagIndices[rule.original_tag()],
                                        firstUnknownIndex[rule])
                for nextIndex in tagIndices[rule.original_tag()][ti:]:
                    if rule.applies(myToken[SUBTOKENS], nextIndex):
                        _updateRuleApplies(rule, nextIndex)
                        if ruleScores[rule] < maxScore:
                            firstUnknownIndex[rule] = nextIndex+1
                            break  # the _update demoted the rule

                # If we checked all remaining indices and found no more errors:
                if ruleScores[rule] == maxScore:
                    firstUnknownIndex[rule] = len(tokens) # i.e., we checked them all
                    print "%i) %s (score: %i)" %(len(rules)+1, rule, maxScore)
                    bestRule = rule
                    break
                
            if bestRule == None: # all rules dropped below maxScore
                del rulesByScore[maxScore]
                maxScore = max(rulesByScore.keys())
                continue  # with next-best rules

            # bug-check only
            if TESTING:
                before = len(_errorPositions(tokens, train_tokens))
                print "There are %i errors before applying this rule." %before
                assert after == -1 or before == after, \
                        "after=%i but before=%i" %(after,before)
                        
            print "Applying best rule at %i locations..." \
                    %len(positionsByRule[bestRule].keys())
            
            # If we reach this point, we've found a new best rule.
            # Apply the rule at the relevant sites.
            # (apply_at is a little inefficient here, since we know the rule applies
            #  and don't actually need to test it again.)
            rules.append(bestRule)
            bestRule.apply_at(tokens, positionsByRule[bestRule].keys())

            # Update the tag index accordingly.
            for i in positionsByRule[bestRule].keys(): # where it applied
                # Update positions of tags
                # First, find and delete the index for i from the old tag.
                oldIndex = bisect.bisect_left(tagIndices[bestRule.original_tag()], i)
                del tagIndices[bestRule.original_tag()][oldIndex]

                # Then, insert i into the index list of the new tag.
                if not tagIndices.has_key(bestRule.replacement_tag()):
                    tagIndices[bestRule.replacement_tag()] = []
                newIndex = bisect.bisect_left(tagIndices[bestRule.replacement_tag()], i)
                tagIndices[bestRule.replacement_tag()].insert(newIndex, i)

            # This part is tricky.
            # We need to know which sites might now require new rules -- that
            # is, which sites are close enough to the changed site so that
            # a template might now generate different rules for it.
            # Only the templates can know this.
            #
            # If a template now generates a different set of rules, we have
            # to update our indices to reflect that.
            print "Updating neighborhoods of changed sites.\n" 

            # First, collect all the indices that might get new rules.
            neighbors = Set()
            for i in positionsByRule[bestRule].keys(): # sites changed
                for template in self._templates:
                    neighbors.update(template.get_neighborhood(myToken[SUBTOKENS], i))

            # Then collect the new set of rules for each such index.
            c = d = e = 0
            for i in neighbors:
                siteRules = Set()
                for template in self._templates:
                    # Get a set of the rules that the template now generates
                    siteRules.update(Set(template.applicable_rules(
                                        myToken[SUBTOKENS], i, train_token[SUBTOKENS][i][TAG])))

                # Update rules no longer generated here by any template
                for obsolete in rulesByPosition[i] - siteRules:
                    c += 1
                    _updateRuleNotApplies(obsolete, i)

                # Update rules only now generated by this template
                for newRule in siteRules - rulesByPosition[i]:
                    d += 1
                    if not positionsByRule.has_key(newRule):
                        e += 1
                        _initRule(newRule) # make a new rule w/score=0
                    _updateRuleApplies(newRule, i) # increment score, etc.

            if TESTING:
                after = before - maxScore
            print "%i obsolete rule applications, %i new ones, " %(c,d)+ \
                    "using %i previously-unseen rules." %e        

            maxScore = max(rulesByScore.keys()) # may have gone up

        
        if self._trace > 0: print ("Training Brill tagger on %d tokens..." %
                                   len(train_token[SUBTOKENS]))
        
        # Maintain a list of the rules that apply at each position.
        rules_by_position = [{} for tok in train_token[SUBTOKENS]]

        # Create and return a tagger from the rules we found.
        return BrillTagger(self._initial_tagger, rules)

######################################################################
## Testing
######################################################################

def _errorPositions (train_token, token):
    return [i for i in range(len(token['SUBTOKENS'])) 
            if token['SUBTOKENS'][i]['TAG'] !=
            train_token['SUBTOKENS'][i]['TAG'] ]

# returns a list of errors in string format
def errorList (train_token, token, radius=2):
    """
    Returns a list of human-readable strings indicating the errors in the
    given tagging of the corpus.

    @param train_token: The correct tagging of the corpus
    @type train_token: Token
    @param tokens: The tagged corpus
    @type tokens: list of Token
    @param radius: How many tokens on either side of a wrongly-tagged token
        to include in the error string.  For example, if C{radius}=2, each error
        string will show the incorrect token plus two tokens on either side.
    @type radius: int
    """
    errors = []
    indices = _errorPositions(train_token, token)
    tokenLen = len(token['SUBTOKENS'])
    for i in indices:
        ei = token['SUBTOKENS'][i]['TAG'].rjust(3) + " -> " \
             + train_token['SUBTOKENS'][i]['TAG'].rjust(3) + ":  "
        for j in range( max(i-radius, 0), min(i+radius+1, tokenLen) ):
            if token['SUBTOKENS'][j]['TEXT'] == token['SUBTOKENS'][j]['TAG']:
                s = token['SUBTOKENS'][j]['TEXT'] # don't print punctuation tags
            else:
                s = token['SUBTOKENS'][j]['TEXT'] + "/" + token['SUBTOKENS'][j]['TAG']
                
            if j == i:
                ei += "**"+s+"** "
            else:
                ei += s + " "
        errors.append(ei)

    return errors

def getWSJTokens (n, randomize = False):
    """
    Returns a list of the tagged C{Token}s in M{n} files of the Wall Street
    Journal corpus.

    @param n: How many files to get C{Token}s from; if there are more than
        M{n} files in the corpus, all tokens are returned.
    @type n: int
    @param randomize: C{False} means the tokens are from the first M{n} files
        of the corpus.  C{True} means the tokens are from a random set of M{n}
        files.
    @type randomize: Boolean
    @return: The list of tagged tokens
    @rtype: list of C{Token}
    """
    taggedData = []
    items = treebank.items('tagged')
    if randomize:
        random.seed(len(items))
        random.shuffle(items)
    for item in items[:n]:
        taggedData += treebank.tokenize(item)['SUBTOKENS']
    taggedData = [taggedData[i] for i in range(len(taggedData))
                  if taggedData[i]['TEXT'][0] not in "[]="]
    return taggedData

def test(numFiles=100, max_rules=200, min_score=2, ruleFile="dump.rules",
         errorOutput = "errors.out", ruleOutput="rules.out",
         randomize=False, train=.8, trace=3):

    NN_CD_tagger = RegexpTagger([(r'^[0-9]+(.[0-9]+)?$', 'CD'),
                                             (r'.*', 'NN')])

    # train is the proportion of data used in training; the rest is reserved
    # for testing.

    print "Loading tagged data..."
    taggedData = getWSJTokens(numFiles, randomize)

    trainCutoff = int(len(taggedData)*train)
    trainingData = Token(SUBTOKENS=taggedData[0:trainCutoff])
    goldData = Token(SUBTOKENS=taggedData[trainCutoff:])
    testingData = goldData.exclude('TAG')

    # Unigram tagger

    print "Training unigram tagger:",
    u = UnigramTagger()
    u.train(trainingData)
    backoff = BackoffTagger([u, NN_CD_tagger])
    print("[accuracy: %f]"
          %tagger_accuracy(backoff, [goldData]))

    # Brill tagger

    templates = [
        SymmetricProximateTokensTemplate(ProximateTagsRule, (1,1)),
        SymmetricProximateTokensTemplate(ProximateTagsRule, (2,2)),
        SymmetricProximateTokensTemplate(ProximateTagsRule, (1,2)),
        SymmetricProximateTokensTemplate(ProximateTagsRule, (1,3)),
        SymmetricProximateTokensTemplate(ProximateWordsRule, (1,1)),
        SymmetricProximateTokensTemplate(ProximateWordsRule, (2,2)),
        SymmetricProximateTokensTemplate(ProximateWordsRule, (1,2)),
        SymmetricProximateTokensTemplate(ProximateWordsRule, (1,3)),
        ProximateTokensTemplate(ProximateTagsRule, (-1, -1), (1,1)),
        ProximateTokensTemplate(ProximateWordsRule, (-1, -1), (1,1)),
        ]

    trainer = FastBrillTaggerTrainer(backoff, templates, trace)
    b = trainer.train(trainingData, max_rules, min_score)

    print
    print("Brill accuracy: %f" % tagger_accuracy(b, [goldData]))

    print("\nRules: ")
    printRules = file(ruleOutput, 'w')
    for rule in b.rules():
        print(str(rule))
        printRules.write(str(rule)+"\n\n")
    #b.saveRules(ruleFile)

    b.tag(testingData)
    el = errorList(goldData, testingData)
    errorFile = file(errorOutput, 'w')

    for e in el:
        errorFile.write(e+"\n\n")
    errorFile.close()
    print("Done.")

# TESTING
#sys.argv = ['', '50', '0', '200', '1']
    
if __name__ == '__main__':
    args = sys.argv[1:]

    if len(args) == 0 or len(args) > 4:
        print "Usage: python brill.py n [randomize [max_rules [min_score]]]\n \
            n -> number of WSJ files to read\n \
            randomize -> 0 (default) means read the first n files in the corpus, \
                          1 means read a random set of n files \n \
            max_rules -> (default 200) generate at most this many rules during \
                             training \n \
            min_score -> (default 2) only use rules which decrease the number of \
                           errors in the training corpus by at least this much"
    else:
        args = map(int, args)
        if len(args) == 1:
            print("Using the first %i files.\n" %args[0])
            test(numFiles = args[0])
        elif len(args) == 2:
            print("Using %i files, randomize=%i\n" %tuple(args[:2]) )
            test(numFiles = args[0], randomize = args[1])
        elif len(args) == 3:
            print("Using %i files, randomize=%i, max_rules=%i\n" %tuple(args[:3]) )
            test(numFiles = args[0], randomize = args[1], max_rules = args[2])
        elif len(args) == 4:
            print("Using %i files, randomize=%i, max_rules=%i, min_score=%i\n"
                  %tuple(args[:4]) )
            test(numFiles = args[0], randomize = args[1], max_rules = args[2],
                 min_score = args[3])

        print("\nCheck errors.out for a listing of errors in the training set, "+
              "and rules.out for a list of the rules above.")
