# Natural Language Toolkit: Test Code for Sets
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Unit testing for L{nltk.set}.
"""

from nltk.set import *

##//////////////////////////////////////////////////////
##  Test code
##//////////////////////////////////////////////////////

import unittest

class SetTestCase(unittest.TestCase):
    """
    Unit test cases for L{nltk.set.Set}
    """
    def _makeset(self, *values):
        """
        This is so the subclass L{MutableSetTestCase} will create
        mutable sets, instead of sets.
        """
        return Set(*values)
    
    def testConstructor(self):
        "nltk.set.Set: constructor tests"
        s1 = self._makeset(1,2,5,4,6,3)
        self.failUnlessEqual(len(s1), 6)
        self.failUnless(1 in s1 and 2 in s1 and 3 in s1 and
                        4 in s1 and 5 in s1 and 6 in s1 and
                        0 not in s1 and 7 not in s1 and
                        8 not in s1)
        s2 = self._makeset()
        self.failUnlessEqual(len(s2), 0)
        self.failIf(-1 in s2 or 0 in s2 or 1 in s2)

        s3 = self._makeset( (1,2,3) )
        self.failUnlessEqual(len(s3), 1)
        self.failIf(1 in s3 or 2 in s3 or 3 in s3)
        self.failUnless( (1,2,3) in s3)

    def testUnion(self):
        "nltk.set.Set: union tests"
        s1 = self._makeset(1,3,5,7,9,11,13,15,17,19,21,23,25)
        s2 = self._makeset(2,3,5,7,11,13,17,19,23)
        s3 = self._makeset(2,4,9,16,25)
        s1s2 = self._makeset(1,2,3,5,7,9,11,13,15,17,19,21,23,25)
        s1s3 = self._makeset(1,2,3,4,5,7,9,11,13,15,16,17,19,21,23,25)
        s2s3 = self._makeset(2,3,4,5,7,9,11,13,16,17,19,23,25)
        s1s2s3 = s1s3

        self.failUnlessEqual(s1.union(s2), s1s2)
        self.failUnlessEqual(s1.union(s3), s1s3)
        self.failUnlessEqual(s2.union(s1), s1s2)
        self.failUnlessEqual(s2.union(s3), s2s3)
        self.failUnlessEqual(s3.union(s1), s1s3)
        self.failUnlessEqual(s3.union(s2), s2s3)
        self.failUnlessEqual(s1.union(s2).union(s3), s1s2s3)
        self.failUnlessEqual(s1.union(s3).union(s2), s1s2s3)
        self.failUnlessEqual(s2.union(s1).union(s3), s1s2s3)
        self.failUnlessEqual(s2.union(s3).union(s1), s1s2s3)
        self.failUnlessEqual(s3.union(s2).union(s1), s1s2s3)
        self.failUnlessEqual(s3.union(s1).union(s2), s1s2s3)
        
        self.failUnlessEqual(s1 | s2, s1s2)
        self.failUnlessEqual(s1 | s3, s1s3)
        self.failUnlessEqual(s2 | s1, s1s2)
        self.failUnlessEqual(s2 | s3, s2s3)
        self.failUnlessEqual(s3 | s1, s1s3)
        self.failUnlessEqual(s3 | s2, s2s3)
        self.failUnlessEqual(s1 | s2 | s3, s1s2s3)
        self.failUnlessEqual(s1 | s3 | s2, s1s2s3)
        self.failUnlessEqual(s2 | s1 | s3, s1s2s3)
        self.failUnlessEqual(s2 | s3 | s1, s1s2s3)
        self.failUnlessEqual(s3 | s2 | s1, s1s2s3)
        self.failUnlessEqual(s3 | s1 | s2, s1s2s3)
        
    def testIntersection(self):
        "nltk.set.Set: intersection tests"
        s1 = self._makeset(1,3,5,7,9,11,13,15,17,19,21,23,25)
        s2 = self._makeset(2,3,5,7,11,13,17,19,23)
        s3 = self._makeset(2,4,9,16,25)
        s1s2 = self._makeset(3,5,7,11,13,17,19,23)
        s1s3 = self._makeset(9,25)
        s2s3 = self._makeset(2)
        s1s2s3 = self._makeset()

        self.failUnlessEqual(s1.intersection(s2), s1s2)
        self.failUnlessEqual(s1.intersection(s3), s1s3)
        self.failUnlessEqual(s2.intersection(s1), s1s2)
        self.failUnlessEqual(s2.intersection(s3), s2s3)
        self.failUnlessEqual(s3.intersection(s1), s1s3)
        self.failUnlessEqual(s3.intersection(s2), s2s3)
        self.failUnlessEqual(s1.intersection(s2).intersection(s3), s1s2s3)
        self.failUnlessEqual(s1.intersection(s3).intersection(s2), s1s2s3)
        self.failUnlessEqual(s2.intersection(s1).intersection(s3), s1s2s3)
        self.failUnlessEqual(s2.intersection(s3).intersection(s1), s1s2s3)
        self.failUnlessEqual(s3.intersection(s2).intersection(s1), s1s2s3)
        self.failUnlessEqual(s3.intersection(s1).intersection(s2), s1s2s3)
        
        self.failUnlessEqual(s1 & s2, s1s2)
        self.failUnlessEqual(s1 & s3, s1s3)
        self.failUnlessEqual(s2 & s1, s1s2)
        self.failUnlessEqual(s2 & s3, s2s3)
        self.failUnlessEqual(s3 & s1, s1s3)
        self.failUnlessEqual(s3 & s2, s2s3)
        self.failUnlessEqual(s1 & s2 & s3, s1s2s3)
        self.failUnlessEqual(s1 & s3 & s2, s1s2s3)
        self.failUnlessEqual(s2 & s1 & s3, s1s2s3)
        self.failUnlessEqual(s2 & s3 & s1, s1s2s3)
        self.failUnlessEqual(s3 & s2 & s1, s1s2s3)
        self.failUnlessEqual(s3 & s1 & s2, s1s2s3)
        
    def testDifference(self):
        "nltk.set.Set: difference tests"
        s1 = self._makeset(1,3,5,7,9,11,13,15,17,19,21,23,25)
        s2 = self._makeset(2,3,5,7,11,13,17,19,23)
        s3 = self._makeset(2,4,9,16,25)
        s1s2 = self._makeset(1,9,15,21,25)
        s1s3 = self._makeset(1,3,5,7,11,13,15,17,19,21,23)
        s2s3 = self._makeset(3,5,7,11,13,17,19,23)
        s2s1 = self._makeset(2)
        s3s1 = self._makeset(2,4,16)
        s3s2 = self._makeset(4,9,16,25)
        s1s2s3 = self._makeset(1,15,21)

        self.failUnlessEqual(s1.difference(s2), s1s2)
        self.failUnlessEqual(s1.difference(s3), s1s3)
        self.failUnlessEqual(s2.difference(s1), s2s1)
        self.failUnlessEqual(s2.difference(s3), s2s3)
        self.failUnlessEqual(s3.difference(s1), s3s1)
        self.failUnlessEqual(s3.difference(s2), s3s2)
        self.failUnlessEqual(s1.difference(s2).difference(s3), s1s2s3)
        
        self.failUnlessEqual(s1 - s2, s1s2)
        self.failUnlessEqual(s1 - s3, s1s3)
        self.failUnlessEqual(s2 - s1, s2s1)
        self.failUnlessEqual(s2 - s3, s2s3)
        self.failUnlessEqual(s3 - s1, s3s1)
        self.failUnlessEqual(s3 - s2, s3s2)
        self.failUnlessEqual(s1 - s2 - s3, s1s2s3)

    def testContains(self):
        "nltk.set.Set: containership tests"
        s = self._makeset(2,3,5,7,11,13,17,19,23)

        self.failUnless(s.contains(11))
        self.failUnless(s.contains(2))
        self.failUnless(s.contains(23))
        self.failUnless(s.contains(11))
        self.failUnless(s.contains(7))
        self.failIf(s.contains(0))
        self.failIf(s.contains(1))
        self.failIf(s.contains(4))
        self.failIf(s.contains(24))

        self.failUnless(11 in s)
        self.failUnless(2 in s)
        self.failUnless(23 in s)
        self.failUnless(11 in s)
        self.failUnless(7 in s)
        self.failIf(0 in s)
        self.failIf(1 in s)
        self.failIf(4 in s)
        self.failIf(24 in s)

    def testCopy(self):
        "nltk.set.Set: copy tests"
        s1 = self._makeset(1,2,3)
        s2 = s1.copy()
        self.failUnlessEqual(s1, self._makeset(1,2,3))
        self.failUnlessEqual(s2, self._makeset(1,2,3))

    def testRepr(self):
        "nltk.set.Set: representation tests (glass-box)."
        
        s1 = self._makeset(1,2,3)
        s2 = self._makeset('a', 'b', (1, '3'))

        # These may break, depending on hasing. :-/
        self.failUnless(repr(s1) in ("{1, 2, 3}", "{1, 3, 2}",
                                     "{2, 1, 3}", "{2, 3, 1}",
                                     "{3, 2, 1}", "{3, 1, 2}"))
        self.failUnless(repr(s2) in ("{'a', 'b', (1, '3')}",
                                     "{'a', (1, '3'), 'b'}",
                                     "{'b', 'a', (1, '3')}",
                                     "{'b', (1, '3'), 'a'}",
                                     "{(1, '3'), 'b', 'a'}",
                                     "{(1, '3'), 'a', 'b'}"))
        self.failUnlessEqual(repr(self._makeset()), '{}')

    def testCount(self):
        "nltk.set.Set: count tests"
        self.failUnlessEqual(self._makeset(1,2,3).count(), 3)
        self.failUnlessEqual(self._makeset(1,(2,3)).count(), 2)
        self.failUnlessEqual(self._makeset((1,2,3)).count(), 1)
        self.failUnlessEqual(self._makeset('abc').count(), 1)
        self.failUnlessEqual(self._makeset().count(), 0)

        self.failUnlessEqual(len(self._makeset(1,2,3)), 3)
        self.failUnlessEqual(len(self._makeset(1,(2,3))), 2)
        self.failUnlessEqual(len(self._makeset((1,2,3))), 1)
        self.failUnlessEqual(len(self._makeset('abc')), 1)
        self.failUnlessEqual(len(self._makeset()), 0)

    def testEqual(self):
        "nltk.set.Set: equality comparison test"
        s1 = self._makeset(1, 2, (3, 5))
        s2 = self._makeset(2, (3, 5))
        self.failIfEqual(s1, s2)
        s2 = s2.union(self._makeset(1))
        self.failUnlessEqual(s1, s2)
        s1 = s1.union(self._makeset((1,7)))
        self.failIfEqual(s1, s2)
        s2 = s2.union(self._makeset((1,7)))
        self.failUnlessEqual(s1, s2)
        self.failUnlessEqual(self._makeset(), self._makeset())

        # Explicitly check ==/!=
        s1 = self._makeset(1, 2, (3, 5))
        s2 = self._makeset(2, (3, 5))
        self.failIf(s1 == s2)
        s2 = s2.union(self._makeset(1))
        self.failIf(s1 != s2)
        s1 = s1.union(self._makeset((1,7)))
        self.failIf(s1 == s2)
        s2 = s2.union(self._makeset((1,7)))
        self.failIf(s1 != s2)
        self.failIf(self._makeset() != self._makeset())

        # Explicitly check cmp()
        s1 = self._makeset(1, 2, (3, 5))
        s2 = self._makeset(2, (3, 5))
        self.failIf(cmp(s1,s2) == 0)
        s2 = s2.union(self._makeset(1))
        self.failIf(cmp(s1,s2) != 0)
        s1 = s1.union(self._makeset((1,7)))
        self.failIf(cmp(s1,s2) == 0)
        s2 = s2.union(self._makeset((1,7)))
        self.failIf(cmp(s1,s2) != 0)
        self.failIf(cmp(self._makeset(), self._makeset()) != 0)

    def testElements(self):
        "nltk.set.Set: elements accessor tests"
        eltsLists = ([1, 3, (5,6)],
                     [],
                     ['asdf', ('a', 's', 'd', 'f'), 123])

        for elts in eltsLists:
            s = self._makeset(*elts)
            s_elts = s.elements()
            elts.sort()
            s_elts.sort()
            self.failUnlessEqual(elts, s_elts)

    def testHash(self):
        "nltk.set.Set: hash() tests"
        s1 = self._makeset(1,2,3)
        s2 = self._makeset(1,2,3)
        self.failUnlessEqual(hash(s1), hash(s2))

    def testPrecision(self):
        "nltk.set.Set: precision() tests"
        s1 = self._makeset(1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
        s2 = self._makeset(2, 4, 6, 8, 10, 12, 14, 16)

        self.failUnlessEqual(s1.precision(s1), 1)
        self.failUnlessEqual(s2.precision(s2), 1)
        self.failUnlessEqual(s1.precision(s2), 5./8)
        self.failUnlessEqual(s2.precision(s1), 5./10)

    def testRecall(self):
        "nltk.set.Set: recall() tests"
        s1 = self._makeset(1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
        s2 = self._makeset(2, 4, 6, 8, 10, 12, 14, 16)

        self.failUnlessEqual(s1.recall(s1), 1)
        self.failUnlessEqual(s2.recall(s2), 1)
        self.failUnlessEqual(s1.recall(s2), 5./10)
        self.failUnlessEqual(s2.recall(s1), 5./8)

    def testFMeasure(self):
        "nltk.set.Set: f_measure() tests"
        s1 = self._makeset(1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
        s2 = self._makeset(2, 4, 6, 8, 10, 12, 14, 16)

        self.failUnlessEqual(s1.f_measure(s1), 1)
        self.failUnlessEqual(s2.f_measure(s2), 1)
        self.failUnlessEqual(s1.f_measure(s2), self._fm(5./8, 5./10))
        self.failUnlessEqual(s2.f_measure(s1), self._fm(5./10, 5./8))

        # alpha=0 gives recall
        self.failUnlessEqual(s1.f_measure(s2,0), 5./10)
        self.failUnlessEqual(s2.f_measure(s1,0), 5./8)

        # alpha=1 gives precision
        self.failUnlessEqual(s1.f_measure(s2,1), 5./8)
        self.failUnlessEqual(s2.f_measure(s1,1), 5./10)

        # test some intermediate alpha values
        self.failUnlessEqual(s1.f_measure(s2, .3), self._fm(5./8, 5./10, .3))
        self.failUnlessEqual(s2.f_measure(s1, .3), self._fm(5./10, 5./8, .3))
        self.failUnlessEqual(s1.f_measure(s2, .8), self._fm(5./8, 5./10, .8))
        self.failUnlessEqual(s2.f_measure(s1, .8), self._fm(5./10, 5./8, .8))

    def _fm(self, p, r, alpha=.5):
        return 1/(alpha/p + (1-alpha)/r)

class MutableSetTestCase(SetTestCase):
    """
    Unit test cases for L{nltk.set.MutableSet}
    """
    def _makeset(self, *values):
        return MutableSet(*values)

    def testInsert(self):
        "nltk.set.MutableSet: insertion tests"
        s1 = MutableSet(5,7)
        self.failUnlessEqual(s1.insert(3), 1)
        self.failUnlessEqual(s1.insert(5), 0)
        self.failUnlessEqual(s1.insert(3), 0)
        self.failUnlessEqual(s1.insert(5), 0)
        self.failUnlessEqual(s1.insert(8), 1)
        self.failUnlessEqual(s1.insert(7), 0)
        self.failUnlessEqual(s1, Set(3,5,8,7))

        s2 = MutableSet('a', 'z', 'abcd', (1,2), 3)
        self.failUnlessEqual(s2.insert(1), 1)
        self.failUnlessEqual(s2.insert((1,2)), 0)
        self.failUnlessEqual(s2.insert('b'), 1)
        self.failUnlessEqual(s2.insert('abc'), 1)
        self.failUnlessEqual(s2.insert('a'), 0)
        self.failUnlessEqual(s2.insert('abcd'), 0)
        self.failUnlessEqual(s2.insert('abc'), 0)
        self.failUnlessEqual(s2.insert((1,2)), 0)
        self.failUnlessEqual(s2, Set('a', 'z', 'abcd', (1,2), 3,
                                     1, 'b', 'a', 'abc'))

    def testHash(self):
        "nltk.set.MutableSet: hash() tests"
        s1 = MutableSet(1,2,3)
        self.failUnlessRaises(TypeError, hash, s1)

    def testCopy(self):
        "nltk.set.MutableSet: copy tests"
        s1 = MutableSet(1,2,3)

        s2 = s1.copy()
        s1.insert(4)
        s2.insert(5)

        self.failUnlessEqual(s1, MutableSet(1,2,3,4))
        self.failUnlessEqual(s2, MutableSet(1,2,3,5))

    def testEqual(self):
        "nltk.set.MutableSet: equality comparison test"
        s1 = MutableSet(1, 2, (3, 5))
        s2 = MutableSet(2, (3, 5))

        self.failIfEqual(s1, s2)
        s2.insert(1)
        self.failUnlessEqual(s1, s2)
        s1.insert((1,7))
        self.failIfEqual(s1, s2)
        s2.insert((1,7))
        self.failUnlessEqual(s1, s2)
        self.failUnlessEqual(MutableSet(), MutableSet())

def testsuite():
    """
    Return a PyUnit testsuite for the set module.
    """
    t1 = unittest.makeSuite(SetTestCase, 'test')
    t2 = unittest.makeSuite(MutableSetTestCase, 'test')
    return unittest.TestSuite( (t1, t2) )

def test():
    import unittest
    runner = unittest.TextTestRunner()
    runner.run(testsuite())

if __name__ == '__main__':
    test()
