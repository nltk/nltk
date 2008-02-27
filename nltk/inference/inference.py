# Natural Language Toolkit: Interface to Theorem Provers 
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#         Ewan Klein <ewan@inf.ed.ac.uk>
#
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

from nltk.sem.logic import ApplicationExpression, Operator, LogicParser
import tableau
import prover9
import mace

"""
A wrapper module that calls theorem provers and model builders.
"""

def get_prover(goal=None, assumptions=[], prover_name='Prover9'):
    """
    @param goal: Input expression to prove
    @type goal: L{logic.Expression}
    @param assumptions: Input expressions to use as assumptions in the proof
    @type assumptions: L{list} of logic.Expression objects
    """
    if prover_name.lower() == 'tableau':
        prover_module = tableau.Tableau
    elif prover_name.lower() == 'prover9':
        prover_module = prover9.Prover9
    
    return prover_module(goal, assumptions)

def get_model_builder(goal=None, assumptions=[], model_builder_name='Mace'):
    """
    @param goal: Input expression to prove
    @type goal: L{logic.Expression}
    @param assumptions: Input expressions to use as assumptions in the proof
    @type assumptions: L{list} of logic.Expression objects
    """
    if model_builder_name.lower() == 'mace':
        builder_module = mace.Mace
    
    return builder_module(goal, assumptions)

def demo_drt_glue_remove_duplicates(show_example=-1):
    from nltk_contrib.gluesemantics import drt_glue
    examples = ['David sees Mary',
                'David eats a sandwich',
                'every man chases a dog',
                'John chases himself',
                'John likes a cat',
                'John likes every cat',
                'he likes a dog',
                'a dog walks and he leaves']

    example_num = 0
    hit = False
    for sentence in examples:
        if example_num==show_example or show_example==-1:
            print '[[[Example %s]]]  %s' % (example_num, sentence)
            readings = drt_glue.parse_to_meaning(sentence, True)
            for j in range(len(readings)):
                reading = readings[j].simplify().resolve_anaphora()
                print reading
            print ''
            hit = True
        example_num += 1
    if not hit:
        print 'example not found'
  
def demo():
    from nltk_contrib.drt import DRT

    DRT.testTp_equals()
    print '\n'
    
    lp = LogicParser()
    a = lp.parse(r'some x.((man x) and (walks x))')
    b = lp.parse(r'some x.((walks x) and (man x))')
    bicond = ApplicationExpression(ApplicationExpression(Operator('iff'), a), b)
    print "Trying to prove:\n '%s <-> %s'" % (a.infixify(), b.infixify())
    print 'tableau: %s' % get_prover(bicond, prover_name='tableau').prove()
    print 'Prover9: %s' % get_prover(bicond, prover_name='Prover9').prove()
    print '\n'
    
    demo_drt_glue_remove_duplicates()

    lp = LogicParser()
    a = lp.parse(r'all x.((man x) implies (mortal x))')
    b = lp.parse(r'(man socrates)')
    c1 = lp.parse(r'(mortal socrates)')
    c2 = lp.parse(r'(not (mortal socrates))')

    print get_prover(c1, [a,b], 'prover9').prove()
    print get_prover(c2, [a,b], 'prover9').prove()
    print get_model_builder(c1, [a,b], 'mace').build_model()
    print get_model_builder(c2, [a,b], 'mace').build_model()

if __name__ == '__main__': 
    demo()
