from __future__ import print_statement

import re, random

from collections import defaultdict

###############################################################################
### FILE ACCESS
###############################################################################

def read_words(filename):
    "Get the words out of the file, ignoring case and punctuation."
    text = open(filename).read().lower()
    return re.split('\W+', text)

def read_text(filename):
    "Load the file into a text string, normalising whitespace."
    text = open(filename).read()
    return re.sub('\s+', ' ', text)

###############################################################################
### SEARCHING
###############################################################################

def print_conc(pattern, text, num=25):
    "Print segments of the file that match the pattern."
    for i in range(num):
        m = re.search(pattern, text)
        if not m:
            break
        print(text[m.start()-30:m.start()+40])
        text = text[m.start()+1:]

###############################################################################
### COUNTING
###############################################################################

def count_words(words):
    "Count the number of times each word has appeared."
    wordcounts = {}
    for word in words:
        if word not in wordcounts:
             wordcounts[word] = 0
        wordcounts[word] += 1
    return wordcounts

def print_freq(counts, num=25):
    "Print the words and their counts, in order of decreasing frequency."
    from operator import itemgetter
    total = sum(counts.values())
    cumulative = 0.0
    sorted_word_counts = sorted(counts.items(), key=itemgetter(1), reverse=True)
    for i in range(num):
        word, count = sorted_word_counts[i]
        cumulative += count * 100.0 / total
        print("%3d %3.2d%% %s" % (i, cumulative, word))

###############################################################################
### COLLOCATIONS
###############################################################################

def count_pairs(words, num=50):
    "Print the frequent bigrams, omitting short words"
    paircounts = {}
    for i in range(len(words)-1):
        if len(words[i]) > 4 and len(words[i+1]) > 4:
            pair = words[i] + ' ' + words[i+1]
            if pair not in paircounts:
                paircounts[pair] = 0
            paircounts[pair] += 1
    return paircounts

###############################################################################
### RANDOM TEXT GENERATION
###############################################################################

def train(words):
    prev1 = ''
    prev2 = ''
    model = defaultdict(list)
    for word in words:
        key = (prev1, prev2)
        if word not in model[key]:
            model[key].append(word)
            model[prev2].append(word)
        prev2 = prev1
        prev1 = word
    return model

def generate(model, num=100):
    prev2 = ''
    prev1 = ''
    for i in range(num):
        next = model[(prev1,prev2)]
        if next:
            word = random.choice(next)
        else:
            word = random.choice(model[prev2])
        print(word, end='')
        prev2 = prev1
        prev1 = word
    print()

        

