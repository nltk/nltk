# Natural Language Toolkit: Wordnet Interface
#
# Copyright (C) 2001-2006 University of Pennsylvania
# Author: Oliver Steele <steele@osteele.com>
#         David Ormiston Smith <daosmith@csse.unimelb.edu.au>>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Wordnet interface, based on Oliver Steele's Pywordnet, together
with an implementation of Ted Pedersen's Wordnet::Similarity package.

Usage
-----
>>> from nltk_lite.wordnet import *

Retrieve words from the database
>>> N['dog']
dog(n.)
>>> V['dog']
dog(v.)
>>> ADJ['clear']
clear(adj.)
>>> ADV['clearly']
clearly(adv.)

Examine a word's senses and pointers:
>>> N['dog'].getSenses()
('dog' in {noun: dog, domestic dog, Canis familiaris}, 'dog' in {noun: frump, dog}, 'dog' in {noun: dog}, 'dog' in {noun: cad, bounder, blackguard, dog, hound, heel}, 'dog' in {noun: frank, frankfurter, hotdog, hot dog, dog, wiener, wienerwurst, weenie}, 'dog' in {noun: pawl, detent, click, dog}, 'dog' in {noun: andiron, firedog, dog, dog-iron})

Extract the first sense
>>> N['dog'][0] # aka N['dog'].getSenses()[0]
'dog' in {noun: dog, domestic dog, Canis familiaris}

Get the first five pointers (relationships) from dog to other synsets.
>>> N['dog'][0].getPointers()[:5]
(hypernym -> {noun: canine, canid}, member meronym -> {noun: Canis, genus Canis}, member meronym -> {noun: pack}, hyponym -> {noun: pooch, doggie, doggy, barker, bow-wow}, hyponym -> {noun: cur, mongrel, mutt})

Get those synsets of which 'dog' is a member meronym.
>>> N['dog'][0].getPointerTargets(MEMBER_MERONYM)
[{noun: Canis, genus Canis}, {noun: pack}]

"""

import os
import string

from os import environ

# Configuration variables

_paths = {
    'mac': ":",
    'dos': "C:\\wn16",
    'nt': "C:\\Program Files\\Wordnet\\2.1"
    }

WNHOME = environ.get('WNHOME', _paths.get(os.name, "/usr/local/WordNet-2.1"))
WNSEARCHDIR = environ.get('WNSEARCHDIR', os.path.join(WNHOME, {'mac': "Database"}.get(os.name, "dict")))

ReadableRepresentations = 1
"""If true, repr(word), repr(sense), and repr(synset) return
human-readable strings instead of strings that evaluate to an object
equal to the argument.

This breaks the contract for repr, but it makes the system much more
usable from the command line."""

# Enumerated types

NOUN = 'noun'
VERB = 'verb'
ADJECTIVE = 'adjective'
ADVERB = 'adverb'
PartsOfSpeech = (NOUN, VERB, ADJECTIVE, ADVERB)

ANTONYM = 'antonym'
HYPERNYM = 'hypernym'
HYPONYM = 'hyponym'
ATTRIBUTE = 'attribute'
ALSO_SEE = 'also see'
ENTAILMENT = 'entailment'
CAUSE = 'cause'
VERB_GROUP = 'verb group'
MEMBER_MERONYM = 'member meronym'
SUBSTANCE_MERONYM = 'substance meronym'
PART_MERONYM = 'part meronym'
MEMBER_HOLONYM = 'member holonym'
SUBSTANCE_HOLONYM = 'substance holonym'
PART_HOLONYM = 'part holonym'
SIMILAR = 'similar'
PARTICIPLE_OF = 'participle of'
PERTAINYM = 'pertainym'
# New in wn 2.0:
FRAMES = 'frames'
CLASSIF_CATEGORY = 'domain category'
CLASSIF_USAGE = 'domain usage'
CLASSIF_REGIONAL = 'domain regional'
CLASS_CATEGORY = 'class category'
CLASS_USAGE = 'class usage'
CLASS_REGIONAL = 'class regional'
# New in wn 2.1:
INSTANCE_HYPERNYM = 'hypernym (instance)'
INSTANCE_HYPONYM = 'hyponym (instance)'

POINTER_TYPES = (
    ANTONYM,
    HYPERNYM,
    HYPONYM,
    ATTRIBUTE,
    ALSO_SEE,
    ENTAILMENT,
    CAUSE,
    VERB_GROUP,
    MEMBER_MERONYM,
    SUBSTANCE_MERONYM,
    PART_MERONYM,
    MEMBER_HOLONYM,
    SUBSTANCE_HOLONYM,
    PART_HOLONYM,
    SIMILAR,
    PARTICIPLE_OF,
    PERTAINYM,
    # New in wn 2.0:
    FRAMES,
    CLASSIF_CATEGORY,
    CLASSIF_USAGE,
    CLASSIF_REGIONAL,
    CLASS_CATEGORY,
    CLASS_USAGE,
    CLASS_REGIONAL,
    # New in wn 2.1:
    INSTANCE_HYPERNYM,
    INSTANCE_HYPONYM,
    )

ATTRIBUTIVE = 'attributive'
PREDICATIVE = 'predicative'
IMMEDIATE_POSTNOMINAL = 'immediate postnominal'
ADJECTIVE_POSITIONS = (ATTRIBUTIVE, PREDICATIVE, IMMEDIATE_POSTNOMINAL, None)

VERB_FRAME_STRINGS = (
    None,
    "Something %s",
    "Somebody %s",
    "It is %sing",
    "Something is %sing PP",
    "Something %s something Adjective/Noun",
    "Something %s Adjective/Noun",
    "Somebody %s Adjective",
    "Somebody %s something",
    "Somebody %s somebody",
    "Something %s somebody",
    "Something %s something",
    "Something %s to somebody",
    "Somebody %s on something",
    "Somebody %s somebody something",
    "Somebody %s something to somebody",
    "Somebody %s something from somebody",
    "Somebody %s somebody with something",
    "Somebody %s somebody of something",
    "Somebody %s something on somebody",
    "Somebody %s somebody PP",
    "Somebody %s something PP",
    "Somebody %s PP",
    "Somebody's (body part) %s",
    "Somebody %s somebody to INFINITIVE",
    "Somebody %s somebody INFINITIVE",
    "Somebody %s that CLAUSE",
    "Somebody %s to somebody",
    "Somebody %s to INFINITIVE",
    "Somebody %s whether INFINITIVE",
    "Somebody %s somebody into V-ing something",
    "Somebody %s something with something",
    "Somebody %s INFINITIVE",
    "Somebody %s VERB-ing",
    "It %s that CLAUSE",
    "Something %s INFINITIVE")

from cache import *
from dictionary import *
from wordnet import *

# Create Lexname objects, originally sourced from the lexnames file available
# as a patch from the Pywordnet sourceforge site. This list may be updated by
# the creators of Wordnet at any time.

Lexname("adj.all", PartsOfSpeech[2])
Lexname("adj.pert", PartsOfSpeech[2])
Lexname("adj.ppl", PartsOfSpeech[2])
Lexname("adv.all", PartsOfSpeech[3])
Lexname("noun.Tops", PartsOfSpeech[0])
Lexname("noun.act", PartsOfSpeech[0])
Lexname("noun.animal", PartsOfSpeech[0])
Lexname("noun.artifcact", PartsOfSpeech[0])
Lexname("noun.attribute", PartsOfSpeech[0])
Lexname("noun.body", PartsOfSpeech[0])
Lexname("noun.cognition", PartsOfSpeech[0])
Lexname("noun.communication", PartsOfSpeech[0])
Lexname("noun.event", PartsOfSpeech[0])
Lexname("noun.feeling", PartsOfSpeech[0])
Lexname("noun.food", PartsOfSpeech[0])
Lexname("noun.group", PartsOfSpeech[0])
Lexname("noun.location", PartsOfSpeech[0])
Lexname("noun.motive", PartsOfSpeech[0])
Lexname("noun.object", PartsOfSpeech[0])
Lexname("noun.person", PartsOfSpeech[0])
Lexname("noun.phenomenon", PartsOfSpeech[0])
Lexname("noun.plant", PartsOfSpeech[0])
Lexname("noun.possession", PartsOfSpeech[0])
Lexname("noun.process", PartsOfSpeech[0])
Lexname("noun.quantity", PartsOfSpeech[0])
Lexname("noun.relation", PartsOfSpeech[0])
Lexname("noun.shape", PartsOfSpeech[0])
Lexname("noun.state", PartsOfSpeech[0])
Lexname("noun.substance", PartsOfSpeech[0])
Lexname("noun.time", PartsOfSpeech[0])
Lexname("verb.body", PartsOfSpeech[1])
Lexname("verb.change", PartsOfSpeech[1])
Lexname("verb.cognition", PartsOfSpeech[1])
Lexname("verb.communication", PartsOfSpeech[1])
Lexname("verb.competition", PartsOfSpeech[1])
Lexname("verb.consumption", PartsOfSpeech[1])
Lexname("verb.contact", PartsOfSpeech[1])
Lexname("verb.creation", PartsOfSpeech[1])
Lexname("verb.emotion", PartsOfSpeech[1])
Lexname("verb.motion", PartsOfSpeech[1])
Lexname("verb.perception", PartsOfSpeech[1])
Lexname("verb.possession", PartsOfSpeech[1])
Lexname("verb.social", PartsOfSpeech[1])
Lexname("verb.stative", PartsOfSpeech[1])
Lexname("verb.weather", PartsOfSpeech[1])

# PoS mapping tables (must be initialized after file utilities)

N = Dictionary(NOUN, 'noun')
V = Dictionary(VERB, 'verb')
ADJ = Dictionary(ADJECTIVE, 'adj')
ADV = Dictionary(ADVERB, 'adv')
Dictionaries = (N, V, ADJ, ADV)

initPOSTables(Dictionaries)

