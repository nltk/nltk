# Natural Language Toolkit: Nonmonotonic Reasoning
#
# Author: Daniel H. Garrette <dhgarrette@gmail.com>
#
# Copyright (C) 2001-2008 NLTK Project
# URL: <http://www.nltk.org>
# For license information, see LICENSE.TXT

"""
A module to perform nonmonotonic reasoning
"""

from nltk.sem.logic import *
from nltk.inference import inference
from nltk.inference.api import ProverI
from nltk import defaultdict

class NonmonotonicProver(ProverI):
    def __init__(self, goal=None, assumptions=[], prover_name='Prover9'):
        self._goal = goal
        self._assumptions = assumptions
        self._prover_name = prover_name
        
    def prove(self, debug=False):
        """
        @return: C{bool} Whether the proof was successful or not.
        """
        (goal, assumptions) = self.augmented_assumptions()
        
        prover = inference.get_prover(goal, assumptions, self._prover_name)
        result = prover.prove(debug)
        
        if debug:
            prover.show_proof()
        
        return result

class ClosedDomainProver(NonmonotonicProver):
    """
    This is a prover that adds domain closure assumptions before proving.
    """
    def augmented_assumptions(self):
        """
         - Domain = union([e.free(False) for e in all_expressions])
         - translate "exists x.P" to "(z=d1 | z=d2 | ... ) & P.replace(x,z)" or "P.replace(x, d1) | P.replace(x, d2) | ..."
         - translate "all x.P" to "P.replace(x, d1) & P.replace(x, d2) & ..."
        """
        assumptions = self._assumptions + [-self._goal]
        
        domain = set()
        for a in assumptions:
            domain |= (a.free(False) - a.free(True))
        
        assumptions1 = set()
        for a in assumptions:
            if isinstance(a, ExistsExpression):
                newterms = [a.term.replace(a.variable, VariableExpression(d)) for d in domain]
                assumptions1.add(reduce(Expression.__or__, newterms))
            else:
                assumptions1.add(a)
                
        assumptions2 = set()
        for a in assumptions1:
            if isinstance(a, AllExpression):
                for d in domain:
                    assumptions2.add(a.term.replace(a.variable, VariableExpression(d)))
            else:
                assumptions2.add(a)

        return (None, assumptions2)
    
class UniqueNamesProver(NonmonotonicProver):
    """
    This is a prover that adds unique names assumptions before proving.
    """
    def augmented_assumptions(self):
        """
         - Domain = union([e.free(False) for e in all_expressions])
         - if "d1 = d2" cannot be proven from the premises, then add "d1 != d2"
        """
        assumptions = self._assumptions
        
        domain = set()
        for a in assumptions:
            domain |= (a.free(False) - a.free(True))
        domain = sorted(list(domain))
        
        #build a dictionary of obvious equalities
        eq_dict = defaultdict(list)
        for a in assumptions:
            if isinstance(a, EqualityExpression):
                av = a.first.variable
                bv = a.second.variable
                if av < bv:
                    eq_dict[av].append(bv)
                else:
                    eq_dict[bv].append(av)
        
        assumptions2 = []
        for i,a in enumerate(domain):
            for b in domain[i+1:]:
                if b not in eq_dict[a]:
                    newEqEx = EqualityExpression(VariableExpression(a), 
                                                 VariableExpression(b))
                    if not inference.get_prover(newEqEx, assumptions).prove():
                        #if we can't prove it, then assume it's false
                        assumptions2.append(-newEqEx)
                
        return (self._goal, assumptions + assumptions2)

class ClosedWorldProver(NonmonotonicProver):
    """
    This is a prover that completes predicates before proving.

    If the premises don't logically entail "P(A)" then add "-P(A)"
    all x.(P(x) -> (x=A)) is the completion of P
    
    walk(Socrates)
    Socrates != Bill
    + all x.(walk(x) -> (x = Socrates))
    ----------------
    -walk(Bill)

    see(Socrates, John)
    see(John, Mary)
    Socrates != John
    John != Mary
    + all x.all y.(see(x,y) -> ((x=Socrates & y=John) | (x=John & y=Mary)))
    ----------------
    -see(Socrates, Mary)
    
    all x.(ostrich(x) -> bird(x))
    bird(Tweety)
    -ostrich(Sam)
    Sam != Tweety
    + all x.(bird(x) -> (ostrich(x) | x=Tweety))
    -------------------
    -bird(Sam)
    """ 
    def augmented_assumptions(self):
        assumptions = self._assumptions
        
        predicates = self._make_predicate_dict(assumptions)

        assumptions2 = []
        for p in predicates:
            new_sig = self._make_unique_signature(predicates[p])
            new_sig_exs = [IndividualVariableExpression(v) for v in new_sig]
            
            disjuncts = []
            for sig in predicates[p].signatures:
                equality_exs = []
                for i,v in enumerate(sig):
                    equality_exs.append(EqualityExpression(new_sig_exs[i],v)) 
                disjuncts.append(reduce(Expression.__and__, equality_exs))

            for prop in predicates[p].properties:
                #replace variables from the signature with new sig variables
                bindings = {}
                for i,v in enumerate(prop[0]):
                    bindings[v] = new_sig_exs[i]
                disjuncts.append(prop[1].substitute_bindings(bindings))

            #make the implication
            antecedent = self._make_antecedent(p, new_sig)
            consequent = reduce(Expression.__or__, disjuncts)
            accum = ImpExpression(antecedent, consequent)
            
            #quantify the implication
            for new_sig_var in new_sig[::-1]:
                accum = AllExpression(new_sig_var, accum)
            assumptions2.append(accum)
        
        return (self._goal, assumptions + assumptions2)
    
    def _make_unique_signature(self, predHolder):
        """
        This method figures out how many arguments the predicate takes and 
        returns a tuple containing that number of unique variables.
        """
        return tuple([unique_variable() 
                      for i in range(predHolder.signature_len)])
        
    def _make_antecedent(self, predicate, signature):
        antecedent = predicate
        for v in signature:
            antecedent = antecedent(IndividualVariableExpression(v))
        return antecedent

    def _make_predicate_dict(self, assumptions):
        """
        Create a dictionary of predicates from the assumptions.
        
        @param assumptions: a C{list} of C{Expression}s
        @return: C{dict} mapping C{VariableExpression}s to of C{PredHolder}s
        """
        predicates = defaultdict(PredHolder)
        for a in assumptions:
            self._map_predicates(a, predicates)
        return predicates

    def _map_predicates(self, expression, predDict):
        if isinstance(expression, ApplicationExpression):
            (func, args) = expression.uncurry()
            if isinstance(func, VariableExpression):
                predDict[func].append_sig(tuple(args))
        elif isinstance(expression, AndExpression):
            self._map_predicates(expression.first, predDict)
            self._map_predicates(expression.second, predDict)
        elif isinstance(expression, AllExpression):
            #collect all the universally quantified variables
            sig = [expression.variable]
            term = expression.term
            while isinstance(term, AllExpression):
                sig.append(term.variable)
                term = term.term
            if isinstance(term, ImpExpression):
                if isinstance(term.second, ApplicationExpression):
                    func = term.second.function
                    if isinstance(func, VariableExpression):
                        predDict[func].append_prop((tuple(sig), term.first))


class PredHolder(object):
    """
    This class will be used by a dictionary that will store information
    about predicates to be used by the C{ClosedWorldProver}.
    
    The 'signatures' property is a list of tuples defining signatures for 
    which the predicate is true.  For instance, 'see(john, mary)' would be 
    result in the signature '(john,mary)' for 'see'.
    
    The second element of the pair is a list of pairs such that the first
    element of the pair is a tuple of variables and the second element is an
    expression of those variables that makes the predicate true.  For instance,
    'all x.all y.(see(x,y) -> know(x,y))' would result in "((x,y),('see(x,y)'))"
    for 'know'.
    """
    def __init__(self):
        self.signatures = []
        self.properties = []
        self.signature_len = None
    
    def append_sig(self, new_sig):
        self.validate_sig_len(new_sig)
        self.signatures.append(new_sig)
        
    def append_prop(self, new_prop):
        self.validate_sig_len(new_prop[0])
        self.properties.append(new_prop)

    def validate_sig_len(self, new_sig):
        if self.signature_len is None:
            self.signature_len = len(new_sig)
        elif self.signature_len != len(new_sig):
            raise Exception("Signature lengths do not match")

    def __str__(self):
        return '(%s,%s,%s)' % (self.signatures, self.properties, 
                               self.signature_len)
        
    def __repr__(self):
        return str(self)

def closed_domain_demo():
    lp = LogicParser()
    
    p1 = lp.parse(r'exists x.walk(x)')
    p2 = lp.parse(r'man(Socrates)')
    c = lp.parse(r'walk(Socrates)')
    ClosedDomainProver(c, [p1,p2]).prove()

    p1 = lp.parse(r'exists x.walk(x)')
    p2 = lp.parse(r'man(Socrates)')
    p3 = lp.parse(r'man(Bill)')
    c = lp.parse(r'walk(Socrates)')
    ClosedDomainProver(c, [p1,p2,p3]).prove()

def unique_names_demo():
    lp = LogicParser()
    
    p1 = lp.parse(r'man(Socrates)')
    p2 = lp.parse(r'man(Bill)')
    c = lp.parse(r'exists x.exists y.(x != y)')
    print inference.get_prover(c, [p1,p2]).prove()
    unp = UniqueNamesProver(c, [p1,p2])
    for a in unp.augmented_assumptions()[1]: print a
    print unp.prove()

    p1 = lp.parse(r'all x.(walk(x) -> (x = Socrates))')
    p2 = lp.parse(r'Bill = William')
    p3 = lp.parse(r'Bill = Billy')
    c = lp.parse(r'-walk(William)')
    print inference.get_prover(c, [p1,p2,p3]).prove()
    unp = UniqueNamesProver(c, [p1,p2,p3], 'tableau')
    for a in unp.augmented_assumptions()[1]: print a
    print unp.prove()
    
def closed_world_demo():
    lp = LogicParser()
    
    p1 = lp.parse(r'walk(Socrates)')
    p2 = lp.parse(r'(Socrates != Bill)')
    c = lp.parse(r'-walk(Bill)')
    print inference.get_prover(c, [p1,p2]).prove()
    cwp = ClosedWorldProver(c, [p1,p2])
    for a in cwp.augmented_assumptions()[1]: print a
    print cwp.prove()

    p1 = lp.parse(r'see(Socrates, John)')
    p2 = lp.parse(r'see(John, Mary)')
    p3 = lp.parse(r'(Socrates != John)')
    p4 = lp.parse(r'(John != Mary)')
    c = lp.parse(r'-see(Socrates, Mary)')
    print inference.get_prover(c, [p1,p2,p3,p4]).prove()
    cwp = ClosedWorldProver(c, [p1,p2,p3,p4])
    for a in cwp.augmented_assumptions()[1]: print a
    print cwp.prove()

    p1 = lp.parse(r'all x.(ostrich(x) -> bird(x))')
    p2 = lp.parse(r'bird(Tweety)')
    p3 = lp.parse(r'-ostrich(Sam)')
    p4 = lp.parse(r'Sam != Tweety')
    c = lp.parse(r'-bird(Sam)')
    print inference.get_prover(c, [p1,p2,p3,p4]).prove()
    cwp = ClosedWorldProver(c, [p1,p2,p3,p4])
    for a in cwp.augmented_assumptions()[1]: print a
    print cwp.prove()

if __name__ == '__main__':
    closed_domain_demo()
    unique_names_demo()
    closed_world_demo()
