from nltk.parse import bracket_parse
sent = '(S (NP the policeman)(VP (V saw)(NP the burglar)(PP with a telescope)))'
tree =  bracket_parse(sent)
tree.draw()
