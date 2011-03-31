from nltk_lite.parse import bracket_parse
from pprint import pprint
sent = '(S (NP Lee)(VP (V saw)(NP the dog)))'
tree =  bracket_parse(sent)
pprint(tree.pp())
#tree.draw()
