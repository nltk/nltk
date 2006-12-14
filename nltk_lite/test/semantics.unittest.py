from nltk_lite.semantics import *
from nltk_lite.semantics import logic

import unittest

class TestModels(unittest.TestCase):
    """
    Unit tests for the L{Model} class.
    """

    def testLogicSelectors(self):
        "Tests for properties of formulae from 'logic' module."
        v = Valuation()
        m = Model(set([]), v)

        # Existential quantification
        pair = m.decompose('some x.(M N)')
        self.assertEqual(pair[0], ('some', 'x'))
        self.assertEqual(pair[1], '(M N)')

        # Universal quantification
        pair = m.decompose('all x.(M N)')
        self.assertEqual(pair[0], ('all', 'x'))
        self.assertEqual(pair[1], '(M N)')

        # Boolean operators
        pair = m.decompose('(and (M N) (P Q))')
        self.assertEqual(pair[0], 'and')
        self.assertEqual(pair[1], ['(M N)', '(P Q)'])

        pair = m.decompose('(not M N P Q)')
        self.assertEqual(pair[0], 'not')
        self.assertEqual(pair[1], ['M', 'N', 'P', 'Q'])

        # Just an application expression
        pair = m.decompose('(M N P)')
        self.assertEqual(pair[0], '(M N)')
        self.assertEqual(pair[1], 'P')
        

    def testValuations(self):
        "Tests for characteristic functions and valuations."
        cf = CharFun({'d1' : {'d1': True, 'd2': True}, 'd2' : {'d1': True}})
 

        self.assertEqual(cf['d1'], {'d1': True, 'd2': True})
        self.assertEqual(cf['d1']['d2'], True)
        # doesn't work since cf not called on 'foo'
        ## self.assertRaises(KeyError, cf['foo'])
        ## self.assertRaises(KeyError, cf['d1']['foo'])

        self.assertEqual(flatten(cf), set(['d1', 'd2']))
        self.assertEqual(flatten(cf), cf.domain)


        s1 = set([('d1', 'd2'), ('d1', 'd1'), ('d2', 'd1')])
        cf1 = CharFun()
        cf1.read(s1)
        self.assertEqual(cf, cf1)
        
        self.assertEqual(cf1.tuples(), s1)
        
        s2 = set([('d1', 'd2'), ('d1', 'd2'), ('d1', 'd1'), ('d2', 'd1')])
        cf2 = CharFun()
        cf2.read(s2)
        self.assertEqual(cf1, cf2)

        unary = set(['d1', 'd2'])
        cf.read(unary)
        self.assertEqual(cf, {'d2': True, 'd1': True})

        wrong = set([('d1', 'd2'), ('d2', 'd1', 'd3')])
        self.assertRaises(ValueError, cf.read, wrong)

        val = Valuation({'Fido' : 'd1', 'dog' : {'d1' : True, 'd2' : True}})
        self.assertEqual(val['dog'], cf)
        self.assertEqual(val['dog'][val['Fido']], True)
        self.assertEqual(val.domain, set(['d1', 'd2']))
        self.assertEqual(val.symbols, ['Fido', 'dog'])
        
        setval = [('Fido', 'd1'), ('dog', set(['d1', 'd2']))]
        val1 = Valuation()
        val1.read(setval)
        self.assertEqual(val, val1)

        val1 = Valuation({'love': {'g1': {'b1': True}, 'b1': {'g1': True}, 'b2': {'g2': True}, 'g2': {'b1': True}}})
        love1 = val1['love']
        relation = set([('b1', 'g1'),  ('g1', 'b1'), ('g2', 'b2'), ('b1', 'g2')])
        self.assertEqual(love1.tuples(), relation)
        val2 = Valuation()
        val2.read([('love', set([('b1', 'g1'), ('g1', 'b1'), ('g2', 'b2'), ('b1', 'g2')]))])
        love2 = val2['love']
        self.assertEqual(love1.tuples(), love2.tuples())
                        

    def testFunArgApp(self):
        "Tests for function argument application in a Model"
        val = Valuation()
        v = [('adam', 'b1'), ('betty', 'g1'), ('fido', 'd1'),\
             ('girl', set(['g1', 'g2'])), ('boy', set(['b1', 'b2'])), ('dog', set(['d1'])),
             ('love', set([('b1', 'g1'), ('b2', 'g2'), ('g1', 'b1'), ('g2', 'b1')]))]
        val.read(v)
        dom = val.domain
        m = Model(dom, val)
        g = Assignment(dom)

        self.assertEqual(m.app(val['boy'], 'b1'), True)
        self.assertEqual(m.app(val['boy'], 'g1'), False)
        self.assertRaises(Undefined, m.app, val['boy'], 'foo')
        

    def testBBModelCheck(self):
        "Test the model checking with Blackburn & Bos testsuite"
        val1 = Valuation()
        v1 = [('jules', 'd1'), ('vincent', 'd2'), ('pumpkin', 'd3'),
              ('honey_bunny', 'd4'), ('yolanda', 'd5'),
              ('customer', set(['d1', 'd2'])),
              ('robber', set(['d3', 'd4'])),
              ('love', set([('d3', 'd4')]))]
        val1.read(v1)
        dom1 = val1.domain
        m1 = Model(dom1, val1)
        g1 = Assignment(dom1)

        val2 = Valuation()
        v2 = [('jules', 'd1'), ('vincent', 'd2'), ('pumpkin', 'd3'),
              ('honey_bunny', 'd4'), ('yolanda', 'd4'),
              ('customer', set(['d1', 'd2', 'd5', 'd6'])),
              ('robber', set(['d3', 'd4'])),
              ('love', set())]
        val2.read(v2)
        dom2 = set(['d1', 'd2', 'd3', 'd4', 'd5', 'd6'])
        m2 = Model(dom2, val2)
        g2 = Assignment(dom2)
        g21 = Assignment(dom2)
        g21.add('d3', 'y')

        val3 = Valuation()
        v3 = [('mia', 'd1'), ('jody', 'd2'), ('jules', 'd3'),
              ('vincent', 'd4'),
              ('woman', set(['d1', 'd2'])), ('man', set(['d3', 'd4'])),
              ('joke', set(['d5', 'd6'])), ('episode', set(['d7', 'd8'])),
              ('in', set([('d5', 'd7'), ('d5', 'd8')])),
              ('tell', set([('d1', 'd5'), ('d2', 'd6')]))]
        val3.read(v3)
        dom3 = set(['d1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7', 'd8'])
        m3 = Model(dom3, val3)
        g3 = Assignment(dom3)

        tests = [
            ('some x. (robber x)', m1, g1, True),
            ('some x. some y. (love x y)', m1, g1, True),
            ('some x0. some x1. (love x0 x1)', m2, g2, False),
            ('all x. all y. (love x y)', m2, g2, False),
            ('(not all x. all y. (love x y))', m2, g2, True),
            ('all x. all y. (not (love x y))', m2, g2, True),
            ('(yolanda = honey_bunny)', m2, g2, True),
            ('(mia = honey_bunny)', m2, g2, 'Undefined'),
            ('(not (yolanda = honey_bunny))', m2, g2, False),
            ('(not (mia = honey_bunny))', m2, g2, 'Undefined'),
            ('all x. ((robber x) or (customer x))', m2, g2, True),
            ('(not all x. ((robber x) or (customer x)))', m2, g2, False),
            ('((robber x) or (customer x))', m2, g2, 'Undefined'),
            ('((robber y) or (customer y))', m2, g21, True),
            ('some x. ((man x) and some x. (woman x))', m3, g3, True),
            ('(some x. (man x) and some x. (woman x))', m3, g3, True),
            ('(not some x. (woman x))', m3, g3, False),
            ('some x. ((tasty x) and (burger x))', m3, g3, 'Undefined'),
            ('(not some x. ((tasty x) and (burger x)))', m3, g3, 'Undefined'),
            ('some x. ((man x) and (not some y. (woman y)))', m3, g3, False),
            ('some x. ((man x) and (not some x. (woman x)))', m3, g3, False),
            ('some x. ((woman x) and (not some x. (customer x)))', m2, g2, 'Undefined'),
        ]

        for item in tests:
            sentence, model, g, testvalue = item
            semvalue = model.evaluate(sentence, g)
            self.assertEqual(semvalue, testvalue)
            g.purge()

         
def testsuite():
    suite = unittest.makeSuite(TestModels)
    return unittest.TestSuite(suite)

def test(verbosity):
    runner = unittest.TextTestRunner(verbosity=verbosity)
    runner.run(testsuite())

if __name__ == "__main__":

    test(verbosity=2) 
