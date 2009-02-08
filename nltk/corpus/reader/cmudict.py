# Natural Language Toolkit: Genesis Corpus Reader
#
# Copyright (C) 2001-2009 NLTK Project
# Author: Steven Bird <sb@ldc.upenn.edu>
# URL: <http://www.nltk.org/>
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

import codecs

from nltk.internals import deprecated
from nltk import Index

from util import *
from api import *

class CMUDictCorpusReader(CorpusReader):
    def entries(self):
        """
        @return: the cmudict lexicon as a list of entries
        containing (word, transcriptions) tuples.
        """
        return concat([StreamBackedCorpusView(fileid, read_cmudict_block,
                                              encoding=enc)
                       for fileid, enc in self.abspaths(None, True)])

    def raw(self):
        """
        @return: the cmudict lexicon as a raw string.
        """
        if fileids is None: fileids = self._fileids
        elif isinstance(fileids, basestring): fileids = [fileids]
        return concat([self.open(f).read() for f in fileids])

    def words(self):
        """
        @return: a list of all words defined in the cmudict lexicon.
        """
        return [word.lower() for (word, _) in self.entries()]

    def dict(self):
        """
        @return: the cmudict lexicon as a dictionary, whose keys are
        lowercase words and whose values are lists of pronunciations.
        """
        return dict(Index(self.entries()))
        
    #{ Deprecated since 0.8
    @deprecated("Use .entries() or .transcriptions() instead.")
    def read(self, items='cmudict', format='listed'):
        if format == 'listed': return self.entries(items)
        if format == 'dictionary': return self.dict(items)
        raise ValueError('bad format %r' % format)
    @deprecated("Use .dict() instead.")
    def dictionary(self, items='cmudict'): return self.dict(items)
    @deprecated("Use .entries() instead.")
    def listed(self, items='cmudict'): return self.entries(items)
    #}

def read_cmudict_block(stream):
    entries = []
    while len(entries) < 100: # Read 100 at a time.
        line = stream.readline()
        if line == '': return entries # end of file.
        pieces = line.split()
        entries.append( (pieces[0].lower(), pieces[2:]) )
    return entries
