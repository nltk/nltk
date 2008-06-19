# Demonstration code for using the CCG parser
# Author: Graeme Gange
import ccgparser
import ccglexicon

# Construct the lexicon
lexicon = ccglexicon.parseLexicon('''
   :- S, NP, N, VP   # Primitive categories, S is the target primitive

   Det :: NP/N       # Family of words
   Pro :: NP
   TV :: VP/NP
   Modal :: (S\\NP)/VP # Backslashes need to be escaped

   I => Pro          # Word -> Category mapping
   you => Pro
   
   the => Det

   # Variables have the special keyword 'var'
   # '.' prevents permutation
   # ',' prevents composition
   and => var\\.,var/.,var

   which => (N\\N)/(S/NP)

   will => Modal # Categories can be either explicit, or families.
   might => Modal

   cook => TV
   eat => TV

   mushrooms => N
   parsnips => N
   bacon => N
   ''')

# Construct the parser
parser = ccgparser.CCGChartParser(lexicon,ccgparser.DefaultRuleSet)

# Parse a sentence
for parse in parser.nbest_parse("I might cook and eat the bacon".split(),3):
   ccgparser.printCCGDerivation(parse)
