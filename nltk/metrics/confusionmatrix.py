# Natural Language Toolkit: Confusion Matrices
#
# Copyright (C) 2001-2010 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

class ConfusionMatrix(object):
    """
    The confusion matrix between a list of reference values and a
    corresponding list of test values.  Entry [M{r},M{t}] of this
    matrix is a count of the number of times that the reference value
    M{r} corresponds to the test value M{t}.  E.g.:

        >>> ref  = 'DET NN VB DET JJ NN NN IN DET NN'.split()
        >>> test = 'DET VB VB DET NN NN NN IN DET NN'.split()
        >>> cm = ConfusionMatrix(ref, test)
        >>> print cm['NN', 'NN']
        3

    Note that the diagonal entries (M{Ri}=M{Tj}) of this matrix
    corresponds to correct values; and the off-diagonal entries
    correspond to incorrect values.
    """
    
    def __init__(self, reference, test, sort_by_count=False):
        """
        Construct a new confusion matrix from a list of reference
        values and a corresponding list of test values.
        
        @type reference: C{list}
        @param reference: An ordered list of reference values.
        @type test: C{list}
        @param test: A list of values to compare against the
            corresponding reference values.
        @raise ValueError: If C{reference} and C{length} do not have
            the same length.
        """
        if len(reference) != len(test):
            raise ValueError('Lists must have the same length.')
            
        # Get a list of all values.
        if sort_by_count:
            ref_fdist = FreqDist(reference)
            test_fdist = FreqDist(test)
            def key(v): return -(ref_fdist[v]+test_fdist[v])
            values = sorted(set(reference+test), key=key)
        else:
            values = sorted(set(reference+test))

        # Construct a value->index dictionary
        indices = dict((val,i) for (i,val) in enumerate(values))

        # Make a confusion matrix table.
        confusion = [[0 for val in values] for val in values]
        max_conf = 0 # Maximum confusion
        for w,g in zip(reference, test):
            confusion[indices[w]][indices[g]] += 1
            max_conf = max(max_conf, confusion[indices[w]][indices[g]])

        #: A list of all values in C{reference} or C{test}.
        self._values = values
        #: A dictionary mapping values in L{self._values} to their indices.
        self._indices = indices
        #: The confusion matrix itself (as a list of lists of counts).
        self._confusion = confusion
        #: The greatest count in L{self._confusion} (used for printing).
        self._max_conf = max_conf
        #: The total number of values in the confusion matrix.
        self._total = len(reference)
        #: The number of correct (on-diagonal) values in the matrix.
        self._correct = sum(confusion[i][i] for i in range(len(values)))

    def __getitem__(self, (li,lj)):
        """
        @return: The number of times that value C{li} was expected and
        value C{lj} was given.
        @rtype: C{int}
        """
        i = self._indices[li]
        j = self._indices[lj]
        return self._confusion[i][j]

    def __repr__(self):
        return '<ConfusionMatrix: %s/%s correct>' % (self._correct,
                                                     self._total)

    def __str__(self):
        return self.pp()
    
    def pp(self, show_percents=False, values_in_chart=True,
           truncate=None, sort_by_count=False):
        """
        @return: A multi-line string representation of this confusion
        matrix.
        @type truncate: int
        @param truncate: If specified, then only show the specified
            number of values.  Any sorting (e.g., sort_by_count)
            will be performed before truncation.
        @param sort_by_count: If true, then sort by the count of each
            label in the reference data.  I.e., labels that occur more
            frequently in the reference label will be towards the left
            edge of the matrix, and labels that occur less frequently
            will be towards the right edge.
        @todo: add marginals?
        """
        confusion = self._confusion

        values = self._values
        if sort_by_count:
            values = sorted(values, key=lambda v:
                            -sum(self._confusion[self._indices[v]]))

        if truncate:
            values = values[:truncate]

        if values_in_chart:
            value_strings = [str(val) for val in values]
        else:
            value_strings = [str(n+1) for n in range(len(values))]
            
        # Construct a format string for row values
        valuelen = max(len(val) for val in value_strings)
        value_format = '%' + `valuelen` + 's | '
        # Construct a format string for matrix entries
        if show_percents:
            entrylen = 6
            entry_format = '%5.1f%%'
            zerostr = '     .'
        else:
            entrylen = len(`self._max_conf`)
            entry_format = '%' + `entrylen` + 'd'
            zerostr = ' '*(entrylen-1) + '.'

        # Write the column values.
        s = ''
        for i in range(valuelen):
            s += (' '*valuelen)+' |'
            for val in value_strings:
                if i >= valuelen-len(val):
                    s += val[i-valuelen+len(val)].rjust(entrylen+1)
                else:
                    s += ' '*(entrylen+1)
            s += ' |\n'

        # Write a dividing line
        s += '%s-+-%s+\n' % ('-'*valuelen, '-'*((entrylen+1)*len(values)))

        # Write the entries.
        for val, li in zip(value_strings, values):
            i = self._indices[li]
            s += value_format % val
            for lj in values:
                j = self._indices[lj]
                if confusion[i][j] == 0:
                    s += zerostr
                elif show_percents:
                    s += entry_format % (100.0*confusion[i][j]/self._total)
                else:
                    s += entry_format % confusion[i][j]
                if i == j:
                    prevspace = s.rfind(' ')
                    s = s[:prevspace] + '<' + s[prevspace+1:] + '>'
                else: s += ' '
            s += '|\n'
            
        # Write a dividing line
        s += '%s-+-%s+\n' % ('-'*valuelen, '-'*((entrylen+1)*len(values)))

        # Write a key
        s += '(row = reference; col = test)\n'
        if not values_in_chart:
            s += 'Value key:\n'
            for i, value in enumerate(values):
                s += '%6d: %s\n' % (i+1, value)

        return s
        
    def key(self):
        values = self._values
        str = 'Value key:\n'
        indexlen = len(`len(values)-1`)
        key_format = '  %'+`indexlen`+'d: %s\n'
        for i in range(len(values)):
            str += key_format % (i, values[i])

        return str

def demo():
    reference = 'DET NN VB DET JJ NN NN IN DET NN'.split()
    test    = 'DET VB VB DET NN NN NN IN DET NN'.split()
    print 'Reference =', reference
    print 'Test    =', test
    print 'Confusion matrix:'
    print ConfusionMatrix(reference, test)
    print ConfusionMatrix(reference, test).pp(sort_by_count=True)

if __name__ == '__main__':
    demo()
