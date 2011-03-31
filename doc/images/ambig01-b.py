from nltk.parse import bracket_parse
sent = '(S (S (S Kim arrived) (conj or) (S Dana left)) (conj and) (S everyone cheered))'
tree =  bracket_parse(sent)
tree.draw()
