from words import *

telephone_words = read_words('corpus/telephone.txt')
model = train(telephone_words)
generate(model)









