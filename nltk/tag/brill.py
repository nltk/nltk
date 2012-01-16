# Natural Language Toolkit: Brill Tagger
#
# Copyright (C) 2001-2012 NLTK Project
# Authors: Christopher Maloof <cjmaloof@gradient.cis.upenn.edu>
#          Edward Loper <edloper@gradient.cis.upenn.edu>
#          Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Brill Tagger

The Brill Tagger is a transformational rule-based tagger.
It starts by running an initial tagger, and then
improves the tagging by applying a list of transformation rules.
These transformation rules are automatically learned from the training
corpus, based on one or more "rule templates."

    >>> from nltk.corpus import brown
    >>> from nltk.tag import UnigramTagger
    >>> from nltk.tag.brill import SymmetricProximateTokensTemplate, ProximateTokensTemplate
    >>> from nltk.tag.brill import ProximateTagsRule, ProximateWordsRule, FastBrillTaggerTrainer
    >>> brown_train = list(brown.tagged_sents(categories='news')[:500])
    >>> brown_test = list(brown.tagged_sents(categories='news')[500:600])
    >>> unigram_tagger = UnigramTagger(brown_train)
    >>> templates = [
    ...     SymmetricProximateTokensTemplate(ProximateTagsRule, (1,1)),
    ...     SymmetricProximateTokensTemplate(ProximateTagsRule, (2,2)),
    ...     SymmetricProximateTokensTemplate(ProximateTagsRule, (1,2)),
    ...     SymmetricProximateTokensTemplate(ProximateTagsRule, (1,3)),
    ...     SymmetricProximateTokensTemplate(ProximateWordsRule, (1,1)),
    ...     SymmetricProximateTokensTemplate(ProximateWordsRule, (2,2)),
    ...     SymmetricProximateTokensTemplate(ProximateWordsRule, (1,2)),
    ...     SymmetricProximateTokensTemplate(ProximateWordsRule, (1,3)),
    ...     ProximateTokensTemplate(ProximateTagsRule, (-1, -1), (1,1)),
    ...     ProximateTokensTemplate(ProximateWordsRule, (-1, -1), (1,1)),
    ...     ]
    >>> trainer = FastBrillTaggerTrainer(initial_tagger=unigram_tagger,
    ...                                  templates=templates, trace=3,
    ...                                  deterministic=True)
    >>> brill_tagger = trainer.train(brown_train, max_rules=10)
    Training Brill tagger on 500 sentences...
    Finding initial useful rules...
        Found 10210 useful rules.
    <BLANKLINE>
               B      |
       S   F   r   O  |        Score = Fixed - Broken
       c   i   o   t  |  R     Fixed = num tags changed incorrect -> correct
       o   x   k   h  |  u     Broken = num tags changed correct -> incorrect
       r   e   e   e  |  l     Other = num tags changed incorrect -> incorrect
       e   d   n   r  |  e
    ------------------+-------------------------------------------------------
      46  46   0   0  | TO -> IN if the tag of the following word is 'AT'
      18  20   2   0  | TO -> IN if the tag of words i+1...i+3 is 'CD'
      14  14   0   0  | IN -> IN-TL if the tag of the preceding word is
                      |   'NN-TL', and the tag of the following word is
                      |   'NN-TL'
      11  11   0   1  | TO -> IN if the tag of the following word is 'NNS'
      10  10   0   0  | TO -> IN if the tag of the following word is 'JJ'
       8   8   0   0  | , -> ,-HL if the tag of the preceding word is 'NP-
                      |   HL'
       7   7   0   1  | NN -> VB if the tag of the preceding word is 'MD'
       7  13   6   0  | NN -> VB if the tag of the preceding word is 'TO'
       7   7   0   0  | NP-TL -> NP if the tag of words i+1...i+2 is 'NNS'
       7   7   0   0  | VBN -> VBD if the tag of the preceding word is
                      |   'NP'
    >>> brill_tagger.evaluate(brown_test) # doctest: +ELLIPSIS
    0.742...

"""

import bisect        # for binary search through a subset of indices
import random        # for shuffling WSJ files
import yaml          # to save and load taggers in files
import textwrap
from collections import defaultdict

from nltk.tag.util import untag
from nltk.tag.api import TaggerI

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
    def __init__(self, initial_tagger, rules):
        """
        :param initial_tagger: The initial tagger
        :type initial_tagger: TaggerI
        :param rules: An ordered list of transformation rules that
            should be used to correct the initial tagging.
        :type rules: list(BrillRule)
        """
        self._initial_tagger = initial_tagger
        self._rules = tuple(rules)

    def rules(self):
        return self._rules

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

######################################################################
## Brill Rules
######################################################################

class BrillRule(yaml.YAMLObject):
    """
    An interface for tag transformations on a tagged corpus, as
    performed by brill taggers.  Each transformation finds all tokens
    in the corpus that are tagged with a specific original tag and
    satisfy a specific condition, and replaces their tags with a
    replacement tag.  For any given transformation, the original
    tag, replacement tag, and condition are fixed.  Conditions may
    depend on the token under consideration, as well as any other
    tokens in the corpus.

    Brill rules must be comparable and hashable.
    """
    def __init__(self, original_tag, replacement_tag):
        assert self.__class__ != BrillRule, \
               "BrillRule is an abstract base class"

        self.original_tag = original_tag
        """The tag which this BrillRule may cause to be replaced."""

        self.replacement_tag = replacement_tag
        """The tag with which this BrillRule may replace another tag."""

    def apply(self, tokens, positions=None):
        """
        Apply this rule at every position in positions where it
        applies to the given sentence.  I.e., for each position p
        in *positions*, if *tokens[p]* is tagged with this rule's
        original tag, and satisfies this rule's condition, then set
        its tag to be this rule's replacement tag.

        :param tokens: The tagged sentence
        :type tokens: list(tuple(str, str))
        :type positions: list(int)
        :param positions: The positions where the transformation is to
            be tried.  If not specified, try it at all positions.
        :return: The indices of tokens whose tags were changed by this
            rule.
        :rtype: int
        """
        if positions is None:
            positions = range(len(tokens))

        # Determine the indices at which this rule applies.
        change = [i for i in positions if self.applies(tokens, i)]

        # Make the changes.  Note: this must be done in a separate
        # step from finding applicable locations, since we don't want
        # the rule to interact with itself.
        for i in change:
            tokens[i] = (tokens[i][0], self.replacement_tag)

        return change

    def applies(self, tokens, index):
        """
        :return: True if the rule would change the tag of
            ``tokens[index]``, False otherwise
        :rtype: bool
        :param tokens: A tagged sentence
        :type tokens: list(str)
        :param index: The index to check
        :type index: int
        """
        assert False, "Brill rules must define applies()"

    # Rules must be comparable and hashable for the algorithm to work
    def __eq__(self):
        assert False, "Brill rules must be comparable"
    def __ne__(self):
        assert False, "Brill rules must be comparable"
    def __hash__(self):
        assert False, "Brill rules must be hashable"


class ProximateTokensRule(BrillRule):
    """
    An abstract base class for brill rules whose condition checks for
    the presence of tokens with given properties at given ranges of
    positions, relative to the token.

    Each subclass of proximate tokens brill rule defines a method
    ``extract_property()``, which extracts a specific property from the
    the token, such as its text or tag.  Each instance is
    parameterized by a set of tuples, specifying ranges of positions
    and property values to check for in those ranges: ``(start, end, value)``.

    The brill rule is then applicable to the *n*th token iff:

      - The *n*th token is tagged with the rule's original tag; and
      - For each (start, end, value) triple, the property value of
        at least one token between n+start and n+end (inclusive) is value.

    For example, a proximate token brill template with start=end=-1
    generates rules that check just the property of the preceding
    token.  Note that multiple properties may be included in a single
    rule; the rule applies if they all hold.

    Construct a new brill rule that changes a token's tag from
    *original_tag* to *replacement_tag* if all of the properties
    specified in *conditions* hold.

    :type conditions: tuple(int, int, *)
    :param conditions: A list of 3-tuples (start, end, value),
        each of which specifies that the property of at least one
        token between n+start and n+end (inclusive) is value.
    :raise ValueError: If start>end for any condition.
    """

    def __init__(self, original_tag, replacement_tag, *conditions):
        assert self.__class__ != ProximateTokensRule, \
               "ProximateTokensRule is an abstract base class"
        BrillRule.__init__(self, original_tag, replacement_tag)
        self._conditions = conditions
        for (s,e,v) in conditions:
            if s>e:
                raise ValueError('Condition %s has an invalid range' %
                                 ((s,e,v),))

    # Make Brill rules look nice in YAML.
    @classmethod
    def to_yaml(cls, dumper, data):
        node = dumper.represent_mapping(cls.yaml_tag, dict(
            description=str(data),
            conditions=list(list(x) for x in data._conditions),
            original=data.original_tag,
            replacement=data.replacement_tag))
        return node
    @classmethod
    def from_yaml(cls, loader, node):
        map = loader.construct_mapping(node, deep=True)
        return cls(map['original'], map['replacement'],
        *(tuple(x) for x in map['conditions']))

    @staticmethod
    def extract_property(token):
        """
        Returns some property characterizing this token, such as its
        base lexical item or its tag.

        Each implentation of this method should correspond to an
        implementation of the method with the same name in a subclass
        of ``ProximateTokensTemplate``.

        :param token: The token
        :type token: tuple(str, str)
        :return: The property
        :rtype: any
        """
        assert False, "ProximateTokenRules must define extract_property()"

    def applies(self, tokens, index):
        # Inherit docs from BrillRule

        # Does the given token have this rule's "original tag"?
        if tokens[index][1] != self.original_tag:
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

    def __eq__(self, other):
        return (self is other or
                (other is not None and
                 other.__class__ == self.__class__ and
                 self.original_tag == other.original_tag and
                 self.replacement_tag == other.replacement_tag and
                 self._conditions == other._conditions))

    def __ne__(self, other):
        return not (self==other)

    def __hash__(self):
        # Cache our hash value (justified by profiling.)
        try:
            return self.__hash
        except:
            self.__hash = hash( (self.original_tag, self.replacement_tag,
                                 self._conditions, self.__class__.__name__) )
            return self.__hash

    def __repr__(self):
        # Cache our repr (justified by profiling -- this is used as
        # a sort key when deterministic=True.)
        try:
            return self.__repr
        except:
            conditions = ' and '.join(['%s in %d...%d' % (v,s,e)
                                       for (s,e,v) in self._conditions])
            self.__repr = ('<%s: %s->%s if %s>' %
                           (self.__class__.__name__, self.original_tag,
                            self.replacement_tag, conditions))
            return self.__repr


    def __str__(self):
        replacement = '%s -> %s' % (self.original_tag,
                                    self.replacement_tag)
        if len(self._conditions) == 0:
            conditions = ''
        else:
            conditions = ' if '+ ', and '.join([self._condition_to_str(c)
                                               for c in self._conditions])
        return replacement+conditions

    def _condition_to_str(self, condition):
        """
        Return a string representation of the given condition.
        This helper method is used by __str__.
        """
        (start, end, value) = condition
        return ('the %s of %s is %r' %
                (self.PROPERTY_NAME, self._range_to_str(start, end), value))

    def _range_to_str(self, start, end):
        """
        Return a string representation for the given range.  This
        helper method is used by __str__.
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
    See ``ProximateTokensRule`` for details.
    Also see ``SymmetricProximateTokensTemplate`` which generates these rules.
    """
    PROPERTY_NAME = 'tag' # for printing.
    yaml_tag = '!ProximateTagsRule'
    @staticmethod
    def extract_property(token):
        """:return: The given token's tag."""
        return token[1]

class ProximateWordsRule(ProximateTokensRule):
    """
    A rule which examines the base types of nearby tokens.
    See ``ProximateTokensRule`` for details.
    Also see ``SymmetricProximateTokensTemplate`` which generates these rules.
    """
    PROPERTY_NAME = 'text' # for printing.
    yaml_tag = '!ProximateWordsRule'
    @staticmethod
    def extract_property(token):
        """:return: The given token's text."""
        return token[0]

######################################################################
## Brill Templates
######################################################################

class BrillTemplateI(object):
    """
    An interface for generating lists of transformational rules that
    apply at given sentence positions.  ``BrillTemplateI`` is used by
    ``Brill`` training algorithms to generate candidate rules.
    """
    def __init__(self):
        raise AssertionError, "BrillTemplateI is an abstract interface"

    def applicable_rules(self, tokens, i, correctTag):
        """
        Return a list of the transformational rules that would correct
        the *i*th subtoken's tag in the given token.  In particular,
        return a list of zero or more rules that would change
        *tokens*[i][1] to *correctTag*, if applied to *token*[i].

        If the *i*th token already has the correct tag (i.e., if
        tagged_tokens[i][1] == correctTag), then
        ``applicable_rules()`` should return the empty list.

        :param tokens: The tagged tokens being tagged.
        :type tokens: list(tuple)
        :param i: The index of the token whose tag should be corrected.
        :type i: int
        :param correctTag: The correct tag for the *i*th token.
        :type correctTag: any
        :rtype: list(BrillRule)
        """
        raise AssertionError, "BrillTemplateI is an abstract interface"

    def get_neighborhood(self, token, index):
        """
        Returns the set of indices *i* such that
        ``applicable_rules(token, i, ...)`` depends on the value of
        the *index*th token of *token*.

        This method is used by the "fast" Brill tagger trainer.

        :param token: The tokens being tagged.
        :type token: list(tuple)
        :param index: The index whose neighborhood should be returned.
        :type index: int
        :rtype: set
        """
        raise AssertionError, "BrillTemplateI is an abstract interface"

class ProximateTokensTemplate(BrillTemplateI):
    """
    A brill template that generates a list of
    ``ProximateTokensRule`` rules that apply at a given sentence
    position.  In particular, each ``ProximateTokensTemplate`` is
    parameterized by a proximate token brill rule class and a list of
    boundaries, and generates all rules that:

      - use the given brill rule class
      - use the given list of boundaries as the start and end
        points for their conditions
      - are applicable to the given token.

    Construct a template for generating proximate token brill rules.

    :type rule_class: class
    :param rule_class: The proximate token brill rule class that
        should be used to generate new rules.  This class must be a
        subclass of ``ProximateTokensRule``.
    :type boundaries: tuple(int, int)
    :param boundaries: A list of (start, end) tuples each of
        which specifies a range for which a condition should be
        created by each rule.
    :raise ValueError: If start>end for any boundary.
    """

    def __init__(self, rule_class, *boundaries):
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
        :return: A set of all conditions for proximate token rules
        that are applicable to *tokens[index]*, given boundaries of
        (start, end).  I.e., return a list of all tuples
        (start, end, value), such the property value of at least one token
        between *index+start* and *index+end* (inclusive) is *value*.
        """
        conditions = []
        s = max(0, index+start)
        e = min(index+end+1, len(tokens))
        for i in range(s, e):
            value = self._rule_class.extract_property(tokens[i])
            conditions.append( (start, end, value) )
        return conditions

    def get_neighborhood(self, tokens, index):
        # inherit docs from BrillTemplateI

        # applicable_rules(tokens, index, ...) depends on index.
        neighborhood = set([index])

        # applicable_rules(tokens, i, ...) depends on index if
        # i+start < index <= i+end.
        for (start, end) in self._boundaries:
            s = max(0, index+(-end))
            e = min(index+(-start)+1, len(tokens))
            for i in range(s, e):
                neighborhood.add(i)

        return neighborhood

class SymmetricProximateTokensTemplate(BrillTemplateI):
    """
    Simulates two ``ProximateTokensTemplate`` templates which are symmetric
    across the location of the token.  For rules of the form "If the
    *n*th token is tagged ``A``, and any tag preceding or following
    the *n*th token by a distance between x and y is ``B``, and
    ... , then change the tag of the *n*th token from ``A`` to ``C``."

    One ``ProximateTokensTemplate`` is formed by passing in the
    same arguments given to this class's constructor: tuples
    representing intervals in which a tag may be found.  The other
    ``ProximateTokensTemplate`` is constructed with the negative
    of all the arguments in reversed order.  For example, a
    ``SymmetricProximateTokensTemplate`` using the pair (-2,-1) and the
    constructor ``SymmetricProximateTokensTemplate`` generates the same rules as a
    ``SymmetricProximateTokensTemplate`` using (-2,-1) plus a second
    ``SymmetricProximateTokensTemplate`` using (1,2).

    This is useful because we typically don't want templates to
    specify only "following" or only "preceding"; we'd like our
    rules to be able to look in either direction.

    Construct a template for generating proximate token brill
    rules.

    :type rule_class: class
    :param rule_class: The proximate token brill rule class that
        should be used to generate new rules.  This class must be a
        subclass of ``ProximateTokensRule``.
    :type boundaries: tuple(int, int)
    :param boundaries: A list of tuples (start, end), each of
        which specifies a range for which a condition should be
        created by each rule.
    :raise ValueError: If start>end for any boundary.
    """

    def __init__(self, rule_class, *boundaries):
        self._ptt1 = ProximateTokensTemplate(rule_class, *boundaries)
        reversed = [(-e,-s) for (s,e) in boundaries]
        self._ptt2 = ProximateTokensTemplate(rule_class, *reversed)

    # Generates lists of a subtype of ProximateTokensRule.
    def applicable_rules(self, tokens, index, correctTag):
        """
        See ``BrillTemplateI`` for full specifications.

        :rtype: list of ProximateTokensRule
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

class BrillTaggerTrainer(object):
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
                 deterministic=None):
        if deterministic is None: deterministic = (trace > 0)
        self._initial_tagger = initial_tagger
        self._templates = templates
        self._trace = trace
        self._deterministic = deterministic

    #////////////////////////////////////////////////////////////
    # Training
    #////////////////////////////////////////////////////////////

    def train(self, train_sents, max_rules=200, min_score=2):
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
        if self._trace > 0: print ("Training Brill tagger on %d "
                                   "sentences..." % len(train_sents))

        # Create a new copy of the training corpus, and run the
        # initial tagger on it.  We will progressively update this
        # test corpus to look more like the training corpus.
        test_sents = [self._initial_tagger.tag(untag(sent))
                      for sent in train_sents]

        if self._trace > 2: self._trace_header()

        # Look for useful rules.
        rules = []
        try:
            while len(rules) < max_rules:
                (rule, score, fixscore) = self._best_rule(test_sents,
                                                          train_sents)
                if rule is None or score < min_score:
                    if self._trace > 1:
                        print 'Insufficient improvement; stopping'
                    break
                else:
                    # Add the rule to our list of rules.
                    rules.append(rule)
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
            print "Training stopped manually -- %d rules found" % len(rules)

        # Create and return a tagger from the rules we found.
        return BrillTagger(self._initial_tagger, rules)

    #////////////////////////////////////////////////////////////
    # Finding the best rule
    #////////////////////////////////////////////////////////////

    # Finds the rule that makes the biggest net improvement in the corpus.
    # Returns a (rule, score) pair.
    def _best_rule(self, test_sents, train_sents):
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

            # Calculate the actual score, by decrementing fixscore
            # once for each tag that the rule changes to an incorrect
            # value.
            score = fixscore
            if rule.original_tag in correct_indices:
                for (sentnum, wordnum) in correct_indices[rule.original_tag]:
                    if rule.applies(test_sents[sentnum], wordnum):
                        score -= 1
                        # If the score goes below best_score, then we know
                        # that this isn't the best rule; so move on:
                        if score < best_score or (score == best_score and
                                                  not self._deterministic):
                            break

            # If the actual score is better than the best score, then
            # update best_score and best_rule.
            if score > best_score or (score == best_score and
                                      self._deterministic and
                                      repr(rule) < repr(best_rule)):
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
                      key=lambda (rule,score): -score)

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
            print textwrap.fill(str(rule), initial_indent=' '*20, width=79,
                                subsequent_indent=' '*18+'|   ').strip()
        else:
            print rule

######################################################################
## Fast Brill Tagger Trainer
######################################################################

class FastBrillTaggerTrainer(object):
    """
    A faster trainer for brill taggers.
    """
    def __init__(self, initial_tagger, templates, trace=0,
                 deterministic=False):
        if not deterministic:
            deterministic = (trace > 0)
        self._initial_tagger = initial_tagger
        self._templates = templates
        self._trace = trace
        self._deterministic = deterministic

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

        if self._trace > 0: print ("Training Brill tagger on %d "
                                   "sentences..." % len(train_sents))

        # Create a new copy of the training corpus, and run the
        # initial tagger on it.  We will progressively update this
        # test corpus to look more like the training corpus.
        test_sents = [self._initial_tagger.tag(untag(sent))
                      for sent in train_sents]

        # Initialize our mappings.  This will find any errors made
        # by the initial tagger, and use those to generate repair
        # rules, which are added to the rule mappings.
        if self._trace > 0: print "Finding initial useful rules..."
        self._init_mappings(test_sents, train_sents)
        if self._trace > 0: print ("    Found %d useful rules." %
                                   len(self._rule_scores))

        # Let the user know what we're up to.
        if self._trace > 2: self._trace_header()
        elif self._trace == 1: print "Selecting rules..."

        # Repeatedly select the best rule, and add it to `rules`.
        rules = []
        try:
            while (len(rules) < max_rules):
                # Find the best rule, and add it to our rule list.
                rule = self._best_rule(train_sents, test_sents, min_score)
                if rule:
                    rules.append(rule)
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
            print "Training stopped manually -- %d rules found" % len(rules)

        # Discard our tag position mapping & rule mappings.
        self._clean()

        # Create and return a tagger from the rules we found.
        return BrillTagger(self._initial_tagger, rules)

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
        print """
           B      |
   S   F   r   O  |        Score = Fixed - Broken
   c   i   o   t  |  R     Fixed = num tags changed incorrect -> correct
   o   x   k   h  |  u     Broken = num tags changed correct -> incorrect
   r   e   e   e  |  l     Other = num tags changed incorrect -> incorrect
   e   d   n   r  |  e
------------------+-------------------------------------------------------
        """.rstrip()

    def _trace_rule(self, rule):
        assert self._rule_scores[rule] == \
               sum(self._positions_by_rule[rule].values())

        changes = self._positions_by_rule[rule].values()
        num_changed = len(changes)
        num_fixed = len([c for c in changes if c==1])
        num_broken = len([c for c in changes if c==-1])
        num_other = len([c for c in changes if c==0])
        score = self._rule_scores[rule]

        if self._trace > 2:
            print '%4d%4d%4d%4d  |' % (score,num_fixed,num_broken,num_other),
            print textwrap.fill(str(rule), initial_indent=' '*20,
                                subsequent_indent=' '*18+'|   ').strip()
        else:
            print rule

    def _trace_apply(self, num_updates):
        prefix = ' '*18+'|'
        print prefix
        print prefix, 'Applying rule to %d positions.' % num_updates

    def _trace_update_rules(self, num_obsolete, num_new, num_unseen):
        prefix = ' '*18+'|'
        print prefix, 'Updated rule tables:'
        print prefix, ('  - %d rule applications removed' % num_obsolete)
        print prefix, ('  - %d rule applications added (%d novel)' %
                       (num_new, num_unseen))
        print prefix



######################################################################
## Testing
######################################################################

# returns a list of errors in string format
def error_list (train_sents, test_sents, radius=2):
    """
    Returns a list of human-readable strings indicating the errors in the
    given tagging of the corpus.

    :param train_sents: The correct tagging of the corpus
    :type train_sents: list(tuple)
    :param test_sents: The tagged corpus
    :type test_sents: list(tuple)
    :param radius: How many tokens on either side of a wrongly-tagged token
        to include in the error string.  For example, if radius=2,
        each error string will show the incorrect token plus two
        tokens on either side.
    :type radius: int
    """
    hdr = (('%25s | %s | %s\n' + '-'*26+'+'+'-'*24+'+'+'-'*26) %
           ('left context', 'word/test->gold'.center(22), 'right context'))
    errors = [hdr]
    for (train_sent, test_sent) in zip(train_sents, test_sents):
        for wordnum, (word, train_pos) in enumerate(train_sent):
            test_pos = test_sent[wordnum][1]
            if train_pos != test_pos:
                left = ' '.join('%s/%s' % w for w in train_sent[:wordnum])
                right = ' '.join('%s/%s' % w for w in train_sent[wordnum+1:])
                mid = '%s/%s->%s' % (word, test_pos, train_pos)
                errors.append('%25s | %s | %s' %
                              (left[-25:], mid.center(22), right[:25]))

    return errors

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
    print "Loading tagged data... "
    tagged_data = treebank.tagged_sents()
    if randomize:
        random.seed(len(sents))
        random.shuffle(sents)
    cutoff = int(num_sents*train)
    training_data = tagged_data[:cutoff]
    gold_data = tagged_data[cutoff:num_sents]
    testing_data = [[t[0] for t in sent] for sent in gold_data]
    print "Done loading."

    # Unigram tagger
    print "Training unigram tagger:"
    unigram_tagger = tag.UnigramTagger(training_data,
                                       backoff=nn_cd_tagger)
    if gold_data:
        print "    [accuracy: %f]" % unigram_tagger.evaluate(gold_data)

    # Bigram tagger
    print "Training bigram tagger:"
    bigram_tagger = tag.BigramTagger(training_data,
                                     backoff=unigram_tagger)
    if gold_data:
        print "    [accuracy: %f]" % bigram_tagger.evaluate(gold_data)

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
    trainer = brill.FastBrillTaggerTrainer(bigram_tagger, templates, trace)
    #trainer = brill.BrillTaggerTrainer(u, templates, trace)
    brill_tagger = trainer.train(training_data, max_rules, min_score)

    if gold_data:
        print("\nBrill accuracy: %f" % brill_tagger.evaluate(gold_data))

    if trace <= 1:
        print("\nRules: ")
        for rule in brill_tagger.rules():
            print(str(rule))

    print_rules = file(rule_output, 'w')
    yaml.dump(brill_tagger, print_rules)
    print_rules.close()

    testing_data = brill_tagger.batch_tag(testing_data)
    error_file = file(error_output, 'w')
    error_file.write('Errors for Brill Tagger %r\n\n' % rule_output)
    for e in error_list(gold_data, testing_data):
        error_file.write(e+'\n')
    error_file.close()
    print ("Done; rules and errors saved to %s and %s." %
           (rule_output, error_output))


if __name__ == "__main__":
    import doctest
    doctest.testmod(optionflags=doctest.NORMALIZE_WHITESPACE)

