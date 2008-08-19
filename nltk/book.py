# Natural Language Toolkit: Material for Book
#
# Copyright (C) 2001-2008 NLTK Project
# Author: Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT
#

import nltk, re, pprint

# Chapter 1

moby = nltk.Text(nltk.corpus.gutenberg.words('melville-moby_dick.txt'))
sense = nltk.Text(nltk.corpus.gutenberg.words('austen-sense.txt'))
chat = nltk.Text(nltk.corpus.nps_chat.words())
