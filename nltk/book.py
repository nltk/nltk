# Some texts for exploration in chapter 1 of the book

from nltk.corpus import gutenberg, genesis, inaugural, nps_chat, webtext, treebank
from nltk.text import Text
from nltk import FreqDist, bigrams

print "Introductory Examples for the NLTK Book"
print
print "Loading 8 texts..."

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
print "text5", text5.name

text6 = Text(gutenberg.words('chesterton-thursday.txt'))
print "text6:", text6.name

text7 = Text(treebank.words(), name="Wall Street Journal")
print "text7:", text7.name

text8 = Text(webtext.words('singles.txt'), name="Personals Corpus")
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

