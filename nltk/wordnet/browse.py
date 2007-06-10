# Natural Language Toolkit: Wordnet Interface: Wordnet Browser
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

from nltk_lite.wordnet import *
from textwrap import TextWrapper
from string import join
from random import randint

# this code is proof of concept only, and needs a lot of tidying up

tw = TextWrapper(subsequent_indent="    ")

def show(synsets, index):
    return "%d %s;" % (index, synsets[index][0])

def print_gloss(synsets, index):
    print index, join(tw.wrap(synsets[index].gloss), "\n")

def print_all_glosses(synsets):
    for index in range(len(synsets)):
        print_gloss(synsets, index)

def print_all(synsets):
    for index in range(len(synsets)):
        print show(synsets, index),
    print

def help():
    print 'Lookup a word by giving the word in double quotes, e.g. "dog".'
    print 'Each word has one or more senses, pick a sense by typing a number.'
    print 'd=down, u=up, g=gloss, s=synonyms, a=all-senses, v=verbose, r=random.'
    print 'N=nouns, V=verbs, J=adjectives, R=adverbs.'

def _print_lookup(D, section, word):
    try:
        synsets = D[word]
        print section,
        print_all(synsets)
    except KeyError:
        pass

def _new_word(word):
    _print_lookup(N, "N", word)
    _print_lookup(V, "V", word)
    _print_lookup(ADJ, "J", word)
    _print_lookup(ADV, "R", word)
    if word in N: D = N
    elif word in V: D = V
    elif word in ADJ: D = ADJ
    elif word in ADV: D = ADV
    if word:
        synsets = D[word]
    else:
        synsets = _random_synset(D)
    return D, synsets

def _random_synset(D):
    return D[randint(0,len(D)-1)]

def browse(word="", index=0):
    print "Wordnet browser (type 'h' for help)"
    if word:
        D, synsets = _new_word(word)
        print show(synsets, index)
    else:
        D = N
        synsets = _random_synset(D)

    while True:
        if index >= len(synsets):
            index = 0
        if synsets:
            input = raw_input(synsets[index][0] + "_" + `index` + "/" + `len(synsets)` + "> ")
        else:
            input = raw_input("> ")  # safety net
        if input[0] == '"' and input[-1] == '"':
            D, synsets = _new_word(input[1:-1])
            index = 0
        elif input[0] in "0123456789":
            if int(input) < len(synsets):
                index = int(input)
                print_gloss(synsets, index)
            else:
                print "There are %d synsets" % len(synsets)
        elif input[0] is "a":
            print_all(synsets)
        elif input[0] is "g":
            print_gloss(synsets, index)
        elif input[0] is "v":
            print_all_glosses(synsets)
        elif input[0] is "h":
            help()
        elif input[0] is "r":
            synsets = _random_synset(D)
        elif input[0] is "u":
            try:
                hypernyms = synsets[index][HYPERNYM]
                hypernyms[0]
                synsets = hypernyms
                print_all(synsets)
                index = 0
            except IndexError:
                print "Cannot go up"
        elif input[0] is "d":
            try:
                hyponyms = synsets[index][HYPONYM]
                hyponyms[0]
                synsets = hyponyms
                print_all(synsets)
                index = 0
            except IndexError:
                print "Cannot go down"
        elif input[0] is "s":
            print "Synonyms:", join(word for word in synsets[index])
        elif input[0] in "N": # nouns
            if word in N:
                D = N
                synsets = D[word]
        elif input[0] is "V": # verbs
            if word in V:
                D = V
                synsets = D[word]
        elif input[0] is "J": # adjectives
            if word in ADJ:
                D = ADJ
                synsets = D[word]
        elif input[0] is "R": # adverbs
            if word in ADV:
                D = ADV
                synsets = D[word]
        elif input[0] is "q":
            print "Goodbye"
            break
        else:
            print "Unrecognised command, type 'h' for help"
            
if __name__ == '__main__':
    browse()
