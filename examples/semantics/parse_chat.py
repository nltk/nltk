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

# sents = ['which country borders France', 'which sea borders France']
# sents = ['which country that borders the_Mediterranean borders Turkey']




def main():
    import sys
    from optparse import OptionParser
    description = \
    """
Parse and evaluate some sentences in the Chat-80 model. The valuation
for the model is read in from a shelved database, 'chat.db'. If the
option '-g' is not set, the file 'chat-80.cfg' is used. If the option
'-s' is not set, some example sentences are provided automatically.
    """

    opts = OptionParser(description=description)
    opts.set_defaults(evaluate=True, beta=True, syntrace=0, semtrace=0,
                      grammar='chat_80.cfg', sentences=None)

    opts.add_option("-e", "--no-eval", action="store_false", dest="evaluate",
                    help="just do a syntactic analysis")
    opts.add_option("-b", "--no-beta-reduction", action="store_false",
                    dest="beta", help="don't carry out beta-reduction")
    opts.add_option("-t", "--syntrace", action="count", dest="syntrace",
                    help="set syntactic tracing on; requires '-e' option")
    opts.add_option("-T", "--semtrace", action="count", dest="semtrace",
                    help="set semantic tracing on")
    opts.add_option("-g", "--gram", dest="grammar",
                    help="read in grammar G", metavar="G")
    opts.add_option("-s", "--sentences", dest="sentences",
                        help="read in a file of test sentences F", metavar="F")


    (options, args) = opts.parse_args()
    SPACER = '-' * 30
    filename = options.grammar

    if options.sentences:
        inputs = [l.rstrip() for l in open(options.sentences)]
        # get rid of blank lines
        inputs = [l for l in inputs if len(l) > 0]
    else:
        inputs = sents
        
    model = m
    assignment = g
    
    # NB. GrammarFile is imported indirectly via nltk_lite.semantics
    grammar = GrammarFile.read_file(filename)

    for sent in inputs:
        n = 1
        print '\nSentence: %s' % sent
        print SPACER
        if options.evaluate: 
            evaluations = \
            text_evaluate(inputs, grammar, model, assignment, semtrace=options.semtrace)
            for (syntree, semrep, value) in evaluations[sent]:
                if isinstance(value, dict):
                    value = set(value.keys())
                print '%d:  %s' % (n, semrep.infixify())
                print value
                n += 1
        else:
            semreps = \
            text_interpret(inputs, grammar, beta_reduce=options.beta, start='S', syntrace=options.syntrace)
            for (syntree, semrep) in semreps[sent]:
                print '%d:  %s' % (n, semrep.infixify())
                n += 1
                
if __name__ == "__main__":
    main()



