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

from __future__ import print_function
import abc

from nltk import python_2_unicode_compatible
from nltk.tag.brill.template import BrillTemplateI
from nltk.tag.brill.rule import BrillRule


@python_2_unicode_compatible
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
    #!!FOR_FUTURE: when targeting python3 only, consider @abc.abstractmethod
    # and metaclass=abc.ABCMeta rather than NotImplementedError
    #http://julien.danjou.info/blog/2013/guide-python-static-class-abstract-methods

    def __init__(self, original_tag, replacement_tag, *conditions):
        if self.__class__ != ProximateTokensRule: raise TypeError(
               "ProximateTokensRule is an abstract base class")
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
            description="%s" % data,
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
    def extract_property(tokens):
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
        raise NotImplementedError

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
        except Exception:
            conditions = ' and '.join('%s in %d...%d' % (v,s,e)
                                      for (s,e,v) in self._conditions)
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
            conditions = ' if '+ ', and '.join(self._condition_to_str(c)
                                               for c in self._conditions)
        return replacement+conditions

    def _condition_to_str(self, condition):
        """
        Return a string representation of the given condition.
        This helper method is used by __str__.
        """
        (start, end, value) = condition
        return ("the %s of %s is '%s'" %
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


######################################################################
## Brill Templates
######################################################################

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

        :rtype: list of nltk.tag.brill.nltk2.template.ProximateTokensRule
        """
        return (self._ptt1.applicable_rules(tokens, index, correctTag) +
                self._ptt2.applicable_rules(tokens, index, correctTag))

    def get_neighborhood(self, tokens, index):
        # inherit docs from BrillTemplateI
        n1 = self._ptt1.get_neighborhood(tokens, index)
        n2 = self._ptt2.get_neighborhood(tokens, index)
        return n1.union(n2)

