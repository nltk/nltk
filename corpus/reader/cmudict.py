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
from api import *
import os

class CMUDictCorpusReader(CorpusReader):
    def __init__(self, root, items, extension=''):
        if isinstance(items, basestring):
            items = find_corpus_items(root, items, extension)
        self._root = root
        self.items = tuple(items)
        self._extension = extension

    def entries(self, items=None):
        """
        @return: the given cmudict lexicon as a list of entries
        containing (word, identifier, transcription) tuples.
        """
        return concat([StreamBackedCorpusView(filename, read_cmudict_block)
                       for filename in self._item_filenames(items)])

    def raw(self, items=None):
        return concat([open(filename).read()
                       for filename in self._item_filenames(items)])

    def words(item='cmudict'):
        """
        @return: a list of all words defined in the given cmudict lexicon.
        """
        return [word for (word, num, transcription) in self.entries(item)]

    def transcriptions(self, items=None):
        """
        @return: the given cmudict lexicon as a dictionary, whose keys
        are upper case words and whose values are lists of
        pronunciation entries.
        """
        lexicon = self.entries(items)
        d = {}
        for word, num, transcription in lexicon:
            if num == 1:
                d[word] = (transcription,)
            else:
                d[word] += (transcription,)
        return d
        
    def _item_filenames(self, items):
        if items is None: items = self.items
        if isinstance(items, basestring): items = [items]
        return [os.path.join(self._root, '%s%s' % (item, self._extension))
                for item in items]
    
def read_cmudict_block(stream):
    line = stream.readline().split()
    if line:
        return [ (line[0], int(line[1]), tuple(line[2:])) ]
    else:
        return []

