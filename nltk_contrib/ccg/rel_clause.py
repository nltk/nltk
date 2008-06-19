# Demonstrating the parsing of Wh-relative clauses
# Author: Graeme Gange

import ccgparser
import ccglexicon

# Construct the lexicon
lexicon = ccglexicon.parseLexicon('''
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

parser = ccgparser.CCGChartParser(lexicon,ccgparser.DefaultRuleSet)
print "Wh-relative Clauses"
print "==================="
for parse in parser.nbest_parse("you prefer that cake".split(),1):
   ccgparser.printCCGDerivation(parse)
for parse in parser.nbest_parse("that is the cake which you prefer".split(),1):
   ccgparser.printCCGDerivation(parse)

# ===Some other example sentences===
#for parse in parser.nbest_parse("that is the cake which we will persuade the chef to cook".split(),1):
#   ccgparser.printCCGDerivation(parse)
#for parse in parser.nbest_parse("that is the cake which we will persuade the chef to give the children".split(),1):
#   ccgparser.printCCGDerivation(parse)


print "Subject Extraction"
print "==================="
sent = "that is the dough which you will eat without cooking".split()
nosub_parser = ccgparser.CCGChartParser(lexicon,ccgparser.ApplicationRuleSet +
                  ccgparser.CompositionRuleSet + ccgparser.TypeRaiseRuleSet)

print "Without Substitution:"
for parse in nosub_parser.nbest_parse(sent,1):
   ccgparser.printCCGDerivation(parse)
print ""
print "With Substitution:"
for parse in parser.nbest_parse(sent,1):
   ccgparser.printCCGDerivation(parse)
