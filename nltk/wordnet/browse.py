# Natural Language Toolkit: Wordnet Interface: Wordnet Browser
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@csse.unimelb.edu.au>
#         Jussi Salmela <jussi.salmela@pp3.inet.fi>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

from util import *
from dictionary import *
from textwrap import TextWrapper
from random import randint

tw = TextWrapper(subsequent_indent="    ")

def show(synsets, index):
    return "%d %s;" % (index, synsets[index][0])

def print_gloss(synsets, index):
    print index, "\n".join(tw.wrap(synsets[index].gloss))

def print_all_glosses(synsets):
    for index in range(len(synsets)):
        print_gloss(synsets, index)

def print_all(synsets):
    for index in range(len(synsets)):
        print show(synsets, index),
    print

def browse_help():
    print 'Lookup a word by typing it and finishing with Enter.'
    print 'Words have numbered senses, pick a sense by typing a number.'
    print 'Commands:'
    print 'd=down, u=up, g=gloss, s=synonyms, a=all-senses, v=verbose, r=random, q=quit'
    print 'N=nouns, V=verbs, J=adjectives, R=adverbs'

def _new_word(word):
    D = None
    for pos,sec in ((N,"N"), (V,"V"), (ADJ,"J"), (ADV,"R")):
        if word in pos:
            if not D: D = pos
            print sec,
            print_all(pos[word])
    if D: synsets = D[word]
    else:
        print "Word '%s' not found! Choosing a random word." % word
        D = N
        synsets = _random_synset(D)
        print "N",
        print_all(N[synsets[0][0]])
    return D, synsets

def _random_synset(D):
    return D[randint(0,len(D)-1)]


def browse(word=" ", index=0):
    """
    Browse WordNet interactively, starting from the specified word, and
    navigating the WordNet hierarchy to synonyms, hypernyms, hyponyms, and so on.

    @type word: C{string}
    @param word: the word to look up in WordNet
    @type index: C{int}
    @param index: the sense number of this word to use (optional)
    """
    print "Wordnet browser (type 'h' for help)"
    D, synsets = _new_word(word)

    while True:
        if index >= len(synsets):
            index = 0
        input = ''
        while input == '':
            if synsets:
                input = raw_input(synsets[index][0] + "_" + `index` + "/" +
                                  `len(synsets)` + "> ")
            else:
                input = raw_input("> ")  # safety net

        # word lookup
        if len(input) > 1 and not input.isdigit():
            word = input.lower()
            D, synsets = _new_word(word)
            index = 0

        # sense selection
        elif input.isdigit():
            if int(input) < len(synsets):
                index = int(input)
                print_gloss(synsets, index)
            else:
                print "There are %d synsets" % len(synsets)

        # more info
        elif input == "a":
            print_all(synsets)
        elif input == "g":
            print_gloss(synsets, index)
        elif input == "v":
            print_all_glosses(synsets)
        elif input == "s":
            print "Synonyms:", ' '.join(word for word in synsets[index])

        # choose part-of-speech
        elif input in "NVJR":
            ind = "NVJR".index(input)
            pos = [N, V, ADJ, ADV][ind]
            s = ["noun", "verb", "adjective", "adverb"][ind]
            if word in pos:
                D = pos
                synsets = D[word]
            else:
                print "No " + s + " sense found"

        # navigation
        elif input == "r":
            synsets = _random_synset(D)
        elif input == "u":
            try:
                hypernyms = synsets[index][HYPERNYM]
                hypernyms[0]
                synsets = hypernyms
                print_all(synsets)
                index = 0
            except IndexError:
                print "Cannot go up"
        elif input == "d":
            try:
                hyponyms = synsets[index][HYPONYM]
                hyponyms[0]
                synsets = hyponyms
                print_all(synsets)
                index = 0
            except IndexError:
                print "Cannot go down"

        # miscellany
        elif input == "h" or input == "?":
            browse_help()
        elif input == "q":
            print "Goodbye"
            break

        else:
            print "Unrecognised command: %s" % input
            print "Type 'h' for help"

if __name__ == '__main__':
    browse()
