# coding: utf-8
__author__ = 'kacper'


class _MaltevalParameters(object):
    '''
    The available parameters are: Metric, GroupBy, MinSentenceLength,
    MaxSentenceLength, ExcludeWordforms, ExcludeLemmas, ExcludeCpostags,
    ExcludePostags, ExcludeFeats, ExcludeDeprels, ExcludePdeprels
    and ExcludeUnicodePunc. The parameters Metric and GroupBy have re-
    stricted sets of possible values, enumerated in 3.1.2 and 3.1.3, whereas
    no control of the values is performed by MaltEval for the others.
    '''

    @property
    def Metric(self):
        return "Metric"

    @property
    def GroupBy(self):
        return "GroupBy"

    @property
    def MinSentenceLength(self):
        return "MinSentenceLength"

    @property
    def MaxSentenceLength(self):
        return "MaxSentenceLength"

    @property
    def ExcludeWordforms(self):
        return "ExcludeWordforms"

    @property
    def ExcludeLemmas(self):
        return "ExcludeLemmas"

    @property
    def ExcludeCpostags(self):
        return "ExcludeCpostags"

    @property
    def ExcludePostags(self):
        return "ExcludePostags"

    @property
    def ExcludeFeats(self):
        return "ExcludeFeats"

    @property
    def ExcludeDeprels(self):
        return "ExcludeDeprels"

    @property
    def ExcludePdeprels(self):
        return "ExcludePdeprels"

    @property
    def ExcludeUnicodePunc(self):
        return "ExcludeUnicodePunc"


class _MaltevalMetric(object):
    @property
    def LAS(self):
        """ A token is counted as a hit if both the head and the dependency
        label are the same as in the gold-standard data. This is the
        default value."""
        return 'LAS'

    @property
    def LA(self):
        """
        A token is counted as a hit if the dependency label is the same
        as in the gold-standard data.
        """
        return 'LA'

    @property
    def UAS(self):
        """
        A token is counted as a hit if the head is the same as in the
        gold-standard data.
        """
        return "UAS"

    @property
    def AnyRight(self):
        """
        A token is counted as a hit if either the head or the dependency
        label (or both) is the same as in the gold-standard data.
        """
        return "AnyRight"

    @property
    def BothWrong(self):
        """
        A token is counted as a hit if neither the head nor the dependency
        label are the same as in the gold-standard data.
        """
        return "BothWrong"

    @property
    def LabelWrong(self):
        """A token is counted as a hit if the dependency label is not the same
        as in the gold-standard data."""
        return "LabelWrong"

    @property
    def HeadWrong(self):
        """A token is counted as a hit if the head is not the same as in the
        gold-standard data."""
        return "HeadWrong"

    @property
    def AnyWrong(self):
        """A token is counted as a hit if either the head or the dependency
        label (or both) is not the same as in the gold-standard data."""
        return "AnyWrong"

    @property
    def Self(self):
        """This is a special type of metric that is dependent on the selected
        GroupBy values (see 3.1.3 in maltEval documentation). Each grouping
        strategy has a of called self metric which is applied when the metric
        value equals self. The self value is applicable for all grouping
        strategies but is in practice only useful for grouping strategies where
        the grouping values of the gold-standard data and the parsed data may
        differ. For example consult MaltEval documentation 3.1.2"""
        return "self"


class _MaltevalGroupBy(object):
    @property
    def Token(self):
        '''
        Each token is treated individually. The mean value is therefore
        computed by dividing the number of tokens with a hit (according
        to the Metric value) with the total number of tokens in the data,
        the standard way of computing accuracy in dependency parsing.
        Available values for the format attribute: accuracy.
        '''
        return "Token"

    @property
    def Wordform(self):
        """
        All tokens with the same value for the wordform attribute (case sen-
        sitive) are grouped together.
        """
        return "Wordform"

    @property
    def Lemma(self):
        """
        All tokens with the same value for the lemma attribute
        (case sensitive) are grouped together.
        """
        return "Lemma"

    @property
    def Cpostag(self):
        """
        All tokens with the same value for the cpostag attribute
        (case sensitive) are grouped together.
        """
        return "Cpostag"

    @property
    def Postag(self):
        """
        All tokens with the same value for the postag attribute
        (case sensitive) are grouped together.
        """
        return "Postag"

    @property
    def Feats(self):
        """
        All tokens with the same value for the feats attribute (case
        sensitive) are grouped together. Each feat value is therefore
        treated as an atomic value.
        """
        return "Feats"

    @property
    def Deprel(self):
        """
        All tokens with the same value for the deprel attribute
        (case sensitive) are grouped together.
        """
        return "Deprel"

    @property
    def Sentence(self):
        """
        All tokens in the same sentence are treated as one group.
        """
        return "Sentence"

    @property
    def RelationLength(self):
        """
        All tokens with the same arc length are grouped. Arc length
        is computed as the (positive) difference in word position between
        a token and the token’s head. Hence, whether the dependent is
        located to the left or right of the head is indifferent. Root tokens,
        i.e. tokens without heads, are treated as one group separately having
        the value -1. The value 0 is reserved for any tokens having an arc
        pointing to itself.
        """
        return "RelationLength"

    @property
    def GroupedRelationLength(self):
        """
        This is a similar grouping strategy as RelationLength,
        where the difference is that the lengths are grouped into
        either “to root”, “1”, “2”,“3–6” or “7–...”.
        """
        return "GroupedRelationLength"

    @property
    def SentenceLength(self):
        """
        The tokens are grouped according to sentence length, which
        can be any integer value equal or greater than 1.
        """
        return "SentenceLength"

    @property
    def StartWordPosition(self):
        """
        This strategy groups tokens according to the tokens’
        positions in the sentence counted from the sentence start. That
        is, the first token of every sentence belongs to group 1, the
        second token to group 2, and so forth.
        """
        return "StartWordPosition"

    @property
    def EndWordPosition(self):
        """
        The opposite to StartWordPosition, e.g. the last
        token of each sentence belongs to group 1, the second last token
        belongs to group 2, and so forth.
        """
        return "EndWordPosition"

    @property
    def ArcDirection(self):
        """
        Each token is mapped to one of four values, depending on the
        direction of the arc. The group “left” contains all token with
        the head located to the left of itself, and the group “right” then
        contains all token with the head located to the right of itself.
        All root tokens are treated separately as the group “to root”. All
        tokens with itself as the head is mapped to the group “self”, which
        hopefully is an empty group.
        """
        return "ArcDirection"

    @property
    def ArcDepth(self):
        """
        The tokens are groups according the distance to the root token. Again,
        all tokens with out a head token are grouped separately, in this case
        in group “0”, and all tokens on depth 1 from the root will
        consequently form the group “1”, and so forth.
        """
        return "ArcDepth"

    @property
    def BranchingFactor(self):
        """
        This grouping strategy is the number of direct dependents
        of a token as key for grouping, which can be any integer value equal
        or greater than 0.
        """
        return "BranchingFactor"

    @property
    def ArcProjectivity(self):
        """
        This grouping strategy has only two values, “0” and “1”
        representing projective and non-projective arcs. Informally,
        an arc is projective if all tokens it covers are descendants
        of the arc’s head token.
        """
        return "ArcProjectivity"

    @property
    def Frame(self):
        """
        For this grouping strategy, the dependency labels of a token and
        its dependents are used. The dependency types of the dependents
        are sorted according their position in the sentence, separated by
        a white space. The dependency label of the token’s dependency label
        is positioned between the left and right dependents surrounded by
        two *-characters. For example, a token with the dependency label
        Pred having a Sub dependent to the left, and an Obj dependent
        followed by an Adv dependent to the right, would be one instance of
        the frame group Sub *Pred* Obj Adv. Note that the evaluation is
        computed for the token with the dependency label Pred and/or its head
        value,not the complete frame.
        """
        return "Frame"

MaltevalGroupBy = _MaltevalGroupBy()
MaltevalParameters = _MaltevalParameters()
MaltevalMetric = _MaltevalMetric()
