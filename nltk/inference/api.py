# Natural Language Toolkit: Classifier Interface
#
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
#         Dan Garrette <dhgarrette@gmail.com>
#
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Interfaces for theorem provers and model builders.

L{ProverI} is a standard interace for a theorem prover which tries to prove a goal from a 
list of assumptions.

L{ModelBuilderI} is a standard interace for a model builder. Given just a set of assumptions.
the model builder tries to build a model for the assumptions. Given a set of assumptions and a 
goal M{G}, the model builder tries to find a counter-model, in the sense of a model that will satisfy
the assumptions plus the negation of M{G}. 
"""

class ProverI(object):
    """
    Interface for trying to prove a goal from assumptions. 
    Both the goal and the assumptions are 
    constrained to be formulas of L{logic.Expression}.
    """
    
    def prove(self):
        """
        @return: Whether the proof was successful or not.
        @rtype: C{bool} 
        """
        raise NotImplementedError()
    
    def add_assumptions(self, assumptions):
        """
        @param assumptions: Assumptions for the proof
        @type assumptions: C{list} of strings
        """
        raise NotImplementedError('add_assumptions')
    
    
class ModelBuilderI(object):
    """
    Interface for trying to build a model of set of formulas.
    Open formulas are assumed to be universally quantified.
    Both the goal and the assumptions are 
    constrained to be formulas of L{logic.Expression}.
    """
    
    def model_found(self):
        """
        @return: Whether the model building was successful or not.
        @rtype: C{bool} 
        """
        raise NotImplementedError()
    
    def build_model(self):
        """
        @return: A model if one is generated; None otherwise.
        @rtype: C{nltk.sem.evaluate.Valuation} 
        """
        raise NotImplementedError()
    
    def add_assumptions(self, assumptions):
        """
        @param assumptions: Assumptions for the proof
        @type assumptions: C{list} of strings
        """
        raise NotImplementedError('add_assumptions')
    