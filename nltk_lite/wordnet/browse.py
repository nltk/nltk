# Natural Language Toolkit: Wordnet Interface: Wordnet Module
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

from nltk_lite.wordnet import *
from textwrap import TextWrapper
from string import join
from random import randint

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

def browse(word="", index=0):
    print "Wordnet browser (type 'h' for help)"
    if word:
        synsets = N[word]
        print show(synsets, index)
    else:
        synsets = N['entity']

    while True:
        input = raw_input(synsets[index][0] + "_" + `index` + "/" + `len(synsets)` + ">")
        if input[0] == '"' and input[-1] == '"':
            word = input[1:-1]
            synsets = N[word]
            index = 0
            print_all(synsets)
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
            offset = randint(len(N))
            synsets = N[offset]
        elif input[0] is "u":
            if synsets[index][HYPERNYM]:
                synsets = synsets[index][HYPERNYM]
                index = 0
                print_all(synsets)
            else:
                print "Cannot go up"
        elif input[0] is "d":
            if synsets[index][HYPONYM]:
                synsets = synsets[index][HYPONYM]
                index = 0
                print_all(synsets)
            else:
                print "Cannot go down"
        elif input[0] is "s":
            print "Synonyms:", join(word for word in synsets[index])
        else:
            print "Unrecognised command, type 'h' for help"
            
if __name__ == '__main__':
    browse()
