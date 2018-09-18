Natural Language Toolkit
========================

NLTK is a leading platform for building Python programs to work with human language data.
It provides easy-to-use interfaces to `over 50 corpora and lexical
resources <http://nltk.org/nltk_data/>`_ such as WordNet,
along with a suite of text processing libraries for classification, tokenization, stemming, tagging, parsing, and semantic reasoning,
wrappers for industrial-strength NLP libraries,
and an active `discussion forum <http://groups.google.com/group/nltk-users>`_.

Thanks to a hands-on guide introducing programming fundamentals alongside topics in computational linguistics, plus comprehensive API documentation,
NLTK is suitable for linguists, engineers, students, educators, researchers, and industry users alike.
NLTK is available for Windows, Mac OS X, and Linux. Best of all, NLTK is a free, open source, community-driven project.

NLTK has been called "a wonderful tool for teaching, and working in, computational linguistics using Python,"
and "an amazing library to play with natural language."

`Natural Language Processing with Python <http://nltk.org/book>`_ provides a practical
introduction to programming for language processing.
Written by the creators of NLTK, it guides the reader through the fundamentals
of writing Python programs, working with corpora, categorizing text, analyzing linguistic structure,
and more.
The online version of the book has been been updated for Python 3 and NLTK 3.
(The original Python 2 version is still available at `http://nltk.org/book_1ed <http://nltk.org/book_1ed>`_.)

Some simple things you can do with NLTK
---------------------------------------

Tokenize and tag some text:

    >>> import nltk
    >>> sentence = """At eight o'clock on Thursday morning
    ... Arthur didn't feel very good."""
    >>> tokens = nltk.word_tokenize(sentence)
    >>> tokens
    ['At', 'eight', "o'clock", 'on', 'Thursday', 'morning',
    'Arthur', 'did', "n't", 'feel', 'very', 'good', '.']
    >>> tagged = nltk.pos_tag(tokens)
    >>> tagged[0:6]
    [('At', 'IN'), ('eight', 'CD'), ("o'clock", 'JJ'), ('on', 'IN'),
    ('Thursday', 'NNP'), ('morning', 'NN')]

Identify named entities:

    >>> entities = nltk.chunk.ne_chunk(tagged)
    >>> entities
    Tree('S', [('At', 'IN'), ('eight', 'CD'), ("o'clock", 'JJ'),
               ('on', 'IN'), ('Thursday', 'NNP'), ('morning', 'NN'),
           Tree('PERSON', [('Arthur', 'NNP')]),
               ('did', 'VBD'), ("n't", 'RB'), ('feel', 'VB'),
               ('very', 'RB'), ('good', 'JJ'), ('.', '.')])

Display a parse tree:

    >>> from nltk.corpus import treebank
    >>> t = treebank.parsed_sents('wsj_0001.mrg')[0]
    >>> t.draw()

.. image:: images/tree.gif

NB. If you publish work that uses NLTK, please cite the NLTK book as
follows:

	Bird, Steven, Edward Loper and Ewan Klein (2009), *Natural Language Processing with Python*.  O'Reilly Media Inc.

Next Steps
----------

* `sign up for release announcements <http://groups.google.com/group/nltk>`_
* `join in the discussion <http://groups.google.com/group/nltk-users>`_

Contents
========


.. toctree::
   :maxdepth: 1

   news
   install
   data
   contribute
   FAQ <https://github.com/nltk/nltk/wiki/FAQ>
   Wiki <https://github.com/nltk/nltk/wiki> 
   API <api/nltk>
   HOWTO <http://www.nltk.org/howto>

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
