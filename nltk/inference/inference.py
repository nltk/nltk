# Natural Language Toolkit: Interface to Theorem Provers 
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#         Ewan Klein <ewan@inf.ed.ac.uk>
#
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT

from nltk.sem import logic 

import api
import tableau
import prover9
import mace
import resolution

"""
A wrapper module that calls theorem provers and model builders.
"""

def get_prover(goal=None, assumptions=None, prover_name=None):
    """
    @param goal: Input expression to prove
    @type goal: L{logic.Expression}
    @param assumptions: Input expressions to use as assumptions in the proof
    @type assumptions: L{list} of logic.Expression objects
    """
    if not prover_name:
        prover_name = 'Prover9'
    
    if prover_name.lower() == 'tableau':
        return api.BaseProverCommand(tableau.Tableau(), goal, assumptions)
    elif prover_name.lower() == 'prover9':
        return prover9.Prover9Command(goal, assumptions)
    elif prover_name.lower() == 'resolution':
        return resolution.ResolutionCommand(goal, assumptions)
    
    raise Exception('\'%s\' is not a valid prover name' % prover_name)

def get_model_builder(goal=None, assumptions=None, model_builder_name=None):
    """
    @param goal: Input expression to prove
    @type goal: L{logic.Expression}
    @param assumptions: Input expressions to use as assumptions in the proof
    @type assumptions: L{list} of logic.Expression objects
    """
    if not model_builder_name:
        model_builder_name = 'Mace'
    
    if model_builder_name.lower() == 'mace':
        return mace.MaceCommand(goal, assumptions)

def get_parallel_prover_builder(goal=None, assumptions=None, 
                                prover_name='', model_builder_name=''):
    prover = get_prover(prover_name=prover_name)
    model_builder = get_model_builder(model_builder_name=model_builder_name)
    return api.ParallelProverBuilderCommand(prover.get_prover(), 
                                            model_builder.get_model_builder(),
                                            goal, assumptions)

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

    print get_parallel_prover_builder(c1, [a,b]).prove(True)
    print get_parallel_prover_builder(c1, [a,b]).build_model(True)

if __name__ == '__main__': 
    demo()
