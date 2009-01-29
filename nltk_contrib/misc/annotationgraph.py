# Natural Language Toolkit: Annotation Graphs
#
# Copyright (C) 2001-2009 NLTK Project
# Author: Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

from nltk import Tree, Index

class AnnotationGraph(object):
    
    def __init__(self, t):
        self._edges = []
        self._len = len(t.leaves())
        self._nodes = range(self._len)
        self._convert(t, 0)
        self._index = Index((start, (end, label)) for (start, end, label) in self._edges)
    
    def _convert(self, t, start):
        next = start
        if isinstance(t, Tree):
            label = t.node
            for child in t:
                next = self._convert(child, next)
        else:
            label = t
            next += 1
        
        edge = (start, next, label)
        self._edges.append(edge)
        return next

    def edges(self):
        return self._edges
    
    # partial proper analyses
    def ppa(self, maxlen=None, left=0):
        if maxlen is None:
            maxlen = self._len
        if maxlen == 0:
            yield []
        else:
            for i in range(left, self._len):  # each starting node
                for (right, label) in self._index[i]:  # each edge starting here
                    for continuation in self.ppa(maxlen-1, right):
                        if continuation == []:
                            yield [label]
                        else:
                            result = [label]
                            result.extend(continuation)
                            yield result
    
    # proper analysis segments
    def pas(self, Vr):
        for i in range(self._len):
            for p in self.pas2(Vr, i):
                yield p
        
    def pas2(self, Vr, left=0):
        if left == self._len:
            yield []
        for (right, label) in self._index[left]:
            for continuation in self.pas2(Vr, right):
                if continuation == []:
                    yield [label]
                else:
                    result = [label]
                    result.extend(continuation)
                    yield result


def demo():
    s = '(S (NP (DT the) (NN cat)) (VP (VBD ate) (NP (DT a) (NN cookie))))'
    s = '(VP (VBD ate) (NP (DT a) (NN cookie)))'
    t = Tree(s)
    ag = AnnotationGraph(t)
    for p in ag.pas2([]):
        print p

if __name__ == '__main__':
    demo()

    