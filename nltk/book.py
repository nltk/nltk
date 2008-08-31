# Some texts for exploration in chapter 1 of the book

from nltk.corpus import gutenberg, genesis, inaugural, nps_chat
from nltk.text import Text

print "Introductory Examples for the NLTK Book"
print
print "Loading 6 texts..."

text1 = Text(gutenberg.words('melville-moby_dick.txt'))
print "text1:", text1.name

text2 = Text(gutenberg.words('austen-sense.txt'))
print "text2:", text2.name

text3 = Text(genesis.words('english-kjv.txt'), name="The Book of Genesis")
print "text3:", text3.name

text4 = Text(inaugural.words(), name="Inaugural Address Corpus")
print "text4:", text4.name

text5 = Text(nps_chat.words(['10-26-teens_706posts.xml',
                             '11-08-teens_706posts.xml',
                             '11-09-teens_706posts.xml']),
                             name="Teen Chat Corpus")
print "text5:", text5.name

text6 = Text(gutenberg.words('chesterton-thursday.txt'))
print "text6:", text6.name
