# Natural Language Toolkit: Classifier Interface
#
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
#         Dan Garrette <dhgarrette@gmail.com>
#
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Interfaces for provers.
"""

class ProverI(object):
    """
    Interface for trying to establish a proof from assumptions.
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
    Interface for trying to establish a model of a counterexample for a theorem
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
    