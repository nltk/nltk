import nltk
from nltk.collocations import *
import time

# trigram_measures = nltk.collocations.TrigramAssocMeasures()

# t = time.time()
# finder = TrigramCollocationFinder.from_words(nltk.corpus.genesis.words('english-web.txt'), 3)
# print(finder.nbest(trigram_measures.pmi, 10))
# print('modified from_words function with default window_size:', time.time() - t)
#
# t = time.time()
# finder = TrigramCollocationFinder.from_words(nltk.corpus.genesis.words('english-web.txt'), 4)
# print(finder.nbest(trigram_measures.pmi, 10))
# print('modified from_words function with window_size=4:',time.time() - t)

# trigram_measures = nltk.collocations.TrigramAssocMeasures()
# t = time.time()
# text = "I do not like green eggs and ham, I do not like them green Sam I am!"
# tokens = nltk.wordpunct_tokenize(text)
# # finder = QuadgramCollocationFinder.from_words(nltk.corpus.genesis.words('english-web.txt'))
# finder = QuadgramCollocationFinder.from_words(tokens)
# print(finder.nbest(trigram_measures.raw_freq, 10))
# print('modified from_words function with default window_size:', time.time() - t)



trigram_measures = nltk.collocations.TrigramAssocMeasures()
text = "I do not like green eggs and ham, I do not like them green Sam I am!"
tokens = nltk.wordpunct_tokenize(text)
finder = TrigramCollocationFinder.from_words(tokens, window_size=4)
print(finder.ngram_fd)
print(sorted(finder.nbest(trigram_measures.raw_freq, 4)))
