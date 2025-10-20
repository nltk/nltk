import os
import sys
curdir = os.getcwd()
curdir = curdir + "\\..\\.."
sys.path.append(curdir)

import nltk
from nltk import pos_tag, word_tokenize
from nltk.tokenize.treebank import TreebankWordDetokenizer

text = "Lorem ipsum dolor sit amet. consectetur adipiscing elit."
text2 = "Lorem ipsum. . d.o.l.o.r sit amet@   @. consectetur!!!!!!!! adipiscing.... elit??."

tagged_words = pos_tag(word_tokenize(text))
words = [word for word, tag in tagged_words]

tagged_words2 = pos_tag(word_tokenize(text2))
words2 = [word for word, tag in tagged_words2]
# print('x'+words[5]+'x')
print(words)
print(TreebankWordDetokenizer().detokenize(words))
print(TreebankWordDetokenizer().detokenize(words, 0, 1))
print('\n')
print(words2)
print(TreebankWordDetokenizer().detokenize(words2))
print(TreebankWordDetokenizer().detokenize(words2, 0, 1))