# Natural Language Toolkit: Test Code for Type Checking
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

from nltk.chktype import *
import types

##//////////////////////////////////////////////////////
##  Test code
##//////////////////////////////////////////////////////

import unittest

class ChktypeTestCase(unittest.TestCase):
    """
    Unit test cases for C{chktype.chktype}
    """
    def setUp(self):
        type_safety_level(4)
    
    def demo1(self, x, f, s):
        assert chktype(1, x, types.IntType, types.LongType)
        assert chktype(2, f, types.FloatType)
        assert chktype(3, s, types.StringType)

    def testTypes(self):
        # These should not raise exceptions:
        def t1(demo=self.demo1): demo(1, 1.0, 'hello')
        def t2(demo=self.demo1): demo(-5, 1.0, '')
        def t3(demo=self.demo1): demo(12L, 1.0, 'hello')
        t1(), t2(), t3()

        # These should raise exceptions:
        def t4(demo=self.demo1): demo(1.0, 1.0, 'hello')
        def t5(demo=self.demo1): demo(1, 1, 'hello')
        def t6(demo=self.demo1): demo(1, 1L, 'hello')
        def t7(demo=self.demo1): demo(1, 'x', 'hello')
        def t8(demo=self.demo1): demo('x', 1.0, 'hello')
        def t9(demo=self.demo1): demo(0, 0.0, 12)
        def t10(demo=self.demo1): demo(0, 1.0, ['h' ,'i'])
        def t11(demo=self.demo1): demo([0], 1.0, 'hi')
        def t12(demo=self.demo1): demo(0, [1.0], 'hi')

        for t in (t4, t5, t6, t7, t8, t9, t10, t11, t12):
            self.assertRaises(TypeError, t)

    def demo2(self, list1, list2, list3):
        assert chktype(1, list1, [])
        assert chktype(2, list2, [types.IntType])
        assert chktype(3, list3, [types.IntType, [types.StringType]])

    def testLists(self):
        # These should not raise exceptions:
        def t1(demo=self.demo2): demo([], [], [])
        def t2(demo=self.demo2): demo(['x'], [1], [1])
        def t3(demo=self.demo2): demo(['a', {}, (), 3], [1,2], [3,4])
        def t4(demo=self.demo2): demo([], [], [1, ['x'], 2, ['y', 'z']])
        t1(), t2(), t3(), t4()

        # These should raise exceptions:
        def t5(demo=self.demo2): demo((), [], [])
        def t6(demo=self.demo2): demo([], (), [])
        def t7(demo=self.demo2): demo([], [], ())
        
        def t8(demo=self.demo2): demo({}, [], [])
        def t9(demo=self.demo2): demo([], {}, [])
        def t10(demo=self.demo2): demo([], [], {})
        
        def t11(demo=self.demo2): demo(1, [], [])
        def t12(demo=self.demo2): demo([], 1, [])
        def t13(demo=self.demo2): demo([], [], 1)
        
        def t14(demo=self.demo2): demo([], [2,2,2.0], [])
        def t15(demo=self.demo2): demo([], [], [2,'x',2.0])
        def t16(demo=self.demo2): demo([], [], [3, [3]])
        def t17(demo=self.demo2): demo([], [], [3, ['x', ['y']]])

        for t in (t5, t6, t7, t8, t9, t10, t11, t12, t13, t14, t15, t16, t17):
            self.assertRaises(TypeError, t)

    def demo3(self, tuple1, tuple2, tuple3):
        assert chktype(1, tuple1, ())
        assert chktype(2, tuple2, (types.IntType,))
        assert chktype(3, tuple3, (types.IntType, (types.StringType,)))
        
    def testTuples(self):
        # These should not raise exceptions:
        def t1(demo=self.demo3): demo((), (), ())
        def t2(demo=self.demo3): demo(('x',), (1,), (1,))
        def t3(demo=self.demo3): demo(('a', {}, (), 3,), (1,2,), (3,4,))
        def t4(demo=self.demo3): demo((), (), (1, ('x',), 2, ('y', 'z',),))
        t1(), t2(), t3(), t4()

        # These should raise exceptions:
        def t5(demo=self.demo3): demo([], (), ())
        def t6(demo=self.demo3): demo((), [], ())
        def t7(demo=self.demo3): demo((), (), [])
        
        def t8(demo=self.demo3): demo({}, (), ())
        def t9(demo=self.demo3): demo((), {}, ())
        def t10(demo=self.demo3): demo((), (), {})
        
        def t11(demo=self.demo3): demo(1, (), ())
        def t12(demo=self.demo3): demo((), 1, ())
        def t13(demo=self.demo3): demo((), (), 1)
        
        def t14(demo=self.demo3): demo((), (2,2,2.0,), ())
        def t15(demo=self.demo3): demo((), (), (2,'x',2.0,))
        def t16(demo=self.demo3): demo((), (), (3, (3,),))
        def t17(demo=self.demo3): demo((), (), (3, ('x', ('y',),),))

        for t in (t5, t6, t7, t8, t9, t10, t11, t12, t13, t14, t15, t16, t17):
            self.assertRaises(TypeError, t)

    def demo4(self, dict1, dict2, dict3, dict4):
        assert chktype(1, dict1, {})
        assert chktype(2, dict2, {types.IntType: [types.IntType]})
        assert chktype(3, dict3, {types.IntType: [types.StringType,
                                                  types.IntType],
                                  types.FloatType: [types.FloatType]})
        assert chktype(4, dict4, {(types.IntType,): [(), []],
                                  ((),): [(types.IntType,)]})
                      
    def testDicts(self):
        # These should not raise exceptions:
        def t1(demo=self.demo4): demo({}, {}, {}, {})
        def t2(demo=self.demo4): demo({1:'x', 'x':1}, {}, {}, {})
        def t3(demo=self.demo4): demo({}, {1:2, 3:5}, {}, {})
        def t4(demo=self.demo4): demo({}, {}, {1:'x', 1:3, 1:0,
                                               1.0:2.0, -.2:0.0}, {})
        def t5(demo=self.demo4): demo({}, {}, {}, {(2,3): ('x',2),
                                                   (2,3): ['x',2],
                                                   ((3,'x'),): (1,3)})
        t1(), t2(), t3(), t5()

        # These should raise exceptions:
        def t6(demo=self.demo4): demo([], {}, {}, {})
        def t7(demo=self.demo4): demo({}, [], {}, {})
        def t8(demo=self.demo4): demo({}, {}, [], {})
        def t9(demo=self.demo4): demo({}, {}, {}, [])
        
        def t10(demo=self.demo4): demo({}, {1:'x'}, {}, {})
        def t11(demo=self.demo4): demo({}, {'x':1}, {}, {})
        def t12(demo=self.demo4): demo({}, {'x':'x'}, {}, {})
        
        def t13(demo=self.demo4): demo({}, {}, {1:1.0}, {})
        def t14(demo=self.demo4): demo({}, {}, {1.0:1}, {})
        def t15(demo=self.demo4): demo({}, {}, {1.0:'x'}, {})

        def t16(demo=self.demo4): demo({}, {}, {}, {(): 2})
        def t17(demo=self.demo4): demo({}, {}, {}, {3: ()})
        def t18(demo=self.demo4): demo({}, {}, {}, {((),): [33]})

        for t in (t6, t7, t8, t9, t10, t11, t12, t13, t14, t15, t16, t17, t18):
            self.assertRaises(TypeError, t)
    
def testsuite():
    """
    Return a PyUnit testsuite for the chktype module.
    """
    
    tests = unittest.TestSuite()

    chktypetests = unittest.makeSuite(ChktypeTestCase, 'test')
    tests = unittest.TestSuite( (tests, chktypetests) )

    return tests

def test():
    import unittest
    runner = unittest.TextTestRunner()
    runner.run(testsuite())

if __name__ == '__main__':
    test()
