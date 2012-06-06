__author__ = 'kacper'


#noinspection PyMethodParameters
class Malteval_metric(object):
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
