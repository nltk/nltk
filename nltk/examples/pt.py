# -*- coding: utf-8 -*-

# Some texts for exploration with Portuguese, cf chapter 1 of the book

from nltk.corpus import machado, mac_morpho, floresta, genesis
from nltk.text import Text
from nltk.probability import FreqDist
from nltk.util import bigrams
from nltk.misc import babelize_shell

print "*** Introductory Examples for the NLTK Book ***"
print "Loading ptext1, ... and psent1, ..."
print "Type the name of the text or sentence to view it."
print "Type: 'texts()' or 'sents()' to list the materials."

ptext1 = Text(machado.words('romance/marm05.txt'), name="Mem�rias P�stumas de Br�s Cubas (1881)")
print "ptext1:", ptext1.name

ptext2 = Text(machado.words('romance/marm08.txt'), name="Dom Casmurro (1899)")
print "ptext2:", ptext2.name

ptext3 = Text(genesis.words('portuguese.txt'), name="G�nesis")
print "ptext3:", ptext3.name

ptext4 = Text(mac_morpho.words('mu94se01.txt'), name="Folha de Sau Paulo (1994)")
print "ptext4:", ptext4.name

def texts():
    print "ptext1:", ptext1.name
    print "ptext2:", ptext2.name
    print "ptext3:", ptext3.name
    print "ptext4:", ptext4.name

psent1 = "o amor da gl�ria era a coisa mais verdadeiramente humana que h� no homem , e,  conseq�entemente , a sua mais genu�na fei��o".split()
psent2 = "N�o consultes dicion�rios .".split()
psent3 = "No princ�pio , criou Deus os c�us e a terra .".split()
psent4 = "A C�ritas acredita que outros cubanos devem chegar ao Brasil ."


def sents():
    print "psent1:", " ".join(psent1)
    print "psent2:", " ".join(psent2)
    print "psent3:", " ".join(psent3)
    print "psent4:", " ".join(psent4)
