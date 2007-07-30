# Natural Language Toolkit: Wordnet Interface: Wordnet Text Mode Browser
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@csse.unimelb.edu.au> (original code)
# Author: Jussi Salmela <jtsalmela@users.sourceforge.net> (modifications)
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""Natural Language Toolkit: Wordnet Interface: Wordnet Text Mode Browser

This code is proof of concept only. For a more frendlier browsing
experience see the NLTK Wordnet Graphical Browser.

"""

from util import *
from dictionary import *
from textwrap import TextWrapper
from random import randint

__all__ = "demo"

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

def print_help():
    print "="*60
    print "Lookup a word by typing it and finishing with Enter."
    print "'Strange words' e.g. letters and numbers used as browser"
    print "commands can be searched by preceeding them with an asterisk *."
    print
    print "Words have numbered senses, pick a sense by typing a number."
    print
    print "Commands are a letter followed by Enter:"
    print "    d=down, u=up, g=gloss, s=synonyms, a=all-senses"
    print "    v=verbose, r=random, q=quit"
    print
    print "Choose POS with: N=nouns, V=verbs, J=adjectives, R=adverbs"
    print "="*60

def new_word(word):
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
        synsets = random_synset(D)
        print "N",
        print_all(synsets)
    return D, synsets

def random_synset(D):
    return D[randint(0,len(D)-1)]

def browse(word="green", index=0):
    print "Wordnet browser (type 'h' for help)"
    D, synsets = new_word(word)

    while True:
        if index >= len(synsets):
            index = 0
        input = ""
        while input == "":
            if synsets:
                prompt = "%s_%d/%d>" % (synsets[index][0], index, len(synsets))
                input = raw_input(prompt)
            else:
                input = raw_input("> ")  # safety net

        # word lookup
        if len(input) > 1 and not input.isdigit():
            if input[0] == "*": word = input[1:]
            else:               word = input.lower()
            D, synsets = new_word(word)
            index = 0

        # sense selection
        elif input.isdigit():
            if int(input) < len(synsets):
                index = int(input)# - 1
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
            print "Synonyms:", " ".join(word for word in synsets[index])

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
            synsets = random_synset(D)
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
        elif input == "h":
            print_help()
        elif input == "q":
            print "Goodbye"
            break

        else:
            print "Unrecognised command: %s" % input
            print "Type 'h' for help"

def demo():
    print
    print "="*60
    print
    print "What follows is the help text and below that is"
    print "an example output using the word 'green'"
    print "(Remember: 'h' for help!)"
    print
    print_help()
    print
    browse()

if __name__ == "__main__":
    demo()
