# Natural Language Toolkit: Cooper storage for Quantifier Ambiguity
#
# Copyright (C) 2001-2009 NLTK Project
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

from logic import LambdaExpression, ApplicationExpression, Variable, LogicParser
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

    def s_retrieve(self, trace=False):
        """
        Carry out S-Retrieval of binding operators in store. If hack=True,
        serialize the bindop and core as strings and reparse. Ugh.

        Each permutation of the store (i.e. list of binding operators) is
        taken to be a possible scoping of quantifiers. We iterate through the
        binding operators in each permutation, and successively apply them to
        the current term, starting with the core semantic representation,
        working from the inside out.
    
        Binding operators are of the form::
    
             bo(\P.all x.(man(x) -> P(x)),z1)
        """
        for perm, store_perm in enumerate(self._permute(self.store)):
            if trace:
                print "Permutation %s" % (perm+1)
            term = self.core
            for bindop in store_perm:
                # we just want the arguments that are wrapped by the 'bo' predicate
                quant, varex = tuple(bindop.args)
                # use var to make an abstraction over the current term and then
                # apply the quantifier to it
                term = ApplicationExpression(quant, LambdaExpression(varex.variable, term))
                if trace:
                    print "  ", term
                term = term.simplify()
            self.readings.append(term)


def parse_with_bindops(sentence, grammar=None, trace=0):
    """
    Use a grammar with Binding Operators to parse a sentence.
    """
    if not grammar:
        grammar = 'grammars/book_grammars/storage.fcfg'
    parser = load_earley(grammar, trace=trace, chart_class=InstantiateVarsChart)
    # Parse the sentence.
    tokens = sentence.split()
    return parser.nbest_parse(tokens)


def demo():
    from nltk.sem import cooper_storage as cs
    sentence = "every girl chases a dog"
    #sentence = "a man gives a bone to every dog"
    print
    print "Analyis of sentence '%s'" % sentence
    print "=" * 50    
    trees = cs.parse_with_bindops(sentence, trace=0)
    for tree in trees:
        semrep = cs.CooperStore(tree.node['sem'])
        print
        print "Binding operators:"
        print "-" * 15  
        for s in semrep.store: 
            print s
        print 
        print "Core:"
        print "-" * 15
        print semrep.core
        print 
        print "S-Retrieval:"
        print "-" * 15       
        semrep.s_retrieve(trace=True)
        print "Readings:"
        print "-" * 15

        for i, reading in enumerate(semrep.readings):
            print "%s: %s" % (i+1, reading)
            
if __name__ == '__main__':
    demo()
