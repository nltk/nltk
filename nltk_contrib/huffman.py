# Simple Huffman encoding/decoding, Steven Bird
# http://en.wikipedia.org/wiki/Huffman_coding

import nltk
from operator import itemgetter

def huffman_tree(text):
    coding = nltk.FreqDist(text).items()
    coding.sort(key=itemgetter(1))
    while len(coding) > 1:
        a, b = coding[:2]
        pair = (a[0], b[0]), a[1] + b[1]
        coding[:2] = [pair]
        coding.sort(key=itemgetter(1))
    return coding[0][0]

def tree2codes(tree, prefix=""):
    if type(tree) is not tuple:
        yield (tree, prefix)
    else:
        for code in tree2codes(tree[0], prefix + "0"):
            yield code
        for code in tree2codes(tree[1], prefix + "1"):
            yield code

def encode(tree, text):
    mapping = dict(tree2codes(tree))
    return "".join(mapping[c] for c in text)

def decode(tree, text):
    cur_tree = tree
    for bit in text:
        if bit == "0":
            cur_tree = cur_tree[0]
        else:
            cur_tree = cur_tree[1]
        if type(cur_tree) is not tuple:
            yield cur_tree
            cur_tree = tree

text1 = nltk.corpus.udhr.raw('English-Latin1')
text2 = nltk.corpus.udhr.raw('German_Deutsch-Latin1')
text3 = nltk.corpus.udhr.raw('French_Francais-Latin1')
#text2 = nltk.corpus.udhr.raw('Swedish_Svenska-Latin1')
#text3 = nltk.corpus.udhr.raw('Samoan-Latin1')

# text = text1
# code_tree = huffman_tree(text)
# print text == "".join(decode(code_tree, encode(code_tree, text)))

alphabet = "".join(set(text1 + text2 + text3))
text1 += alphabet
text2 += alphabet
text3 += alphabet

# train1, test1 = alphabet + text1[:5000], text1[5000:]
# train2, test2 = alphabet + text2[:5000], text2[5000:]
# train3, test3 = alphabet + text3[:5000], text3[5000:]

train1 = test1 = text1
train2 = test2 = text2
train3 = test3 = text3

def trial(train, texts):
    code_tree = huffman_tree(train)
    for text in texts:
        text_len = len(text)
        comp_len = len(encode(code_tree, text)) / 8.0
        compression = (text_len - comp_len) / text_len
        print compression,
    print

trial(train1, [test1, test2, test3])
trial(train2, [test1, test2, test3])
trial(train3, [test1, test2, test3])


