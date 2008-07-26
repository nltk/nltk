# Natural Language Toolkit: Interface to Theorem Provers 
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#         Ewan Klein <ewan@inf.ed.ac.uk>
#
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT

from nltk.sem import logic 

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

def demo():
    lp = logic.LogicParser()
    a = lp.parse(r'some x.(man(x) and walks(x))')
    b = lp.parse(r'some x.(walks(x) and man(x))')
    bicond = logic.IffExpression(a, b)
    print "Trying to prove:\n '%s <-> %s'" % (a, b)
    print 'tableau: %s' % get_prover(bicond, prover_name='tableau').prove()
    print 'Prover9: %s' % get_prover(bicond, prover_name='Prover9').prove()
    print '\n'
    
    lp = logic.LogicParser()
    a = lp.parse(r'all x.(man(x) -> mortal(x))')
    b = lp.parse(r'man(socrates)')
    c1 = lp.parse(r'mortal(socrates)')
    c2 = lp.parse(r'-mortal(socrates)')

    print get_prover(c1, [a,b], 'prover9').prove()
    print get_prover(c2, [a,b], 'prover9').prove()
    print get_model_builder(c1, [a,b], 'mace').build_model()
    print get_model_builder(c2, [a,b], 'mace').build_model()

if __name__ == '__main__': 
    demo()
