# Natural Language Toolkit: Genesis Corpus Reader
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
The Carnegie Mellon Pronouncing Dictionary [cmudict.0.6]
ftp://ftp.cs.cmu.edu/project/speech/dict/
Copyright 1998 Carnegie Mellon University

File Format: Each line consists of an uppercased word, a counter
(for alternative pronunciations), and a transcription.  Vowels are
marked for stress (1=primary, 2=secondary, 0=no stress).  E.g.:
NATURAL 1 N AE1 CH ER0 AH0 L

The dictionary contains 127069 entries.  Of these, 119400 words are assigned
a unique pronunciation, 6830 words have two pronunciations, and 839 words have
three or more pronunciations.  Many of these are fast-speech variants.

Phonemes: There are 39 phonemes, as shown below:
    
Phoneme Example Translation    Phoneme Example Translation
------- ------- -----------    ------- ------- -----------
AA      odd     AA D           AE      at      AE T
AH      hut     HH AH T        AO      ought   AO T
AW      cow     K AW           AY      hide    HH AY D
B       be      B IY           CH      cheese  CH IY Z
D       dee     D IY           DH      thee    DH IY
EH      Ed      EH D           ER      hurt    HH ER T
EY      ate     EY T           F       fee     F IY
G       green   G R IY N       HH      he      HH IY
IH      it      IH T           IY      eat     IY T
JH      gee     JH IY          K       key     K IY
L       lee     L IY           M       me      M IY
N       knee    N IY           NG      ping    P IH NG
OW      oat     OW T           OY      toy     T OY
P       pee     P IY           R       read    R IY D
S       sea     S IY           SH      she     SH IY
T       tea     T IY           TH      theta   TH EY T AH
UH      hood    HH UH D        UW      two     T UW
V       vee     V IY           W       we      W IY
Y       yield   Y IY L D       Z       zee     Z IY
ZH      seizure S IY ZH ER
"""

from util import *
import os

lexicons = {'cmudict': 'The Carnegie Mellon Pronouncing Dictionary'}
items = list(documents)

def read_cmudict_block(stream):
    line = stream.readline().split()
    if line:
        return [ [line[0], int(line[1]), tuple(line[2:])] ]
    else:
        return []

def read_lexicon(name='cmudict', as_dictionary=False):
    """
    Read and return the given cmudict lexicon file.  This lexicon will
    consist of a list of entries, where each entry is a list
    containing (word, identifier, transcription).  Identifier is a
    counter used when a word has multiple transcriptions.

    @param as_dictionary: If true, then collect all the entries into
        a single dictionary, whose keys are upper case words and whose
        values are lists of pronunciation transcriptions.
    """
    filename = find_corpus_file('cmudict', name)
    lexicon = StreamBackedCorpusView(filename, read_cmudict_block)
    if as_dictionary:
        d = {}
        for word, num, pron in lexicon:
            if num == 1:
                d[word] = (pron,)
            else:
                d[word] += (pron,)
        return d
    else:
        return lexicon

######################################################################
#{ Convenience Functions
######################################################################
read = read_lexicon

def dictionary(name):
    """
    Return the given cmudict lexicon as a dictionary, whose keys are
    upper case words and whose values are lists of pronunciation
    transcriptions.
    """
    return read_lexicon(name, as_dictionary=True)

######################################################################
#{ Demo
######################################################################

def demo():
    from nltk.corpora import cmudict
    from itertools import islice

    print "raw method:"
    for entry in read_lexicon()[40000:40025]:
        print entry
    print

    print "dictionary method:"
    cmudict = read_lexicon(as_dictionary=True)
    print 'NATURAL', cmudict['NATURAL']
    print 'LANGUAGE', cmudict['LANGUAGE']
    print 'TOOL', cmudict['TOOL']
    print 'KIT', cmudict['KIT']

if __name__ == '__main__':
    demo()

