# Natural Language Toolkit: Confusion Matrices
#
# Copyright (C) 2001-2026 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
#         Steven Bird <stevenbird1@gmail.com>
#         Tom Aarsen <>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

from nltk.probability import FreqDist


class ConfusionMatrix:
    """
    The confusion matrix between a list of reference values and a
    corresponding list of test values.  Entry *[r,t]* of this
    matrix is a count of the number of times that the reference value
    *r* corresponds to the test value *t*.  E.g.:

        >>> from nltk.metrics import ConfusionMatrix
        >>> ref  = 'DET NN VB DET JJ NN NN IN DET NN'.split()
        >>> test = 'DET VB VB DET NN NN NN IN DET NN'.split()
        >>> cm = ConfusionMatrix(ref, test)
        >>> print(cm['NN', 'NN'])
        3

    Note that the diagonal entries *Ri=Tj* of this matrix
    corresponds to correct values; and the off-diagonal entries
    correspond to incorrect values.
    """

    def __init__(self, reference, test, sort_by_count=False):
        """
        Construct a new confusion matrix from a list of reference
        values and a corresponding list of test values.

        :type reference: list
        :param reference: An ordered list of reference values.
        :type test: list
        :param test: A list of values to compare against the
            corresponding reference values.
        :raise ValueError: If ``reference`` and ``length`` do not have
            the same length.
        """
        if len(reference) != len(test):
            raise ValueError("Lists must have the same length.")

        # Get a list of all values.
        if sort_by_count:
            ref_fdist = FreqDist(reference)
            test_fdist = FreqDist(test)

            def key(v):
                return -(ref_fdist[v] + test_fdist[v])

            values = sorted(set(reference + test), key=key)
        else:
            values = sorted(set(reference + test))

        # Construct a value->index dictionary
        indices = {val: i for (i, val) in enumerate(values)}

        # Make a sparse confusion matrix: a dict mapping each observed
        # (reference index, test index) pair to its count. A dense V x V table
        # would allocate V**2 cells even when only a few pairs occur, so an
        # all-distinct input (V == number of items) costs O(V**2) memory and
        # OOM-kills the worker (CWE-770; CVE-2026-12839). The sparse map costs
        # only as much as the observed pairs.
        # Row totals (count per reference index) are accumulated here in the
        # same single pass. ``sort_by_count`` orders labels by their row total,
        # so caching them keeps that lookup O(1); recomputing a total by
        # scanning the sparse map on each call would make the sort O(V * nnz),
        # i.e. quadratic again for a large all-distinct input.
        confusion = {}
        row_totals = {}
        max_conf = 0  # Maximum confusion
        for w, g in zip(reference, test):
            i = indices[w]
            pair = (i, indices[g])
            count = confusion.get(pair, 0) + 1
            confusion[pair] = count
            row_totals[i] = row_totals.get(i, 0) + 1
            if count > max_conf:
                max_conf = count

        #: A list of all values in ``reference`` or ``test``.
        self._values = values
        #: A dictionary mapping values in ``self._values`` to their indices.
        self._indices = indices
        #: The confusion matrix itself, as a sparse dict mapping each observed
        #: ``(reference index, test index)`` pair to its count.
        self._confusion = confusion
        #: Cached per-reference-row totals, keyed by reference index, so
        #: ``sort_by_count`` lookups are O(1) (see ``_row_total``).
        self._row_totals = row_totals
        #: The greatest count in ``self._confusion`` (used for printing).
        self._max_conf = max_conf
        #: The total number of values in the confusion matrix.
        self._total = len(reference)
        #: The number of correct (on-diagonal) values in the matrix.
        self._correct = sum(c for (i, j), c in confusion.items() if i == j)

    def _row_total(self, i):
        """Total count in row ``i`` (alignments from reference value ``i``).

        Read from the cache built once in ``__init__`` (a single O(nnz) pass),
        so ``sort_by_count`` can order all labels in O(V log V) rather than
        rescanning the sparse map per label (O(V * nnz), quadratic for a large
        all-distinct input).
        """
        return self._row_totals.get(i, 0)

    def __getitem__(self, li_lj_tuple):
        """
        :return: The number of times that value ``li`` was expected and
        value ``lj`` was given.
        :rtype: int
        """
        (li, lj) = li_lj_tuple
        i = self._indices[li]
        j = self._indices[lj]
        return self._confusion.get((i, j), 0)

    def __repr__(self):
        return f"<ConfusionMatrix: {self._correct}/{self._total} correct>"

    def __str__(self):
        return self.pretty_format()

    def pretty_format(
        self,
        show_percents=False,
        values_in_chart=True,
        truncate=None,
        sort_by_count=False,
    ):
        """
        :return: A multi-line string representation of this confusion matrix.
        :type truncate: int
        :param truncate: If specified, then only show the specified
            number of values.  Any sorting (e.g., sort_by_count)
            will be performed before truncation.
        :param sort_by_count: If true, then sort by the count of each
            label in the reference data.  I.e., labels that occur more
            frequently in the reference label will be towards the left
            edge of the matrix, and labels that occur less frequently
            will be towards the right edge.

        @todo: add marginals?
        """
        confusion = self._confusion

        values = self._values
        if sort_by_count:
            values = sorted(values, key=lambda v: -self._row_total(self._indices[v]))

        if truncate:
            values = values[:truncate]

        if values_in_chart:
            value_strings = ["%s" % val for val in values]
        else:
            value_strings = [str(n + 1) for n in range(len(values))]

        # Construct a format string for row values
        valuelen = max(len(val) for val in value_strings)
        value_format = "%" + repr(valuelen) + "s | "
        # Construct a format string for matrix entries
        if show_percents:
            entrylen = 6
            entry_format = "%5.1f%%"
            zerostr = "     ."
        else:
            entrylen = len(repr(self._max_conf))
            entry_format = "%" + repr(entrylen) + "d"
            zerostr = " " * (entrylen - 1) + "."

        # Write the column values.
        s = ""
        for i in range(valuelen):
            s += (" " * valuelen) + " |"
            for val in value_strings:
                if i >= valuelen - len(val):
                    s += val[i - valuelen + len(val)].rjust(entrylen + 1)
                else:
                    s += " " * (entrylen + 1)
            s += " |\n"

        # Write a dividing line
        s += "{}-+-{}+\n".format("-" * valuelen, "-" * ((entrylen + 1) * len(values)))

        # Write the entries.
        for val, li in zip(value_strings, values):
            i = self._indices[li]
            s += value_format % val
            for lj in values:
                j = self._indices[lj]
                count = confusion.get((i, j), 0)
                if count == 0:
                    s += zerostr
                elif show_percents:
                    s += entry_format % (100.0 * count / self._total)
                else:
                    s += entry_format % count
                if i == j:
                    prevspace = s.rfind(" ")
                    s = s[:prevspace] + "<" + s[prevspace + 1 :] + ">"
                else:
                    s += " "
            s += "|\n"

        # Write a dividing line
        s += "{}-+-{}+\n".format("-" * valuelen, "-" * ((entrylen + 1) * len(values)))

        # Write a key
        s += "(row = reference; col = test)\n"
        if not values_in_chart:
            s += "Value key:\n"
            for i, value in enumerate(values):
                s += "%6d: %s\n" % (i + 1, value)

        return s

    def key(self):
        values = self._values
        str = "Value key:\n"
        indexlen = len(repr(len(values) - 1))
        key_format = "  %" + repr(indexlen) + "d: %s\n"
        str += "".join([key_format % (i, values[i]) for i in range(len(values))])
        return str

    def recall(self, value):
        """Given a value in the confusion matrix, return the recall
        that corresponds to this value. The recall is defined as:

        - *r* = true positive / (true positive + false positive)

        and can loosely be considered the ratio of how often ``value``
        was predicted correctly relative to how often ``value`` was
        the true result.

        :param value: value used in the ConfusionMatrix
        :return: the recall corresponding to ``value``.
        :rtype: float
        """
        # Number of times `value` was correct, and also predicted
        TP = self[value, value]
        # Number of times `value` was correct
        TP_FN = sum(self[value, pred_value] for pred_value in self._values)
        if TP_FN == 0:
            return 0.0
        return TP / TP_FN

    def precision(self, value):
        """Given a value in the confusion matrix, return the precision
        that corresponds to this value. The precision is defined as:

        - *p* = true positive / (true positive + false negative)

        and can loosely be considered the ratio of how often ``value``
        was predicted correctly relative to the number of predictions
        for ``value``.

        :param value: value used in the ConfusionMatrix
        :return: the precision corresponding to ``value``.
        :rtype: float
        """
        # Number of times `value` was correct, and also predicted
        TP = self[value, value]
        # Number of times `value` was predicted
        TP_FP = sum(self[real_value, value] for real_value in self._values)
        if TP_FP == 0:
            return 0.0
        return TP / TP_FP

    def f_measure(self, value, alpha=0.5):
        """
        Given a value used in the confusion matrix, return the f-measure
        that corresponds to this value. The f-measure is the harmonic mean
        of the ``precision`` and ``recall``, weighted by ``alpha``.
        In particular, given the precision *p* and recall *r* defined by:

        - *p* = true positive / (true positive + false negative)
        - *r* = true positive / (true positive + false positive)

        The f-measure is:

        - *1/(alpha/p + (1-alpha)/r)*

        With ``alpha = 0.5``, this reduces to:

        - *2pr / (p + r)*

        :param value: value used in the ConfusionMatrix
        :param alpha: Ratio of the cost of false negative compared to false
            positives. Defaults to 0.5, where the costs are equal.
        :type alpha: float
        :return: the F-measure corresponding to ``value``.
        :rtype: float
        """
        p = self.precision(value)
        r = self.recall(value)
        if p == 0.0 or r == 0.0:
            return 0.0
        return 1.0 / (alpha / p + (1 - alpha) / r)

    def evaluate(self, alpha=0.5, truncate=None, sort_by_count=False):
        """
        Tabulate the **recall**, **precision** and **f-measure**
        for each value in this confusion matrix.

        >>> reference = "DET NN VB DET JJ NN NN IN DET NN".split()
        >>> test = "DET VB VB DET NN NN NN IN DET NN".split()
        >>> cm = ConfusionMatrix(reference, test)
        >>> print(cm.evaluate())
        Tag | Prec.  | Recall | F-measure
        ----+--------+--------+-----------
        DET | 1.0000 | 1.0000 | 1.0000
         IN | 1.0000 | 1.0000 | 1.0000
         JJ | 0.0000 | 0.0000 | 0.0000
         NN | 0.7500 | 0.7500 | 0.7500
         VB | 0.5000 | 1.0000 | 0.6667
        <BLANKLINE>

        :param alpha: Ratio of the cost of false negative compared to false
            positives, as used in the f-measure computation. Defaults to 0.5,
            where the costs are equal.
        :type alpha: float
        :param truncate: If specified, then only show the specified
            number of values. Any sorting (e.g., sort_by_count)
            will be performed before truncation. Defaults to None
        :type truncate: int, optional
        :param sort_by_count: Whether to sort the outputs on frequency
            in the reference label. Defaults to False.
        :type sort_by_count: bool, optional
        :return: A tabulated recall, precision and f-measure string
        :rtype: str
        """
        tags = self._values

        # Apply keyword parameters
        if sort_by_count:
            tags = sorted(tags, key=lambda v: -self._row_total(self._indices[v]))
        if truncate:
            tags = tags[:truncate]

        tag_column_len = max(max(len(tag) for tag in tags), 3)

        # Construct the header
        s = (
            f"{' ' * (tag_column_len - 3)}Tag | Prec.  | Recall | F-measure\n"
            f"{'-' * tag_column_len}-+--------+--------+-----------\n"
        )

        # Construct the body
        for tag in tags:
            s += (
                f"{tag:>{tag_column_len}} | "
                f"{self.precision(tag):<6.4f} | "
                f"{self.recall(tag):<6.4f} | "
                f"{self.f_measure(tag, alpha=alpha):.4f}\n"
            )

        return s


def demo():
    reference = "DET NN VB DET JJ NN NN IN DET NN".split()
    test = "DET VB VB DET NN NN NN IN DET NN".split()
    print("Reference =", reference)
    print("Test    =", test)
    print("Confusion matrix:")
    print(ConfusionMatrix(reference, test))
    print(ConfusionMatrix(reference, test).pretty_format(sort_by_count=True))

    print(ConfusionMatrix(reference, test).recall("VB"))


if __name__ == "__main__":
    demo()
