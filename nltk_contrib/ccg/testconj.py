# Natural Language Toolkit: Combinatory Categorial Grammar
#
# Copyright (C) 2001-2009 NLTK Project
# Author: Graeme Gange <ggange@csse.unimelb.edu.au>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

from chart import CCGChartParser, ApplicationRuleSet, CompositionRuleSet, SubstitutionRuleSet, TypeRaiseRuleSet
from chart import printCCGDerivation
import lexicon

# Lexicons for the tests
test1_lex = '''
       :- S,N,NP,VP
       I => NP
       you => NP
       will => S\\NP/VP
       cook => VP/NP
       which => (N\N)/(S/NP)
       and => var\\.,var/.,var
       might => S\\NP/VP
       eat => VP/NP
       the => NP/N
       mushrooms => N
       parsnips => N'''

test2_lex = '''        
        :- N, S, NP, VP
        articles => N
        the => NP/N
        and => var\\.,var/.,var
        which => (N\N)/(S/NP)
        I => NP
        anyone => NP
        will => (S/VP)\\NP
        file => VP/NP
        without => (VP\\VP)/VP[ing]
        forget => VP/NP
        reading => VP[ing]/NP
        '''

# Tests handling of conjunctions
# Note that while the two derivations are different, they are semantically equivalent.
def test1():
    lex = lexicon.parseLexicon(test1_lex)
    parser = CCGChartParser(lex, ApplicationRuleSet + CompositionRuleSet + SubstitutionRuleSet)
    for parse in parser.nbest_parse("I will cook and might eat the mushrooms and parsnips".split()):
       printCCGDerivation(parse)

# Tests handling subject extraction
# Interesting to point that the two parses are clearly semantically different.
def test2():
    lex = lexicon.parseLexicon(test2_lex)

    parser = CCGChartParser(lex, ApplicationRuleSet + CompositionRuleSet + SubstitutionRuleSet)
    for parse in parser.nbest_parse("articles which I will file and forget without reading".split()):
        printCCGDerivation(parse)

print "======="
print "Test 1:"
print "======="
test1()

print "======="
print "Test 2:"
print "======="
test2()
