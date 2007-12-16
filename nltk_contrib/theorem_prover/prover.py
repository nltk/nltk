# Natural Language Toolkit: Interface to Theorem Provers 
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#              Ewan Klein <ewan@inf.ed.ac.uk>

# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

from nltk.sem.logic import ApplicationExpression, Operator, LogicParser

from nltk_contrib.theorem_prover import tableau, prover9

def attempt_proof(expression, prover_name='Prover9'):
    """
    Try to prove an expression of First Order Logic. 
    
    @param expression: Input expression to prove
    @type expression: L{logic.Expression}
    @type prover_name: C{str}
    @param prover_name: Name of the prover to use.
    
    """
    #assert isinstance(expression, DRT.Expression)

    if prover_name == 'tableau':
        return tableau.attempt_proof(expression)
    
    elif prover_name == 'Prover9':
        return prover9.attempt_proof(expression)


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
    print 'tableau: %s' % attempt_proof(bicond, 'tableau')
    print 'Prover9: %s' % attempt_proof(bicond, 'Prover9')
    
    demo_drt_glue_remove_duplicates()
    print '\n'
    
if __name__ == '__main__': 
    demo()
