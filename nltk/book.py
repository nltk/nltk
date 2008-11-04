# Some texts for exploration in chapter 1 of the book

from nltk.corpus import gutenberg, genesis, inaugural, nps_chat, webtext, treebank
from nltk.text import Text
from nltk import FreqDist, bigrams
from nltk.wordnet import N

print "*** Introductory Examples for the NLTK Book ***"
print "Loading text1, ..., text8 and sent1, ..., sent8"
print "Type the name of the text or sentence to view it."
print "Type: 'texts()' or 'sents()' to list the materials."

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

text7 = Text(treebank.words(), name="Wall Street Journal")
print "text7:", text7.name

text8 = Text(webtext.words('singles.txt'), name="Personals Corpus")
print "text8:", text8.name

def texts():
    print "text1:", text1.name
    print "text2:", text2.name
    print "text3:", text3.name
    print "text4:", text4.name
    print "text5:", text5.name
    print "text6:", text6.name
    print "text7:", text7.name
    print "text8:", text8.name

sent1 = ["Call", "me", "Ishmael", "."]
sent2 = ["The", "family", "of", "Dashwood", "had", "long",
         "been", "settled", "in", "Sussex", "."]
sent3 = ["In", "the", "beginning", "God", "created", "the",
         "heaven", "and", "the", "earth", "."]
sent4 = ["Fellow", "-", "Citizens", "of", "the", "Senate",
         "and", "of", "the", "House", "of", "Representatives", ":"]
sent5 = ["I", "have", "a", "problem", "with", "people",
         "PMing", "me", "to", "lol", "JOIN"]
sent6 = ["THE", "suburb", "of", "Saffron", "Park", "lay", "on", "the",
         "sunset", "side", "of", "London", ",", "as", "red", "and",
         "ragged", "as", "a", "cloud", "of", "sunset", "."]
sent7 = ["Pierre", "Vinken", ",", "61", "years", "old", ",",
         "will", "join", "the", "board", "as", "a", "nonexecutive",
         "director", "Nov.", "29", "."]
sent8 = ['25', 'SEXY', 'MALE', ',', 'seeks', 'attrac', 'older',
         'single', 'lady', ',', 'for', 'discreet', 'encounters', '.']

def sents():
    print "sent1:", " ".join(sent1)
    print "sent2:", " ".join(sent2)
    print "sent3:", " ".join(sent3)
    print "sent4:", " ".join(sent4)
    print "sent5:", " ".join(sent5)
    print "sent6:", " ".join(sent6)
    print "sent7:", " ".join(sent7)
    print "sent8:", " ".join(sent8)
