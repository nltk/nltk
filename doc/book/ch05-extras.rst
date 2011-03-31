.. -*- mode: rst -*-
.. include:: ../definitions.rst

.. standard global imports

    >>> import nltk, re, pprint

==========================================
5. Categorizing and Tagging Words (Extras)
==========================================

Tagging exhibits several properties that are characteristic of natural
language processing.  First, tagging involves *classification*: words have
properties; many words share the same property (e.g. ``cat`` and ``dog``
are both nouns), while some words can have multiple such properties
(e.g. ``wind`` is a noun and a verb).  Second, in tagging, disambiguation
occurs via *representation*: we augment the representation of tokens with
part-of-speech tags.  Third, training a tagger involves *sequence learning
from annotated corpora*.  Finally, tagging uses *simple, general methods*
such as conditional frequency distributions and transformation-based learning.


List of available taggers:
``http://www-nlp.stanford.edu/links/statnlp.html``

NLTK's HMM tagger, ``nltk.HiddenMarkovModelTagger``

[Abney1996PST]_

``http://en.wikipedia.org/wiki/Part-of-speech_tagging``

.. Dutch example: http://www.askoxford.com/pressroom/archive/odelaunch/
