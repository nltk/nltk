# Natural Language Toolkit: Parsers
#
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#

"""
Demo of how to combine the output of parsing with evaluation in a model.
Requires two inputs:

 - C{sem2.cfg}: a toy grammar with some syntactic and semantic rules.
 - C{model0.py}: a small first-order model to interpret outputs of the grammar.



"""


import nltk_lite.semantics.evaluate as evaluate
from nltk_lite.semantics.chat_80 import val_load
from nltk_lite.semantics.utilities import *

val = val_load('chat')

dom = val.domain
#Bind C{dom} to the C{domain} property of C{val}."""

m = evaluate.Model(dom, val)
#Initialize a model with parameters C{dom} and C{val}.

g = evaluate.Assignment(dom)
#Initialize a variable assignment with parameter C{dom}."""




sents = ['France is a country', 'Paris is the capital of France', 'what is the capital of France']

sents = ['which country borders France', 'which sea borders France']
sents = ['which country that borders the_Mediterranean borders Turkey']




def main(inputs = sents, evaluate=1, filename = 'chat_80.cfg'):
    SPACER = '-' * 30
    
    model = m
    assignment = g
    
    # NB. GrammarFile is imported indirectly via nltk_lite.semantics
    grammar = GrammarFile.read_file(filename)

    for sent in inputs:
        n = 1
        print '\nSentence: %s' % sent
        print SPACER
        if evaluate: 
            evaluations = text_evaluate(inputs, grammar, model, assignment, semtrace=0)
            for (syntree, semrep, value) in evaluations[sent]:
                if isinstance(value, dict):
                    value = set(value.keys())
                print '%d:  %s' % (n, semrep.infixify())
                print '%9s in Model m' % value
                n += 1
        else:
            semreps = text_interpret(inputs, grammar, beta_reduce=True, start='S', syntrace=0)
            for (syntree, semrep) in semreps[sent]:
                print '%d:  %s' % (n, semrep.infixify())
                n += 1
                
if __name__ == "__main__":
    main()



