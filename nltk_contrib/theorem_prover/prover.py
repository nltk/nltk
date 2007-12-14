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


def demo_drt_glue_remove_duplicates():
    from nltk_contrib.gluesemantics import drt_glue
    drt_glue.demo(remove_duplicates=True)

def demo():
    from nltk_contrib.drt import DRT

    DRT.testTp_equals()
    print '\n'
#    demo_drt_glue_remove_duplicates()
#    print '\n'
    lp = LogicParser()
    a = lp.parse(r'some x.((man x) and (walks x))')
    b = lp.parse(r'some x.((walks x) and (man x))')
    bicond = ApplicationExpression(ApplicationExpression(Operator('iff'), a), b)
    print "Trying to prove:\n '%s <-> %s'" % (a.infixify(), b.infixify())
    print 'tableau: %s' % attempt_proof(bicond, 'tableau')
    print 'Prover9: %s' % attempt_proof(bicond, 'Prover9')

if __name__ == '__main__': 
    demo()
