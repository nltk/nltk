# Natural Language Toolkit: Corpus Access
#
# Copyright (C) 2001-2005 University of Pennsylvania
# Author: Edward Loper <edloper@ldc.upenn.edu>
# Modified by Carlos Rodriguez
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#


"""
Access to CLICTALP corpus data for NLTK's standard distribution.  Each corpus is
accessed by an instance of a C{CorpusReader} class.  For information
about using these corpora, see the reference documentation for
L{CorpusReaderI}.  The following corpus readers are currently defined:

     
  - L{clictalpcas}: Clic-TALP Corpus for Spanish consists at the moment of 100.000 of words manually annotated in a morpho-syntactic level.
    The rest of the corpus, up to 5,5 million words, is automatically tagged, with an estimated error rate of 3%. Only manual data is included here.

  - L{clictalpcat}: Similar Clic-TALP Corpus for Catalan
  


@variable _BASEDIR: The base directory for NLTK's standard distribution
    of corpora.  This is read from the environment variable
    C{NLTK_CORPORA}, if it exists; otherwise, it is given a
    system-dependant default value.  C{_BASEDIR}'s value can be changed
    with the L{set_basedir()} function.
@type _BASEDIR: C{string}

USAGE:


CLICTALP CORPUS:

>>> from nltk_contrib.corpora.clictalp import clictalpcas (for castillian Spanish)
>>> from nltk_contrib.corpora.clictalp import clictalpcat  (for Catalan)
>>> from nltk_contrib.corpora.clictalp import clictalpcas
>>> clictalpcas.groups()
['press: suplementosCiencia', 'press: articulistas', 'press: prensa deportiva', 'press: semanarios', 'press: ensayo', 'fiction: narrativa', 'press: noticias']
>>> clictalpcas.items('press: prensa deportiva')
('d1.tag.nou', 'd2.tag.nou')
>>> tks = clictalpcas.read('d1.tag.nou')
>>> tks["WORDS"][:15]
[<LEMMA='este', TAG='DD0MS0', TEXT='Este'>, <LEMMA='a\xf1o', TAG='NCMS000', TEXT='a\xf1o'>, <LEMMA='reci\xe9n', TAG='RG', TEXT='reci\xe9n'>, <LEMMA='concluido', TAG='AQ0MSP', TEXT='concluido'>, <LEMMA='no', TAG='RN', TEXT='no'>, <LEMMA='haber', TAG='VAIP3S0', TEXT='ha'>, <LEMMA='ser', TAG='VSP00SM', TEXT='sido'>, <LEMMA='ni', TAG='CC', TEXT='ni'>, <LEMMA='el', TAG='DA0MS0', TEXT='el'>, <LEMMA='a\xf1o_del_gato', TAG='NP00000', TEXT='A\xf1o_del_Gato'>, <LEMMA=',', TAG='Fc', TEXT=','>, <LEMMA='ni', TAG='CC', TEXT='ni'>, <LEMMA='el', TAG='DA0MS0', TEXT='el'>, <LEMMA='a\xf1o_del_conejo', TAG='NP00000', TEXT='A\xf1o_del_Conejo'>, <LEMMA=',', TAG='Fc', TEXT=','>]
>>> for x in tks["WORDS"][:15]:
	print x.exclude("LEMMA"),

<Este/DD0MS0> <a\xf1o/NCMS000> <reci\xe9n/RG> <concluido/AQ0MSP> <no/RN> <ha/VAIP3S0> <sido/VSP00SM> <ni/CC> <el/DA0MS0> <A\xf1o_del_Gato/NP00000> <,/Fc> <ni/CC> <el/DA0MS0> <A\xf1o_del_Conejo/NP00000> <,/Fc>


"""

import sys, os.path, re
from nltk.token import *
from nltk.tokenizer import RegexpTokenizer
from nltk.tokenreader import *
from nltk.tokenreader import sense
from nltk.tokenreader import tokenizerbased
from nltk_contrib.corpora.clictalptokenizer import LemmaTaggedTokenReader
from nltk.corpus import CorpusReaderI,SimpleCorpusReader

## CORPUS-CLIC-TALP in Spanish<----------------- Added by Carlos Rodriguez (2005)
groups = [('press: articulistas', r'a\d\d*'), ('press: ensayo', r'e\d\d*'),
          ('press: suplementosCiencia', r'c\d\d*'), ('press: prensa deportiva', r'd\d\d*'),
          ('press: noticias', r'n\d\d*'), ('press: semanarios', r'r\d\d*'),
          ('fiction: narrativa', r't\d\d*')]
clictalpcas = SimpleCorpusReader(
    'CLICTALPCAS', 'clictalpcas/', r'\w\d\d*', groups, description_file='READMEC',
    token_reader=LemmaTaggedTokenReader(SUBTOKENS='WORDS'))
del groups # delete temporary variable

## CORPUS-CLIC-TALP in SCatalan<----------------- Added by Carlos Rodriguez (2005)
clictalpcat = SimpleCorpusReader(
    'CLICTALPCAT', 'clictalpcat/', r'\d\d\d*', description_file='READMECAT',
    token_reader=LemmaTaggedTokenReader(SUBTOKENS='WORDS'))
#del groups # delete temporary variable


#################################################################
# Demonstration
#################################################################

def _truncate_repr(obj, width, indent, lines=1):
    n = width-indent
    s = repr(obj)
    if len(s) > n*lines:
        s = s[:n*lines-3] + '...'
    s = re.sub('(.{%d})' % n, '\\1\n'+' '*indent, s)
    return s.rstrip()

def _xtokenize_repr(token, width, indent, lines=1):
    n = width-indent
    s = '<'+'['
    for subtok in token['SUBTOKENS']:
        s += '%r, ' % subtok
        if len(s) > n*lines:
            s = s[:n*lines-3]+'...'
            break
    else: s = s[:-2] + ']'+'>'
    s = re.sub('(.{%d})' % n, '\\1\n'+' '*indent, s)
    return s.rstrip()

def _test_corpus(corpus):
    if corpus is None:
        print '(skipping None)'
        return
    print '='*70
    print corpus.name().center(70)
    print '-'*70
    print 'description() => ' + _truncate_repr(corpus.description(), 70,17)
    print 'license()     => ' + _truncate_repr(corpus.license(), 70,17)
    print 'copyright()   => ' + _truncate_repr(corpus.copyright(), 70,17)
    print 'items()       => ' + _truncate_repr(corpus.items(), 70,17)
    print 'groups()      => ' + _truncate_repr(corpus.groups(), 70,17)
    item = corpus.items()[0]
    contents = corpus.read(item)
    print 'read(e0)      => ' + _truncate_repr(contents, 70,25)

def demo():
    """
    Demonstrate corpus access for each of the defined corpora.
    """
    _test_corpus(clictalpcas)
    _test_corpus(clictalpcat)

    print '='*70
    
if __name__ == '__main__':
    demo()
