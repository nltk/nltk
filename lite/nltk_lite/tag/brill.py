# Natural Language Toolkit: Brill Tagger
#
# Copyright (C) 2001-2005 University of Pennsylvania
# Authors: Christopher Maloof <cjmaloof@gradient.cis.upenn.edu>
#          Edward Loper <edloper@gradient.cis.upenn.edu>
#          Steven Bird <sb@ldc.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Brill's transformational rule-based tagger.
"""

from nltk_lite.tag import TagI

import bisect        # for binary search through a subset of indices
import os            # for finding WSJ files
import random        # for shuffling WSJ files
import sys           # for getting command-line arguments

######################################################################
## The Brill Tagger
######################################################################

class Brill(TagI):
    """
    Brill's transformational rule-based tagger.  Brill taggers use an
    X{initial tagger} (such as L{tag.Default}) to assign an intial
    tag sequence to a text; and then apply an ordered list of
    transformational rules to correct the tags of individual tokens.
    These transformation rules are specified by the L{BrillRuleI}
    interface.

    Brill taggers can be created directly, from an initial tagger and
    a list of transformational rules; but more often, Brill taggers
    are created by learning rules from a training corpus, using either
    L{BrillTrainer} or L{FastBrillTrainer}.
    """
    def __init__(self, initial_tagger, rules):
        """
        @param initial_tagger: The initial tagger
        @type initial_tagger: L{TagI}
        @param rules: An ordered list of transformation rules that
            should be used to correct the initial tagging.
        @type rules: C{list} of L{BrillRuleI}
        """
        self._initial_tagger = initial_tagger
        self._rules = rules

    def rules(self):
        return self._rules[:]

    def tag (self, tokens):
        # Inherit documentation from TagI
        
        # Run the initial tagger.
        tagged_tokens = list(self._initial_tagger.tag(tokens))

        # Create a dictionary that maps each tag to a list of the
        # indices of tokens that have that tag.
        tag_to_positions = {}
        for i, (token, tag) in enumerate(tagged_tokens):
            if tag not in tag_to_positions:
                tag_to_positions[tag] = set([i])
            else:
                tag_to_positions[tag].add(i)

        # Apply each rule, in order.  Only try to apply rules at
        # positions that have the desired original tag.
        for rule in self._rules:
            # Find the positions where it might apply
            positions = tag_to_positions.get(rule.original_tag(), [])
            # Apply the rule at those positions.
            changed = rule.apply_at(tagged_tokens, positions)
            # Update tag_to_positions with the positions of tags that
            # were modified.
            for i in changed:
                tag_to_positions[rule.original_tag()].remove(i)
                if rule.replacement_tag() not in tag_to_positions:
                    tag_to_positions[rule.replacement_tag()] = set([i])
                else:
                    tag_to_positions[rule.replacement_tag()].add(i)
        for t in tagged_tokens:
            yield t

######################################################################
## Brill Rules
######################################################################

class BrillRuleI(object):
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
        @type tokens: C{list} of C{tuple}
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
    """

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
        of L{ProximateTokensTemplate}.

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
            (token, tag) = tokens[i]
            tokens[i] = (token, self._replacement)
        
        return change

    def applies(self, tokens, index):
        # Inherit docs from BrillRuleI
        
        # Does the given token have this rule's "original tag"?
        if tokens[index][1] != self._original:
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
    @see: superclass L{ProximateTokensRule} for details.
    @see: L{ProximateTagsTemplate}, which generates these rules.
    """
    PROPERTY_NAME = 'tag' # for printing.
    def extract_property(token): # [staticmethod]
        """@return: The given token's tag."""
        return token[1]
    extract_property = staticmethod(extract_property)

class ProximateWordsRule(ProximateTokensRule):
    """
    A rule which examines the base types of nearby tokens.
    @see: L{ProximateTokensRule} for details.
    @see: L{ProximateWordsTemplate}, which generates these rules.
    """
    PROPERTY_NAME = 'text' # for printing.
    def extract_property(token): # [staticmethod]
        """@return: The given token's text."""
        return token[0]
    extract_property = staticmethod(extract_property)

######################################################################
## Brill Templates
######################################################################

class BrillTemplateI(object):
    """
    An interface for generating lists of transformational rules that
    apply at given corpus positions.  C{BrillTemplateI} is used by
    C{Brill} training algorithms to generate candidate rules.
    """
    def __init__(self):
        raise AssertionError, "BrillTemplateI is an abstract interface"

    def applicable_rules(self, tokens, i, correctTag):
        """
        Return a list of the transformational rules that would correct
        the C{i}th subtoken's tag in the given token.  In particular,
        return a list of zero or more rules that would change
        C{tagged_tokens[i][1]} to C{correctTag}, if applied
        to C{token}.

        If the C{i}th subtoken already has the correct tag (i.e., if
        C{tagged_tokens[i][1]} == C{correctTag}), then
        C{applicable_rules} should return the empty list.
        
        @param token: The tagged tokens being tagged.
        @type token: C{list} of C{tuple}
        @param i: The index of the token whose tag should be corrected.
        @type i: C{int}
        @param correctTag: The correct tag for the C{i}th token.
        @type correctTag: (any)
        @rtype: C{list} of L{BrillRuleI}
        """
        raise AssertionError, "BrillTemplateI is an abstract interface"
    
    def get_neighborhood(self, token, index):
        """
        Returns the set of indices C{i} such that
        C{applicable_rules(token, index, ...)} depends on the value of
        the C{i}th subtoken of C{token}.

        This method is used by the \"fast\" Brill tagger trainer.

        @param token: The tokens being tagged.
        @type token: C{list} of C{tuple}
        @param index: The index whose neighborhood should be returned.
        @type index: C{int}
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
        if tokens[index][1] == correct_tag:
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
        return [self._rule_class(tokens[index][1], correct_tag, *conds)
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
        conditions = set()
        s = max(0, index+start)
        e = min(index+end+1, len(tokens))
        for i in range(s, e):
            value = self._rule_class.extract_property(tokens[i])
            conditions.add( (start, end, value) )
        return conditions

    def get_neighborhood(self, tokens, index):
        # inherit docs from BrillTemplateI
        neighborhood = set([index])
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

class BrillTrainer(object):
    """
    A trainer for brill taggers.
    """
    def __init__(self, initial_tagger, templates, trace=0):
        self._initial_tagger = initial_tagger
        self._templates = templates
        self._trace = trace

    #////////////////////////////////////////////////////////////
    # Training
    #////////////////////////////////////////////////////////////

    def train(self, train_tokens, max_rules=200, min_score=2):
        """
        Trains the Brill tagger on the corpus C{train_token},
        producing at most C{max_rules} transformations, each of which
        reduces the net number of errors in the corpus by at least
        C{min_score}.
        
        @type train_tokens: C{list} of L{tuple}
        @param train_tokens: The corpus of tagged tokens
        @type max_rules: C{int}
        @param max_rules: The maximum number of transformations to be created
        @type min_score: C{int}
        @param min_score: The minimum acceptable net error reduction
            that each transformation must produce in the corpus.
        """
        if self._trace > 0: print ("Training Brill tagger on %d tokens..." %
                                   len(train_tokens))

        # Create a new copy of the training token, and run the initial
        # tagger on this.  We will progressively update this test
        # token to look more like the training token.

        test_tokens = list(self._initial_tagger.tag(t[0] for t in train_tokens))
        
        if self._trace > 2: self._trace_header()
            
        # Look for useful rules.
        rules = []
        try:
            while len(rules) < max_rules:
                old_tags = [t[1] for t in test_tokens]
                (rule, score, fixscore) = self._best_rule(test_tokens,
                                                          train_tokens)
                if rule is None or score < min_score:
                    if self._trace > 1:
                        print 'Insufficient improvement; stopping'
                    break
                else:
                    # Add the rule to our list of rules.
                    rules.append(rule)
                    # Use the rules to update the test token.
                    k = rule.apply_to(test_tokens)
                    # Display trace output.
                    if self._trace > 1:
                        self._trace_rule(rule, score, fixscore, len(k))
        # The user can also cancel training manually:
        except KeyboardInterrupt: pass

        # Create and return a tagger from the rules we found.
        return Brill(self._initial_tagger, rules)

    #////////////////////////////////////////////////////////////
    # Finding the best rule
    #////////////////////////////////////////////////////////////

    # Finds the rule that makes the biggest net improvement in the corpus.
    # Returns a (rule, score) pair.
    def _best_rule(self, test_tokens, train_tokens):

        # Create a dictionary mapping from each tag to a list of the
        # indices that have that tag in both test_tokens and
        # train_tokens (i.e., where it is correctly tagged).
        correct_indices = {}
        for i in range(len(test_tokens)):
            if test_tokens[i][1] == train_tokens[i][1]:
                tag = test_tokens[i][1]
                correct_indices.setdefault(tag, []).append(i)

        # Find all the rules that correct at least one token's tag,
        # and the number of tags that each rule corrects (in
        # descending order of number of tags corrected).
        rules = self._find_rules(test_tokens, train_tokens)

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
            if correct_indices.has_key(rule.original_tag()):
                for i in correct_indices[rule.original_tag()]:
                    if rule.applies(test_tokens, i):
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

    def _find_rules(self, test_tokens, train_tokens):
        """
        Find all rules that correct at least one token's tag in
        C{test_tokens}.

        @return: A list of tuples C{(rule, fixscore)}, where C{rule}
            is a brill rule and C{fixscore} is the number of tokens
            whose tag the rule corrects.  Note that C{fixscore} does
            I{not} include the number of tokens whose tags are changed
            to incorrect values.        
        """

        # Create a list of all indices that are incorrectly tagged.
        error_indices = [i for i in range(len(test_tokens))
                         if (test_tokens[i][1] !=
                             train_tokens[i][1])]

        # Create a dictionary mapping from rules to their positive-only
        # scores.
        rule_score_dict = {}
        for i in range(len(test_tokens)):
            rules = self._find_rules_at(test_tokens, train_tokens, i)
            for rule in rules:
                rule_score_dict[rule] = rule_score_dict.get(rule,0) + 1

        # Convert the dictionary into a list of (rule, score) tuples,
        # sorted in descending order of score.
        rule_score_items = rule_score_dict.items()
        temp = [(-score, rule) for (rule, score) in rule_score_items]
        temp.sort()
        return [(rule, -negscore) for (negscore, rule) in temp]

    def _find_rules_at(self, test_tokens, train_tokens, i):
        """
        @rtype: C{Set}
        @return: the set of all rules (based on the templates) that
        correct token C{i}'s tag in C{test_tokens}.
        """
        
        applicable_rules = set()
        if test_tokens[i][1] != train_tokens[i][1]:
            correct_tag = train_tokens[i][1]
            for template in self._templates:
                new_rules = template.applicable_rules(test_tokens, i,
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
   o   x   k   h  |  u     Broken = num tags changed correct -> incorrect
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

class FastBrillTrainer(object):
    """
    A faster trainer for brill taggers.
    """
    def __init__(self, initial_tagger, templates, trace=0):
        self._initial_tagger = initial_tagger
        self._templates = templates
        self._trace = trace

    #////////////////////////////////////////////////////////////
    # Training
    #////////////////////////////////////////////////////////////

    def train(self, train_tokens, max_rules=200, min_score=2):

        # If TESTING is true, extra computation is done to determine whether
        # each "best" rule actually reduces net error by the score it received.
        TESTING = False
        
        # Basic idea: Keep track of the rules that apply at each position.
        # And keep track of the positions to which each rule applies.

        # The set of somewhere-useful rules that apply at each position
        rulesByPosition = []
        for i in range(len(train_tokens)):
            rulesByPosition.append(set())

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

            if rule.replacement_tag() == train_tokens[i][1]:
                positionsByRule[rule][i] = 1
            elif rule.original_tag() == train_tokens[i][1]:
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

        tagged_tokens = list(self._initial_tagger.tag(t[0] for t in train_tokens))

        # First sort the corpus by tag, and also note where the errors are.
        errorIndices = []  # only used in initialization
        for i in range(len(tagged_tokens)):
            tag = tagged_tokens[i][1]
            if tag != train_tokens[i][1]:
                errorIndices.append(i)
            if not tagIndices.has_key(tag):
                tagIndices[tag] = []
            tagIndices[tag].append(i)

        print "Finding useful rules..."
        # Collect all rules that fix any errors, with their positive scores.
        for i in errorIndices:
            for template in self._templates:
                # Find the templated rules that could fix the error.
                for rule in template.applicable_rules(tagged_tokens, i,
                                                    train_tokens[i][1]):
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
                    if rule.applies(tagged_tokens, nextIndex):
                        _updateRuleApplies(rule, nextIndex)
                        if ruleScores[rule] < maxScore:
                            firstUnknownIndex[rule] = nextIndex+1
                            break  # the _update demoted the rule

                # If we checked all remaining indices and found no more errors:
                if ruleScores[rule] == maxScore:
                    firstUnknownIndex[rule] = len(tagged_tokens) # i.e., we checked them all
                    print "%i) %s (score: %i)" %(len(rules)+1, rule, maxScore)
                    bestRule = rule
                    break
                
            if bestRule == None: # all rules dropped below maxScore
                del rulesByScore[maxScore]
                maxScore = max(rulesByScore.keys())
                continue  # with next-best rules

            # bug-check only
            if TESTING:
                before = len(_errorPositions(tagged_tokens, train_tokens))
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
            bestRule.apply_at(tagged_tokens, positionsByRule[bestRule].keys())

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
            neighbors = set()
            for i in positionsByRule[bestRule].keys(): # sites changed
                for template in self._templates:
                    neighbors.update(template.get_neighborhood(tagged_tokens, i))

            # Then collect the new set of rules for each such index.
            c = d = e = 0
            for i in neighbors:
                siteRules = set()
                for template in self._templates:
                    # Get a set of the rules that the template now generates
                    siteRules.update(set(template.applicable_rules(
                                        tagged_tokens, i, train_tokens[i][1])))

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
                                   len(train_tokens))
        
        # Maintain a list of the rules that apply at each position.
        rules_by_position = [{} for tok in train_tokens]

        # Create and return a tagger from the rules we found.
        return Brill(self._initial_tagger, rules)

######################################################################
## Testing
######################################################################

def _errorPositions (train_tokens, tokens):
    return [i for i in range(len(tokens)) 
            if tokens[i][1] !=
            train_tokens[i][1] ]

# returns a list of errors in string format
def errorList (train_tokens, tokens, radius=2):
    """
    Returns a list of human-readable strings indicating the errors in the
    given tagging of the corpus.

    @param train_tokens: The correct tagging of the corpus
    @type train_tokens: C{list} of C{tuple}
    @param tokens: The tagged corpus
    @type tokens: C{list} of C{tuple}
    @param radius: How many tokens on either side of a wrongly-tagged token
        to include in the error string.  For example, if C{radius}=2, each error
        string will show the incorrect token plus two tokens on either side.
    @type radius: int
    """
    errors = []
    indices = _errorPositions(train_tokens, tokens)
    tokenLen = len(tokens)
    for i in indices:
        ei = tokens[i][1].rjust(3) + " -> " \
             + train_tokens[i][1].rjust(3) + ":  "
        for j in range( max(i-radius, 0), min(i+radius+1, tokenLen) ):
            if tokens[j][0] == tokens[j][1]:
                s = tokens[j][0] # don't print punctuation tags
            else:
                s = tokens[j][0] + "/" + tokens[j][1]
                
            if j == i:
                ei += "**"+s+"** "
            else:
                ei += s + " "
        errors.append(ei)

    return errors

#####################################################################################
# Demonstration
#####################################################################################

def demo(num_sents=100, max_rules=200, min_score=2, error_output = "errors.out",
         rule_output="rules.out", randomize=False, train=.8, trace=3):
    """
    Brill Tagger Demonstration

    @param num_sents: how many sentences of training and testing data to use
    @type num_sents: L{int}
    @param max_rules: maximum number of rule instances to create
    @type max_rules: L{int}
    @param min_score: the minimum score for a rule in order for it to be considered
    @type min_score: L{int}
    @param error_output: the file where errors will be saved
    @type error_output: L{string}
    @param rule_output: the file where rules will be saved
    @type rule_output: L{string}
    @param randomize: whether the training data should be a random subset of the corpus
    @type randomize: L{boolean}
    @param train: the fraction of the the corpus to be used for training (1=all)
    @type train: L{float}
    @param trace: the level of diagnostic tracing output to produce (0-3)
    @type train: L{int}
    """

    from nltk_lite.corpora import treebank
    from nltk_lite import tag
    from nltk_lite.tag import brill

    NN_CD_tagger = tag.Regexp([(r'^-?[0-9]+(.[0-9]+)?$', 'CD'), (r'.*', 'NN')])

    # train is the proportion of data used in training; the rest is reserved
    # for testing.

    print "Loading tagged data..."
    sents = list(treebank.tagged())
    if randomize:
        random.seed(len(sents))
        random.shuffle(sents)

    tagged_data = [t for s in sents[:num_sents] for t in s]
    cutoff = int(len(tagged_data)*train)

    training_data = tagged_data[:cutoff]
    gold_data = tagged_data[cutoff:]

    testing_data = [t[0] for t in gold_data]

    # Unigram tagger

    print "Training unigram tagger:",
    u = tag.Unigram(backoff=NN_CD_tagger)

    # NB training and testing are required to use a list-of-lists structure,
    # so we wrap the flattened corpus data with the extra list structure.
    u.train([training_data])
    print("[accuracy: %f]" % tag.accuracy(u, [gold_data]))

    # Brill tagger

    templates = [
        brill.SymmetricProximateTokensTemplate(brill.ProximateTagsRule, (1,1)),
        brill.SymmetricProximateTokensTemplate(brill.ProximateTagsRule, (2,2)),
        brill.SymmetricProximateTokensTemplate(brill.ProximateTagsRule, (1,2)),
        brill.SymmetricProximateTokensTemplate(brill.ProximateTagsRule, (1,3)),
        brill.SymmetricProximateTokensTemplate(brill.ProximateWordsRule, (1,1)),
        brill.SymmetricProximateTokensTemplate(brill.ProximateWordsRule, (2,2)),
        brill.SymmetricProximateTokensTemplate(brill.ProximateWordsRule, (1,2)),
        brill.SymmetricProximateTokensTemplate(brill.ProximateWordsRule, (1,3)),
        brill.ProximateTokensTemplate(brill.ProximateTagsRule, (-1, -1), (1,1)),
        brill.ProximateTokensTemplate(brill.ProximateWordsRule, (-1, -1), (1,1)),
        ]

    #trainer = brill.FastBrillTrainer(u, templates, trace)
    trainer = brill.BrillTrainer(u, templates, trace)
    b = trainer.train(training_data, max_rules, min_score)

    print
    print("Brill accuracy: %f" % tag.accuracy(b, [gold_data]))

    print("\nRules: ")
    printRules = file(rule_output, 'w')
    for rule in b.rules():
        print(str(rule))
        printRules.write(str(rule)+"\n\n")

    testing_data = list(b.tag(testing_data))
    el = errorList(gold_data, testing_data)
    errorFile = file(error_output, 'w')

    for e in el:
        errorFile.write(e+"\n\n")
    errorFile.close()
    print "Done; rules and errors saved to %s and %s." % (rule_output, error_output)

if __name__ == '__main__':
    demo()
