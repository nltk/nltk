# Natural Language Toolkit: Interface to Theorem Provers 
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#         Ewan Klein <ewan@inf.ed.ac.uk>
#
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

from nltk.sem.logic import ApplicationExpression, Operator, LogicParser

from nltk_contrib.theorem_prover import tableau, prover9

def prove(goal, assumptions=[], prover_name='Prover9'):
    """
    Try to prove a theorem of First Order Logic. 
    
    @param goal: Input expression to prove
    @type goal: L{logic.Expression}
    @param assumptions: Input expressions to use as assumptions in the proof
    @type assumptions: C{list} of L{logic.Expression} objects
    @type prover_name: C{str}
    @param prover_name: Name of the prover to use.

    """

    if prover_name == 'tableau':
        prover_module = tableau.Tableau
    elif prover_name.lower() == 'prover9':
        prover_module = prover9.Prover9

    prover = prover_module(goal)
    prover.add_assumptions(assumptions)
    return prover.prove()

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
    print 'tableau: %s' % prove(bicond, prover_name='tableau')
    print 'Prover9: %s' % prove(bicond, prover_name='Prover9')
    print '\n'
    
    demo_drt_glue_remove_duplicates()

if __name__ == '__main__': 
    demo()
