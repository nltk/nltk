# Natural Language Toolkit: Evaluation
#
# Copyright (C) 2004 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT


"""
Utility functions for evaluating processing modules.
"""

from nltk.chktype import chktype
import sets

def accuracy(wanted, got):
    """
    @return: The percentage of items in the list C{got} that are equal
    to the corresponding items in the list C{wanted}.  In particular,
    this function counts the number of instances where C{got[i]} ==
    C{wanted[i]} and returns this count as a fraction of the size of
    C{wanted}.  The two lists C{wanted} and C{got} must have equal
    lengths.

    @type wanted: C{list}
    @param wanted: The correct values.
    @type got: C{list}
    @param got: The actual values.
    """
    assert chktype(1, wanted, [])
    assert chktype(2, got, [])
    if len(wanted) != len(got):
        raise ValueError("Lists must have the same length.")
    num_correct = [1 for x,y in zip(wanted, got) if x==y]
    return float(len(num_correct)) / len(wanted)

def precision(wanted, got):
    """
    @type wanted: C{set}
    @type got: C{set}
    """
    assert chktype(1, wanted, sets.BaseSet)
    assert chktype(2, got, sets.BaseSet)
    if len(got) == 0:
        return None
    else:
        return float(len(wanted.intersection(got)))/len(got)

def recall(wanted, got):
    """
    @type wanted: C{set}
    @type got: C{set}
    """
    assert chktype(1, wanted, sets.BaseSet)
    assert chktype(2, got, sets.BaseSet)
    if len(wanted) == 0:
        return None
    else:
        return float(len(wanted.intersection(got)))/len(wanted)

def f_measure(wanted, got, alpha=0.5):
    p = precision(wanted, got)
    r = recall(wanted, got)
    if p is None or r is None:
        return None
    if p == 0 or r == 0:
        return 0
    return 10.0/(alpha/p + (1-alpha)/r)

class ConfusionMatrix:
    """
    The confusion matrix between a list of correct values and the list
    of actual values.  Entry [M{Li},M{Lj}] of this matrix is a count
    of the number of times that label M{Li} was expected and label
    M{Lj} was given.
    """
    def __init__(self, wanted, got):
        """
        Construct a new confusion matrix from a list of correct values
        and a list of actual values.
        @param wanted: The correct values.
        @param got: The actual values.
        """
        assert chktype(1, wanted, [])
        assert chktype(2, got, [])
        
        if len(wanted) != len(got):
            raise ValueError('Lists must have the same length.')
            
        # Get a list of all labels.
        labels = dict([(l,1) for l in wanted+got]).keys()

        # Construct a label->index dictionary
        indices = dict([(l,i) for (i,l) in enumerate(labels)])

        # Make a confusion matrix table.
        confusion = [[0 for l in labels] for l in labels]
        max_conf = 0 # Maximum confusion
        for w,g in zip(wanted, got):
            confusion[indices[w]][indices[g]] += 1
            max_conf = max(max_conf, confusion[indices[w]][indices[g]])

        self._indices = indices
        self._confusion = confusion
        self._labels = labels
        self._max_conf = 0
        self._total = len(wanted)
        self._correct = sum([confusion[i][i] for i in range(len(labels))])

    def __getitem__(self, (li,lj)):
        """
        @return: The number of times that label C{li} was expected and
        label C{lj} was given.
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
    
    def pp(self, show_percents=False, labels_in_chart=True):
        """
        @return: A multi-line string representation of this confusion
        matrix.
        @todo: add marginals?
        """
        confusion = self._confusion

        if labels_in_chart:
            labels = self._labels
        else:
            labels = range(len(self._labels))

        # Construct a format string for row labels
        labellen = max([len(str(l)) for l in labels])
        label_format = '%' + `labellen` + 's |'
        # Construct a format string for matrix entries
        if show_percents:
            entrylen = 6
            entry_format = '%5.1f%%'
        else:
            entrylen = len(`self._max_conf`)
            entry_format = '%' + `entrylen` + 'd'

        # Write the column labels.
        label_strings = [str(l) for l in labels]
        s = ''
        for i in range(labellen):
            s += (' '*labellen)+' |'
            for l in label_strings:
                if i >= labellen-len(l):
                    s += l[i-labellen+len(l)].rjust(entrylen+1)
                else:
                    s += ' '*(entrylen+1)
            s += ' |\n'

        # Write a dividing line
        s += '%s-+-%s+\n' % ('-'*labellen, '-'*((entrylen+1)*len(labels)))

        # Write the entries.
        for i in range(len(labels)):
            s += label_format % labels[i]
            for j in range(len(labels)):
                s += ' '
                if show_percents:
                    s += entry_format % (100.0*confusion[i][j]/self._total)
                else:
                    s += entry_format % confusion[i][j]
            s += ' |\n'
            
        # Write a dividing line
        s += '%s-+-%s+\n' % ('-'*labellen, '-'*((entrylen+1)*len(labels)))

        # Write a key
        s += '(row = wanted; col = got)\n'
        if not labels_in_chart:
            s += 'Label key:\n'
            for i, label in enumerate(self._labels):
                s += '%6d: %s\n' % (i, label)

        return s
        
    def key(self):
        labels = self._labels
        str = 'Label key:\n'
        indexlen = len(`len(labels)-1`)
        key_format = '  %'+`indexlen`+'d: %s\n'
        for i in range(len(labels)):
            str += key_format % (i, labels[i])

        return str

def demo():
    print '-'*75
    wanted = 'DET NN VB DET JJ NN NN IN DET NN'.split()
    got    = 'DET VB VB DET NN NN NN IN DET NN'.split()
    print 'Wanted =', wanted
    print 'Got    =', got
    print 'Confusion matrix:'
    print ConfusionMatrix(wanted, got)
    print 'Accuracy:', accuracy(wanted, got)

    print '-'*75
    wanted_set = sets.Set(wanted)
    got_set = sets.Set(got)
    print 'Wanted =', wanted_set
    print 'Got =   ', got_set
    print 'Precision:', precision(wanted_set, got_set)
    print '   Recall:', recall(wanted_set, got_set)
    print 'F-Measure:', f_measure(wanted_set, got_set)
    print '-'*75

if __name__ == '__main__':
    demo()
