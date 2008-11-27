# Natural Language Toolkit: Cooper storage for Quantifier Ambiguity
#
# Copyright (C) 2001-2008 NLTK Project
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT

#from logic import LambdaExpression, ApplicationExpression, Variable
from logic import *
from nltk.parse import load_earley
from nltk.parse.featurechart import InstantiateVarsChart

class CooperStore(object):
    """
    A container for handling quantifier ambiguity via Cooper storage.
    """
    def __init__(self, featstruct):
        """
        @param featstruct: The value of the C{sem} node in a tree from
        L{parse_with_bindops()}
        @type featstruct: A L{FeatStruct} with features C{core} and C{store}

        """ 
        self.featstruct = featstruct
        self.readings = []
        try:
            self.core = featstruct['core']
            self.store = featstruct['store']
        except KeyError:
            print "%s is not a Cooper storage structure" % featstruct
        
    def _permute(self, lst):
        """
        @return: An iterator over the permutations of the input list
        @type lst: C{list}
        @rtype: C{iterator}
        """
        remove = lambda lst0, index: lst0[:index] + lst0[index+1:]
        if lst:
            for index, x in enumerate(lst):
                for y in self._permute(remove(lst, index)):
                    yield (x,)+y
        else: yield ()   

    def s_retrieve(self, verbose=False):
        """
        Carry out S-Retrieval of binding operators in store.

        Each permutation of the store (i.e. list of binding operators) is taken to
        be a possible scoping of quantifiers. We iterate through the binding
        operators in each permutation, and successively apply them to the current
        term, starting with the core semantic representation, working from the
        inside out.
    
        Binding operators are of the form::
    
             bo(\P.all x.(man(x) -> P(x)),z1)
        """
        for store_perm in self._permute(self.store):
            term = self.core
            for bindop in store_perm:
                # we just want the arguments that are wrapped by the 'bo' predicate
                quant, var = tuple(bindop.uncurry()[1])
                # use var to make an abstraction over the current term and tten
                # apply the quantifier to it
                if verbose:
                    print
                    print "current term is", repr(term), ", bindop is", repr(quant)
                s = var.str()
                newvar = Variable(s)
                term = ApplicationExpression(quant, LambdaExpression(newvar, term))
                if verbose: 
                    print repr(term)
                term = term.simplify()
                if verbose:
                    print "new term is", term
            self.readings.append(term)


def parse_with_bindops(sentence, grammar_fn=None, trace=0):
    """
    Use a grammar with Binding Operators to parse a sentence.
    """
    if not grammar_fn:
        grammar_fn = 'grammars/storage.fcfg'
        grammar_fn = 'file:bindop.fcfg'
    parser = load_earley(grammar_fn, trace=trace, chart_class=InstantiateVarsChart)
    # Parse the sentence.
    tokens = sentence.split()
    return parser.nbest_parse(tokens)


def demo():
    #from nltk.sem import cooper_storage as cs
    import cooper_storage as cs
    sentence = "every man feeds a dog "
    trees = cs.parse_with_bindops(sentence, trace=0)
    for tree in trees:
        #print tree
        semrep = cs.CooperStore(tree.node['sem'])
        for s in semrep.store: print s
        print semrep.core
        print "Readings for sentence:", sentence
        semrep.s_retrieve()
        for reading in semrep.readings:
            print reading
            print

if __name__ == '__main__':
    demo()
