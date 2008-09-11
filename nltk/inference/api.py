# Natural Language Toolkit: Classifier Interface
#
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
#         Dan Garrette <dhgarrette@gmail.com>
#
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT

"""
Interfaces and base classes for theorem provers and model builders.

L{Prover} is a standard interface for a theorem prover which tries to prove a goal from a 
list of assumptions.

L{ModelBuilder} is a standard interface for a model builder. Given just a set of assumptions.
the model builder tries to build a model for the assumptions. Given a set of assumptions and a 
goal M{G}, the model builder tries to find a counter-model, in the sense of a model that will satisfy
the assumptions plus the negation of M{G}. 
"""

import threading
import time

class Prover(object):
    """
    Interface for trying to prove a goal from assumptions.  Both the goal and 
    the assumptions are constrained to be formulas of L{logic.Expression}.
    """
    def prove(self, goal=None, assumptions=None, verbose=False):
        """
        @return: Whether the proof was successful or not.
        @rtype: C{bool} 
        """
        raise NotImplementedError()

    
class ModelBuilder(object):
    """
    Interface for trying to build a model of set of formulas.
    Open formulas are assumed to be universally quantified.
    Both the goal and the assumptions are constrained to be formulas 
    of L{logic.Expression}.
    """
    def build_model(self, goal=None, assumptions=None, verbose=False):
        """
        Perform the actual model building.
        @return: A model if one is generated; None otherwise.
        @rtype: C{nltk.sem.evaluate.Valuation} 
        """
        raise NotImplementedError()


class TheoremToolCommand(object):
    """
    This class holds a goal and a list of assumptions to be used in proving
    or model building.
    """
    def add_assumptions(self, new_assumptions):
        """
        Add new assumptions to the assumption list.
        
        @param new_assumptions: new assumptions
        @type new_assumptions: C{list} of C{Expression}s
        """
        raise NotImplementedError()
    
    def retract_assumptions(self, retracted, debug=False):
        """
        Retract assumptions from the assumption list.
        
        @param debug: If True, give warning when C{retracted} is not present on 
        assumptions list.
        @type debug: C{bool}
        @param retracted: assumptions to be retracted
        @type retracted: C{list} of L{sem.logic.Expression}s
        """
        raise NotImplementedError()
    
    def assumptions(self):
        """
        List the current assumptions.
        
        @return: C{list} of C{Expression}       
        """
        raise NotImplementedError()
    
    def goal(self):
        """
        Return the goal
        
        @return: C{Expression}
        """
        raise NotImplementedError()
        
    def print_assumptions(self):
        """
        Print the list of the current assumptions.       
        """
        raise NotImplementedError()
    

class ProverCommand(TheoremToolCommand):
    """
    This class holds a C{Prover}, a goal, and a list of assumptions.  When
    prove() is called, the C{Prover} is executed with the goal and assumptions.
    """
    def prove(self, verbose=False):
        """
        Perform the actual proof.
        """
        raise NotImplementedError()

    def proof(self, simplify=True):
        """
        Return the proof string
        @param simplify: C{boolean} simplify the proof?
        @return: C{str}
        """
        raise NotImplementedError()

    def get_prover(self):
        """
        Return the prover object
        @return: C{Prover}
        """
        raise NotImplementedError()


class ModelBuilderCommand(TheoremToolCommand):
    """
    This class holds a C{ModelBuilder}, a goal, and a list of assumptions.  
    When build_model() is called, the C{ModelBuilder} is executed with the goal 
    and assumptions.
    """
    def build_model(self, verbose=False):
        """
        Perform the actual model building.
        @return: A model if one is generated; None otherwise.
        @rtype: C{nltk.sem.evaluate.Valuation} 
        """
        raise NotImplementedError()
    
    def model(self, format=None):
        """
        Return a string representation of the model
        
        @param simplify: C{boolean} simplify the proof?
        @return: C{str}
        """
        raise NotImplementedError()

    def get_model_builder(self):
        """
        Return the model builder object
        @return: C{ModelBuilder}
        """
        raise NotImplementedError()


class BaseTheoremToolCommand(TheoremToolCommand):
    """
    This class holds a goal and a list of assumptions to be used in proving
    or model building.
    """
    def __init__(self, goal=None, assumptions=None):
        """
        @param goal: Input expression to prove
        @type goal: L{logic.Expression}
        @param assumptions: Input expressions to use as assumptions in 
            the proof.
        @type assumptions: C{list} of L{logic.Expression}
        """
        self._goal = goal
        """The logic expression to prove.
           L{logic.Expression}"""
        
        if not assumptions:
            assumptions = []
            
        self._assumptions = list(assumptions)
        """The set of expressions to use as assumptions in the proof.
           C{list} of L{logic.Expression}"""
           
        self._result = None
        """A holder for the result, so prevent unnecessary re-proving"""
        
    def add_assumptions(self, new_assumptions):
        """
        Add new assumptions to the assumption list.
        
        @param new_assumptions: new assumptions
        @type new_assumptions: C{list} of L{sem.logic.Expression}s
        """
        self._assumptions += new_assumptions
        self._result = None
    
    def retract_assumptions(self, retracted, debug=False):
        """
        Retract assumptions from the assumption list.
        
        @param debug: If True, give warning when C{retracted} is not present on 
        assumptions list.
        @type debug: C{bool}
        @param retracted: assumptions to be retracted
        @type retracted: C{list} of L{sem.logic.Expression}s
        """
        result_list = [a for a in self._assumptions if a not in set(retracted)]
        if debug and result_list == self._assumptions:
            print Warning("Assumptions list has not been changed:")
            self.print_assumptions()
            
        self._assumptions = result_list
        
        self._result = None
    
    def assumptions(self):
        """
        List the current assumptions.
        
        @return: C{list} of C{Expression}       
        """
        return self._assumptions
    
    def goal(self):
        """
        Return the goal
        
        @return: C{Expression}
        """
        return self._goal
        
    def print_assumptions(self):
        """
        Print the list of the current assumptions.       
        """
        for a in self.assumptions():
            print a


class BaseProverCommand(BaseTheoremToolCommand, ProverCommand):
    """
    This class holds a C{Prover}, a goal, and a list of assumptions.  When
    prove() is called, the C{Prover} is executed with the goal and assumptions.
    """
    def __init__(self, prover, goal=None, assumptions=None):
        """
        @param prover: The theorem tool to execute with the assumptions
        @type prover: C{Prover}
        @see: C{BaseTheoremToolCommand}
        """
        self._prover = prover
        """The theorem tool to execute with the assumptions"""
        
        BaseTheoremToolCommand.__init__(self, goal, assumptions)
        
        self._proof = None

    def prove(self, verbose=False):
        """
        Perform the actual proof.  Store the result to prevent unnecessary
        re-proving.
        """
        if self._result is None:
            self._result, self._proof = self._prover.prove(self.goal(), 
                                                           self.assumptions(),
                                                           verbose)
        return self._result

    def proof(self, simplify=True):
        """
        Return the proof string
        @param simplify: C{boolean} simplify the proof?
        @return: C{str}
        """
        if self._result is None:
            raise LookupError("You have to call prove() first to get a proof!")
        else:
            return self.decorate_proof(self._proof, simplify)

    def decorate_proof(self, proof_string, simplify=True):
        """
        Modify and return the proof string
        @param proof_string: C{str} the proof to decorate
        @param simplify: C{boolean} simplify the proof?
        @return: C{str}
        """
        return proof_string

    def get_prover(self):
        return self._prover

    
class BaseModelBuilderCommand(BaseTheoremToolCommand, ModelBuilderCommand):
    """
    This class holds a C{ModelBuilder}, a goal, and a list of assumptions.  When
    build_model() is called, the C{ModelBuilder} is executed with the goal and 
    assumptions.
    """
    def __init__(self, modelbuilder, goal=None, assumptions=None):
        """
        @param modelbuilder: The theorem tool to execute with the assumptions
        @type modelbuilder: C{ModelBuilder}
        @see: C{BaseTheoremToolCommand}
        """
        self._modelbuilder = modelbuilder
        """The theorem tool to execute with the assumptions"""
        
        BaseTheoremToolCommand.__init__(self, goal, assumptions)
        
        self._valuation = None

    def build_model(self, verbose=False):
        """
        Attempt to build a model.  Store the result to prevent unnecessary
        re-building.
        """
        if self._result is None:
            self._result, self._valuation = \
                    self._modelbuilder.build_model(self.goal(), 
                                                   self.assumptions(),
                                                   verbose)
        return self._result
    
    def model(self, format=None):
        """
        Return a string representation of the model
        
        @param simplify: C{boolean} simplify the proof?
        @return: C{str}
        """
        if self._result is None:
            raise LookupError('You have to call build_model() first to '
                              'get a model!')
        else:
            return self.decorate_model(self._valuation, format)
        
    def decorate_model(self, valuation_str, format=None):
        """
        @param valuation_str: C{str} with the model builder's output 
        @param format: C{str} indicating the format for displaying
        @return: C{str}
        """
        return valuation_str

    def get_model_builder(self):
        return self._modelbuilder


class TheoremToolCommandDecorator(object):
    """
    A base decorator for the C{ProverCommandDecorator} and 
    C{ModelBuilderCommandDecorator} classes from which decorators can extend.
    """
    def __init__(self, command):
        """
        @param command: C{TheoremToolCommand} to decorate
        """
        self._command = command

        #The decorator has its own versions of 'result' different from the 
        #underlying command
        self._result = None
        
    def assumptions(self):
        return self._command.assumptions()
    
    def goal(self):
        return self._command.goal()
        
    def add_assumptions(self, new_assumptions):
        self._command.add_assumptions(new_assumptions)
        self._result = None
    
    def retract_assumptions(self, retracted, debug=False):
        self._command.retract_assumptions(retracted, debug)
        self._result = None
    
    def print_assumptions(self):
        self._command.print_assumptions()


class ProverCommandDecorator(TheoremToolCommandDecorator, ProverCommand):
    """
    A base decorator for the C{ProverCommand} class from which other 
    prover command decorators can extend.
    """
    def __init__(self, proverCommand):
        """
        @param proverCommand: C{ProverCommand} to decorate
        """
        TheoremToolCommandDecorator.__init__(self, proverCommand)

        #The decorator has its own versions of 'result' and 'proof'
        #because they may be different from the underlying command
        self._proof = None
        
    def prove(self, verbose=False):
        if self._result is None:
            prover = self.get_prover()
            self._result, self._proof = prover.prove(self.goal(), 
                                                     self.assumptions(), 
                                                     verbose)
        return self._result
    
    def proof(self, simplify=True):
        """
        Return the proof string
        @param simplify: C{boolean} simplify the proof?
        @return: C{str}
        """
        if self._result is None:
            raise LookupError("You have to call prove() first to get a proof!")
        else:
            return self.decorate_proof(self._proof, simplify)
    
    def decorate_proof(self, proof_string, simplify=True):
        """
        Modify and return the proof string
        @param proof_string: C{str} the proof to decorate
        @param simplify: C{boolean} simplify the proof?
        @return: C{str}
        """
        return self._command.decorate_proof(proof_string, simplify)

    def get_prover(self):
        return self._command.get_prover()
    

class ModelBuilderCommandDecorator(ModelBuilderCommand):
    """
    A base decorator for the C{ModelBuilderCommand} class from which other 
    prover command decorators can extend.
    """
    def __init__(self, modelBuilderCommand):
        """
        @param modelBuilderCommand: C{ModelBuilderCommand} to decorate
        """
        TheoremToolCommandDecorator.__init__(self, modelBuilderCommand)

        #The decorator has its own versions of 'result' and 'valuation' 
        #because they may be different from the underlying command
        self._valuation = None
        
    def build_model(self, verbose=False):
        """
        Attempt to build a model.  Store the result to prevent unnecessary
        re-building.
        """
        if self._result is None:
            modelbuilder = self.get_model_builder()
            self._result, self._valuation = \
                            modelbuilder.build_model(self.goal(), 
                                                     self.assumptions(),
                                                     verbose)
        return self._result
    
    def model(self, format=None):
        """
        Return a string representation of the model
        
        @param simplify: C{boolean} simplify the proof?
        @return: C{str}
        """
        if self._result is None:
            raise LookupError('You have to call build_model() first to '
                              'get a model!')
        else:
            return self.decorate_model(self._valuation, format)
    
    def decorate_model(self, valuation_str, format=None):
        """
        Modify and return the proof string
        @param valuation_str: C{str} with the model builder's output 
        @param format: C{str} indicating the format for displaying
        @return: C{str}
        """
        return self._command.decorate_model(valuation_str, format)

    def get_model_builder(self):
        return self._command.get_prover()
    

class ParallelProverBuilderCommand(BaseProverCommand, BaseModelBuilderCommand):
    """
    This command stores both a prover and a model builder and when either 
    prove() or build_model() is called, then both theorem tools are run in
    parallel.  Whichever finishes first, the prover or the model builder, is the
    result that will be used.
    
    Because the theorem prover result is the opposite of the model builder
    result, we will treat self._result as meaning "proof found/no model found".
    """
    def __init__(self, prover, modelbuilder, goal=None, assumptions=None):
        BaseProverCommand.__init__(self, prover, goal, assumptions)
        BaseModelBuilderCommand.__init__(self, modelbuilder, goal, assumptions)
    
    def prove(self, verbose=False):
        """
        Perform the actual proof.  
        """
        return self._run(verbose)

    def build_model(self, verbose=False):
        return not self._run(verbose)
    
    def _run(self, verbose):
        # Set up two thread, Prover and ModelBuilder to run in parallel
        tp_result = [None]
        tp_thread = TheoremToolThread(lambda: BaseProverCommand.prove(self, verbose), tp_result, verbose, 'TP')
        mb_result = [None]
        mb_thread = TheoremToolThread(lambda: BaseModelBuilderCommand.build_model(self, verbose), mb_result, verbose, 'MB')
        
        tp_thread.start()
        mb_thread.start()
        
        while tp_result[0] is None and mb_result[0] is None:
            # wait until either the prover or the model builder is done
            pass
    
        if tp_result[0] is not None:
            self._result = tp_result[0]
        else:
            self._result = not mb_result[0]
        return self._result

    
class TheoremToolThread(threading.Thread):
    def __init__(self, command, result, verbose, name=None):
        self.command = command
        self.result = result
        self.verbose = verbose
        self.name = name
        threading.Thread.__init__(self)
        
    def run(self):
        self.result[0] = self.command()
        
        if self.verbose: 
            print 'Thread %s finished with result %s at %s' % \
                  (self.name, self.result[0], time.localtime(time.time()))
