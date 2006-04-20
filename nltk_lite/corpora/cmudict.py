# Natural Language Toolkit: Genesis Corpus Reader
#
# Copyright (C) 2001-2006 University of Pennsylvania
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

from nltk_lite.corpora import get_basedir
import os

items = [
    'cmudict']

item_name = {
    'cmudict': 'CMU Pronunciation Dictionary, Version 0.6, 1998',
}

def raw(files = 'cmudict'):
    """
    @param files: One or more cmudict files to be processed
    @type files: L{string} or L{tuple(string)}
    @rtype: iterator over L{tree}
    """       

    # Just one file to process?  If so convert to a tuple so we can iterate
    if type(files) is str: files = (files,)

    for file in files:
        path = os.path.join(get_basedir(), "cmudict", file)
        for line in open(path).readlines():
            fields = line.strip().split(' ')
            yield (fields[0], int(fields[1]), tuple(fields[2:]))

def dictionary(files='cmudict'):
    d = {}
    for word, num, pron in raw(files):
        if num == 1:
            d[word] = (pron,)
        else:
            d[word] += (pron,)
    return d

def demo():
    from nltk_lite.corpora import cmudict
    from itertools import islice

    print "raw method:"
    for entry in islice(cmudict.raw(), 40000, 40025):
        print entry
    print

    print "dictionary method:"
    cmudict = cmudict.dictionary()
    print 'NATURAL', cmudict['NATURAL']
    print 'LANGUAGE', cmudict['LANGUAGE']
    print 'TOOL', cmudict['TOOL']
    print 'KIT', cmudict['KIT']

if __name__ == '__main__':
    demo()

