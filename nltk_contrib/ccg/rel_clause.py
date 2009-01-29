# Natural Language Toolkit: Combinatory Categorial Grammar
#
# Copyright (C) 2001-2009 NLTK Project
# Author: Graeme Gange <ggange@csse.unimelb.edu.au>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

import chart
import lexicon

# Construct the lexicon
lex = lexicon.parseLexicon('''
    :- S, NP, N, VP

    Det :: NP/N
    Pro :: NP
    Modal :: S\\NP/VP

    TV :: VP/NP
    DTV :: TV/NP
    
    the => Det
    
    that => Det
    that => NP

    I => Pro
    you => Pro
    we => Pro

    chef => N
    cake => N
    children => N
    dough => N

    will => Modal
    should => Modal
    might => Modal
    must => Modal

    and => var\\.,var/.,var
    
    to => VP[to]/VP
    
    without => (VP\\VP)/VP[ing]

    be => TV
    cook => TV
    eat => TV

    cooking => VP[ing]/NP

    give => DTV

    is => (S\\NP)/NP
    prefer => (S\\NP)/NP

    which => (N\\N)/(S/NP)

    persuade => (VP/VP[to])/NP
    ''')

parser = chart.CCGChartParser(lex, chart.DefaultRuleSet)
print "Wh-relative Clauses"
print "==================="
for parse in parser.nbest_parse("you prefer that cake".split(),1):
    chart.printCCGDerivation(parse)
for parse in parser.nbest_parse("that is the cake which you prefer".split(),1):
    chart.printCCGDerivation(parse)

# ===Some other example sentences===
#for parse in parser.nbest_parse("that is the cake which we will persuade the chef to cook".split(),1):
#    chart.printCCGDerivation(parse)
#for parse in parser.nbest_parse("that is the cake which we will persuade the chef to give the children".split(),1):
#    chart.printCCGDerivation(parse)


print "Subject Extraction"
print "==================="
sent = "that is the dough which you will eat without cooking".split()
nosub_parser = chart.CCGChartParser(lex, chart.ApplicationRuleSet +
                      chart.CompositionRuleSet + chart.TypeRaiseRuleSet)

print "Without Substitution:"
for parse in nosub_parser.nbest_parse(sent,1):
    chart.printCCGDerivation(parse)
print ""
print "With Substitution:"
for parse in parser.nbest_parse(sent,1):
    chart.printCCGDerivation(parse)
