# Natural Language Toolkit: WordNet Interface
#
# Copyright (C) 2001-2009 NLTK Project
# Author: Oliver Steele <steele@osteele.com>
#         Steven Bird <sb@csse.unimelb.edu.au>
#         David Ormiston Smith <daosmith@csse.unimelb.edu.au>>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
WordNet interface, based on Oliver Steele's Pywordnet, together
with an implementation of Ted Pedersen's Wordnet::Similarity package.

Usage
=====

    >>> from nltk.wordnet import *

Retrieve words from the database

    >>> N['dog']
    dog (noun)
    >>> V['dog']
    dog (verb)
    >>> ADJ['clear']
    clear (adj)
    >>> ADV['clearly']
    clearly (adv)

Examine a word's senses and pointers:

    >>> N['dog'].synsets()
    [{noun: dog, domestic_dog, Canis_familiaris}, {noun: frump, dog}, {noun: dog}, {noun: cad, bounder, blackguard, dog, hound, heel}, {noun: frank, frankfurter, hotdog, hot_dog, dog, wiener, wienerwurst, weenie}, {noun: pawl, detent, click, dog}, {noun: andiron, firedog, dog, dog-iron}]
    ('dog' in {noun: dog, domestic dog, Canis familiaris}, 'dog' in {noun: frump, dog}, 'dog' in {noun: dog}, 'dog' in {noun: cad, bounder, blackguard, dog, hound, heel}, 'dog' in {noun: frank, frankfurter, hotdog, hot dog, dog, wiener, wienerwurst, weenie}, 'dog' in {noun: pawl, detent, click, dog}, 'dog' in {noun: andiron, firedog, dog, dog-iron})

Extract the first sense:

    >>> N['dog'][0]
    {noun: dog, domestic_dog, Canis_familiaris}

Get the first five pointers (relationships) from dog to other synsets:

    >>> N['dog'][0].relations()
    {'hypernym': [('noun', 2083346, 0), ('noun', 1317541, 0)],
     'part holonym': [('noun', 2158846, 0)],
     'member meronym': [('noun', 2083863, 0), ('noun', 7994941, 0)],
     'hyponym': [('noun', 1322604, 0), ('noun', 2084732, 0), ...]}

Get those synsets of which 'dog' is a member meronym:

    >>> N['dog'][0][MEMBER_MERONYM]
    [{noun: Canis, genus Canis}, {noun: pack}]

"""

from util import *
from cache import *
from lexname import *
from dictionary import *
from similarity import *
from synset import *
from browse import *
from stemmer import *
from browser import *



