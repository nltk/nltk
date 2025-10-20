import os
import sys
curdir = os.getcwd()
curdir = curdir + "\\..\\.."
sys.path.append(curdir)

import nltk
from nltk import pos_tag, word_tokenize
from nltk.tokenize.treebank import TreebankWordDetokenizer

nltk.download('averaged_perceptron_tagger')
nltk.download('punkt')


text = "Lorem ipsum dolor sit amet. consectetur adipiscing elit."
# d = TreebankWordDetokenizer()
tagged_words = pos_tag(word_tokenize(text))
words = [word for word, tag in tagged_words]
# print('x'+words[5]+'x')
print(TreebankWordDetokenizer().detokenize(words))