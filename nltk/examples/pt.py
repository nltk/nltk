# -*- coding: iso-8859-1 -*-

# Natural Language Toolkit: Some Portuguese texts for exploration in chapter 1 of the book
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

from nltk.corpus import machado, mac_morpho, floresta, genesis
from nltk.text import Text
from nltk.probability import FreqDist
from nltk.util import bigrams
from nltk.misc import babelize_shell

print "*** Introductory Examples for the NLTK Book ***"
print "Loading ptext1, ... and psent1, ..."
print "Type the name of the text or sentence to view it."
print "Type: 'texts()' or 'sents()' to list the materials."

ptext1 = Text(machado.words('romance/marm05.txt'), name="Memórias Póstumas de Brás Cubas (1881)")
print "ptext1:", ptext1.name.decode('latin-1')

ptext2 = Text(machado.words('romance/marm08.txt'), name="Dom Casmurro (1899)")
print "ptext2:", ptext2.name.decode('latin-1')

ptext3 = Text(genesis.words('portuguese.txt'), name="Gênesis")
print "ptext3:", ptext3.name.decode('latin-1')

ptext4 = Text(mac_morpho.words('mu94se01.txt'), name="Folha de Sau Paulo (1994)")
print "ptext4:", ptext4.name.decode('latin-1')

def texts():
    print "ptext1:", ptext1.name.decode('latin-1')
    print "ptext2:", ptext2.name.decode('latin-1')
    print "ptext3:", ptext3.name.decode('latin-1')
    print "ptext4:", ptext4.name.decode('latin-1')

psent1 = "o amor da glória era a coisa mais verdadeiramente humana que há no homem , e , conseqüentemente , a sua mais genuína feição .".split()
psent2 = "Não consultes dicionários .".split()
psent3 = "No princípio, criou Deus os céus e a terra.".split()
psent4 = "A Cáritas acredita que outros cubanos devem chegar ao Brasil .".split()

def sents():
    print "psent1:", " ".join(psent1).decode('latin-1')
    print "psent2:", " ".join(psent2).decode('latin-1')
    print "psent3:", " ".join(psent3).decode('latin-1')
    print "psent4:", " ".join(psent4).decode('latin-1')
