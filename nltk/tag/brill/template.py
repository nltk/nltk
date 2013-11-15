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
import yaml
import itertools as it

class BrillTemplateI(object):
    """
    An interface for generating lists of transformational rules that
    apply at given sentence positions.  ``BrillTemplateI`` is used by
    ``Brill`` training algorithms to generate candidate rules.
    """
    def __init__(self):
        raise NotImplementedError()

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
        raise NotImplementedError()

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
        raise NotImplementedError()


from nltk.tag.brill.rule import BrillRule


class Template(BrillTemplateI):
    """
    A brill Template that generates a list of L{Rule}s that apply at a given sentence
    position.  In particular, each C{Template} is parameterized by a list of
    independent features (a combination of a specific
    property to extract and a list C{L} of relative positions at which to extract
    it) and generates all Rules that:

      - use the given features, each at its own independent position; and
      - are applicable to the given token.
    """
    ALLTEMPLATES = []
    #record a unique id of form "001", for each template created
    _ids = it.count(0)

    def __init__(self, *features):
        """
        Construct a Template for generating Rules.

        Takes a list of Features. A C{Feature} is a combination
        of a specific property and its relative positions and should be
        a subclass of L{nltk.tag.brill.template.Feature}.

        An alternative calling convention (kept for backwards compatibility,
        but less expressive as it only permits one feature type) is
        Template(Feature, (start1, end1), (start2, end2), ...)
        In new code, that would be better written
        Template(Feature(start1, end1), Feature(start2, end2), ...)

        :type features: list of Features
        :param features: the features to build this Template on
        """

        #determine the calling form: either
        #Template(Feature, args1, [args2, ...)]
        #Template(Feature1(args),  Feature2(args), ...)
        if all(isinstance(f, Feature) for f in features):
            self._features = features
        elif issubclass(features[0], Feature) and all(isinstance(a, tuple) for a in features[1:]):
            self._features = [features[0](*tp) for tp in features[1:]]
        else:
            raise TypeError(
                "expected either Feature1(args), Feature2(args), ... or Feature, (start1, end1), (start2, end2), ...")
        self.id = "{:03d}".format(self._ids.next())
        self.ALLTEMPLATES.append(self)

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, ",".join([str(f) for f in self._features]))

    def applicable_rules(self, tokens, index, correct_tag):
        if tokens[index][1] == correct_tag:
            return []

        # For each of this Template's features, find the conditions
        # that are applicable for the given token.
        # Then, generate one Rule for each combination of features
        # (the crossproduct of the conditions).

        applicable_conditions = self._applicable_conditions(tokens, index)
        xs = list(it.product(*applicable_conditions))
        return [Rule(self.id, tokens[index][1], correct_tag, tuple(x)) for x in xs]

    def _applicable_conditions(self, tokens, index):
        """
        :returns: A set of all conditions for rules
        that are applicable to C{tokens[index]}.
        """
        conditions = []

        for feature in self._features:
            conditions.append([])
            for pos in feature.positions:
                if not (0 <= index+pos < len(tokens)):
                    continue
                value = feature.extract_property(tokens, index+pos)
                conditions[-1].append( (feature, value) )
        return conditions

    def get_neighborhood(self, tokens, index):
        # inherit docs from BrillTemplateI

        # applicable_rules(tokens, index, ...) depends on index.
        neighborhood = set([index])  #set literal for python 2.7+

        # applicable_rules(tokens, i, ...) depends on index if
        # i+start < index <= i+end.

        allpositions = [0] + [p for feat in self._features for p in feat.positions]
        start, end = min(allpositions), max(allpositions)
        s = max(0, index+(-end))
        e = min(index+(-start)+1, len(tokens))
        for i in range(s, e):
            neighborhood.add(i)
        return neighborhood

    @classmethod
    def expand(cls, featurelists, propersubsets=True, skipintersecting=True):
        """
        Factory method to mass generate Templates from a list L of Feature lists,
        by computing the Cartesian product of all non-empty subsets of L,
        and removing any duplicates. The feature lists may have been specified
        manually, but perhaps generated from Feature.expand(). For instance,


          Template.expand([ [Word([0]), Word([0,1])], [Tag([-2]), Tag([-1])] ])

          will return a list of eight templates
              Template(Word([0])),
              Template(Word([0, 1])),
              Template(Tag([-2])),
              Template(Tag([-1])),
              Template(Tag([-2]),Word([0])),
              Template(Tag([-1]),Word([0])),
              Template(Tag([-2]),Word([0, 1])),
              Template(Tag([-1]),Word([0, 1]))]

        With propersubsets=False, L itself rather than all its subsets will be used,
        so that each featurelist in L is represented in all templates in the output
        (in the example, only the four last templates would be output).

        Templates where one feature is a subset of another, such as
        Template(Word([0,1]), Word([1]), will not appear in the output.
        By default, this non-subset constraint is tightened to disjointness:
        Templates of type Template(Word([0,1]), Word([1,2]) will also be filtered out.
        With skipintersecting=False, then such Templates are allowed

        WARNING: this method makes it very easy to fill all your memory when training
        generated templates on any real-world corpus

        :param featurelists: lists of Features, whose Cartesian product will return a set of Templates
        :type featurelists: list of (list of Features)
        :param propersubsets: if True, generated Templates will have 1..n features given n feature lists; if False, n
        :type propersubsets: bool
        :param skipintersecting: if True, do not output intersecting Templates (non-disjoint positions for some feature)
        :type skipintersecting: bool
        :returns: generator of Templates

        """

        def nonempty_powerset(xs):
            #nonempty_powerset([1,2,3]) --> (1,) (2,) (3,) (1,2) (1,3) (2,3) (1,2,3)
            #from itertools doc (xs is a list)
            subsetsize = 1 if propersubsets else len(xs)
            return it.chain.from_iterable(it.combinations(xs, r)
                                          for r in range(subsetsize, len(xs)+1))
        seentemplates = set()
        for picks in nonempty_powerset(featurelists):
            for pick in it.product(*picks):
                if any(i != j and x.issuperset(y)
                       for (i, x) in enumerate(pick)
                       for (j,y) in enumerate(pick)):
                    continue
                if skipintersecting and any(i != j and x.intersects(y)
                                            for (i, x) in enumerate(pick)
                                            for (j, y) in enumerate(pick)):
                    continue
                thistemplate = cls(*sorted(pick))
                strpick = str(thistemplate)
                if strpick in seentemplates:
                    continue
                seentemplates.add(strpick)
                yield thistemplate


class Feature(yaml.YAMLObject):
    """
    An abstract base class for Features. A Feature is a combination of
    a specific property-computing method and a list of relative positions
    to apply that method to.

    The property-computing method, M{extract_property(tokens, index)},
    must be implemented by every subclass. It extracts or computes a specific
    property for the token at the current index. Typical extract_property()
    methods return features such as the token text or tag; but more involved
    methods may consider the entire sequence M{tokens} and
    for instance compute the length of the sentence the token belongs to.

    In addition, the subclass may have a PROPERTY_NAME, which is how
    it will be printed (in Rules and Templates, etc). If not given, defaults
    to the classname.

    The subclass may also explicitly set a tag for yaml serialization. If
    not given, defaults to '!' + the classname in lowercase (e.g., "!tag").

    """
    yaml_tag = None
    PROPERTY_NAME = None


    def __init__(self, positions, end=None):
        """
        Construct a Feature which may apply at C{positions}.

        :type positions: list of int
        :param positions: the positions at which this features should apply
        :raises ValueError: illegal position specifications

        An alternative calling convention, for contiguous positions only,
        is Feature(start, end):

        :type start: int
        :param start: start of range where this feature should apply
        :type end: int
        :param end: end of range (NOTE: inclusive!) where this feature should apply

        """
        self.positions = None #to avoid warnings
        if end is None:
            self.positions = tuple(sorted(set([int(i) for i in positions])))
        else:                #positions was actually not a list, but only the start index
            try:
                if positions > end:
                    raise TypeError()
                self.positions = tuple(range(positions, end+1))
            except TypeError:
                #let any kind of erroneous spec raise ValueError
                raise ValueError("illegal interval specification: (start={}, end={})".format(positions, end))

        #set property name given in subclass, or otherwise name of subclass
        self.PROPERTY_NAME = self.__class__.PROPERTY_NAME or self.__class__.__name__
        #set yaml_tag name given in subclass, or otherwise name of subclass, lowercased
        self.yaml_tag = self.__class__.yaml_tag or "!{}".format(self.__class__.__name__.lower())

    def __repr__(self):
        return "%s(%r)" % (
            self.__class__.__name__, list(self.positions))

    @classmethod
    def expand(cls, starts, winlens, excludezero=False):
        """
        Return a list of features, one for each start point in starts
        and for each window length in winlen. If excludezero is True,
        no Features containing 0 in its positions will be generated
        (many tbl trainers have a special representation for the
        target feature at [0])

        :param starts: where to start looking for Feature
        :type starts: list of ints
        :param winlens: window lengths where to look for Feature
        :type starts: list of ints
        :param excludezero: do not output any Feature with 0 in any of its positions.
        :type excludezero: bool
        :returns: list of Features
        :raises ValueError: for non-positive window lengths
        """
        if not all(x > 0 for x in winlens):
            raise ValueError("non-positive window length in {:s}".format(winlens))
        xs = (starts[i:i+w] for w in winlens for i in range(len(starts)-w+1))
        return [cls(x) for x in xs if not (excludezero and 0 in x)]

    def issuperset(self, other):
        return (self.__class__ is other.__class__ and
               set(self.positions) >= set(other.positions))

    def intersects(self, other):
        return (self.__class__ is other.__class__ and
               set(self.positions) & set(other.positions))

    #Rich comparisons for Features. With @functools.total_ordering (Python 2.7+),
    # it will be enough to define __lt__ and __eq__
    def __eq__(self, other):
        return (self.__class__ is other.__class__ and
               self.positions == other.positions)
    def __lt__(self, other):
        return (self.__class__.__name__ < other.__class__.__name__ or
               #self.positions is a sorted tuple of ints
               self.positions < other.positions)
    def __ne__(self, other):
        return not (self == other)
    def __gt__(self, other):
        return other < self
    def __ge__(self, other):
        return not self < other
    def __le__(self, other):
        return self < other or self == other

    @staticmethod
    def extract_property(tokens, index):
        raise NotImplementedError("subclass of Feature must define extract_property(tokens, index)")

class Rule(BrillRule):
    """
    A Rule checks the current corpus position for a certain set of conditions;
    if they are all fulfilled, the Rule is triggered, meaning that it
    will change tag A to tag B. For other tags than A, nothing happens.

    The conditions are parameters to the Rule instance. Each condition is a feature-value pair,
    with a set of positions to check for the value of the corresponding feature.
    Conceptually, the positions are joined by logical OR, and the feature set by logical AND.

    More formally, the Rule is then applicable to the M{n}th token iff:

      - The M{n}th token is tagged with the Rule's original tag; and
      - For each (Feature(positions), M{value}) tuple:
        - The value of Feature of at least one token in {n+p for p in positions}
          is M{value}.

    """
    yaml_tag = '!Rule'
    def __init__(self, templateid, original_tag, replacement_tag, conditions):
        """
        Construct a new Rule that changes a token's tag from
        C{original_tag} to C{replacement_tag} if all of the properties
        specified in C{conditions} hold.

        @type templateid: string
        @param templateid: the template id (a zero-padded string, '001' etc,
          so it will sort nicely)

        @type conditions: C{iterable} of C{Feature}
        @param conditions: A list of Feature(positions),
            each of which specifies that the property (computed by
            Feature.extract_property()) of at least one
            token in M{n} + p in positions is C{value}.

        """
        BrillRule.__init__(self, original_tag, replacement_tag)
        self._conditions = conditions
        self.templateid = templateid

    # Make Rules look nice in YAML.
    @classmethod
    def to_yaml(cls, dumper, data):
        d = dict(
            description=str(data),
            conditions=list(data._conditions),
            original=data.original_tag,
            replacement=data.replacement_tag,
            templateid=data.templateid)
        node = dumper.represent_mapping(cls.yaml_tag, d)
        return node

    @classmethod
    def from_yaml(cls, loader, node):
        map = loader.construct_mapping(node, deep=True)
        return cls(map['templateid'], map['original'], map['replacement'], map['conditions'])


    def applies(self, tokens, index):
        # Inherit docs from BrillRule

        # Does the given token have this Rule's "original tag"?
        if tokens[index][1] != self.original_tag:
            return False

        # Check to make sure that every condition holds.
        for (feature, val) in self._conditions:

            # Look for *any* token that satisfies the condition.
            for pos in feature.positions:
                if not (0 <= index + pos < len(tokens)):
                    continue
                if feature.extract_property(tokens, index+pos) == val:
                    break
            else:
                # No token satisfied the condition; return false.
                return False

        # Every condition checked out, so the Rule is applicable.
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
            self.__repr = ('%s(%s, %r, %r, %s)' % (
                self.__class__.__name__,
                self.templateid,
                self.original_tag,
                self.replacement_tag,
                list(self._conditions)))

            return self.__repr

    def __str__(self):
        def _condition_to_logic(feature, value):
            """
            Return a compact, predicate-logic styled string representation
            of the given condition.
            """
            return ('%s:%s@[%s]' %
                (feature.PROPERTY_NAME, value, ",".join(str(w) for w in feature.positions)))

        conditions = ' & '.join([_condition_to_logic(f,v) for (f,v) in self._conditions])
        s = ('%s->%s if %s' % (
            self.original_tag,
            self.replacement_tag,
            conditions))
        return s


    def format(self, fmt):
        if fmt == "str":
            return self.__str__()
        elif fmt == "repr":
            return self.__repr__()
        elif fmt == "verbose":
            return self._verbose_format()
        else:
            raise ValueError("unknown rule format spec: {}".format(fmt))

    def _verbose_format(self):
        """
        Return a wordy, human-readable string representation
        of the given rule.

        Not sure how useful this is.
        """
        def condition_to_str(feature, value):
            return ('the %s of %s is "%s"' %
                    (feature.PROPERTY_NAME, range_to_str(feature.positions), value))

        def range_to_str(positions):
            if len(positions) == 1:
                p = positions[0]
                if p == 0:
                    return 'this word'
                if p == -1:
                    return 'the preceding word'
                elif p == 1:
                    return 'the following word'
                elif p < 0:
                    return 'word i-%d' % -p
                elif p > 0:
                    return 'word i+%d' % p
            else:
                # for complete compatibility with the wordy format of nltk2
                mx = max(positions)
                mn = min(positions)
                if mx - mn == len(positions) - 1:
                    return 'words i%+d...i%+d' % (mn, mx)
                else:
                    return 'words {%s}' % (",".join("i%+d" % d for d in positions),)

        replacement = '%s -> %s' % (self.original_tag, self.replacement_tag)
        conditions = (' if ' if self._conditions else "") + ', and '.join(
            [condition_to_str(f,v) for (f,v) in self._conditions])
        return replacement + conditions

