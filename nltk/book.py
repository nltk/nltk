# Natural Language Toolkit: Some texts for exploration in chapter 1 of the book
#
# Copyright (C) 2001-2026 NLTK Project
# Author: Steven Bird <stevenbird1@gmail.com>
#
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

from nltk.corpus import (
    genesis,
    gutenberg,
    inaugural,
    nps_chat,
    treebank,
    webtext,
    wordnet,
)
from nltk.probability import FreqDist
from nltk.termsec import safe_print
from nltk.text import Text
from nltk.util import bigrams

safe_print("*** Introductory Examples for the NLTK Book ***")
safe_print("Loading text1, ..., text9 and sent1, ..., sent9")
safe_print("Type the name of the text or sentence to view it.")
safe_print("Type: 'texts()' or 'sents()' to list the materials.")

text1 = Text(gutenberg.words("melville-moby_dick.txt"))
safe_print("text1:", text1.name)

text2 = Text(gutenberg.words("austen-sense.txt"))
safe_print("text2:", text2.name)

text3 = Text(genesis.words("english-kjv.txt"), name="The Book of Genesis")
safe_print("text3:", text3.name)

text4 = Text(inaugural.words(), name="Inaugural Address Corpus")
safe_print("text4:", text4.name)

text5 = Text(nps_chat.words(), name="Chat Corpus")
safe_print("text5:", text5.name)

text6 = Text(webtext.words("grail.txt"), name="Monty Python and the Holy Grail")
safe_print("text6:", text6.name)

text7 = Text(treebank.words(), name="Wall Street Journal")
safe_print("text7:", text7.name)

text8 = Text(webtext.words("singles.txt"), name="Personals Corpus")
safe_print("text8:", text8.name)

text9 = Text(gutenberg.words("chesterton-thursday.txt"))
safe_print("text9:", text9.name)


def texts():
    safe_print("text1:", text1.name)
    safe_print("text2:", text2.name)
    safe_print("text3:", text3.name)
    safe_print("text4:", text4.name)
    safe_print("text5:", text5.name)
    safe_print("text6:", text6.name)
    safe_print("text7:", text7.name)
    safe_print("text8:", text8.name)
    safe_print("text9:", text9.name)


sent1 = ["Call", "me", "Ishmael", "."]
sent2 = [
    "The",
    "family",
    "of",
    "Dashwood",
    "had",
    "long",
    "been",
    "settled",
    "in",
    "Sussex",
    ".",
]
sent3 = [
    "In",
    "the",
    "beginning",
    "God",
    "created",
    "the",
    "heaven",
    "and",
    "the",
    "earth",
    ".",
]
sent4 = [
    "Fellow",
    "-",
    "Citizens",
    "of",
    "the",
    "Senate",
    "and",
    "of",
    "the",
    "House",
    "of",
    "Representatives",
    ":",
]
sent5 = [
    "I",
    "have",
    "a",
    "problem",
    "with",
    "people",
    "PMing",
    "me",
    "to",
    "lol",
    "JOIN",
]
sent6 = [
    "SCENE",
    "1",
    ":",
    "[",
    "wind",
    "]",
    "[",
    "clop",
    "clop",
    "clop",
    "]",
    "KING",
    "ARTHUR",
    ":",
    "Whoa",
    "there",
    "!",
]
sent7 = [
    "Pierre",
    "Vinken",
    ",",
    "61",
    "years",
    "old",
    ",",
    "will",
    "join",
    "the",
    "board",
    "as",
    "a",
    "nonexecutive",
    "director",
    "Nov.",
    "29",
    ".",
]
sent8 = [
    "25",
    "SEXY",
    "MALE",
    ",",
    "seeks",
    "attrac",
    "older",
    "single",
    "lady",
    ",",
    "for",
    "discreet",
    "encounters",
    ".",
]
sent9 = [
    "THE",
    "suburb",
    "of",
    "Saffron",
    "Park",
    "lay",
    "on",
    "the",
    "sunset",
    "side",
    "of",
    "London",
    ",",
    "as",
    "red",
    "and",
    "ragged",
    "as",
    "a",
    "cloud",
    "of",
    "sunset",
    ".",
]


def sents():
    safe_print("sent1:", " ".join(sent1))
    safe_print("sent2:", " ".join(sent2))
    safe_print("sent3:", " ".join(sent3))
    safe_print("sent4:", " ".join(sent4))
    safe_print("sent5:", " ".join(sent5))
    safe_print("sent6:", " ".join(sent6))
    safe_print("sent7:", " ".join(sent7))
    safe_print("sent8:", " ".join(sent8))
    safe_print("sent9:", " ".join(sent9))
