.. -*- mode: rst -*-
.. include:: ../definitions.rst

.. _app-reference:

=========================
Python and NLTK Reference
=========================

.. note::
   This appendix is only 10% of its intended size.

----------------
Python Reference
----------------

Python Syntax
-------------

* Statements: appear on a single line; may be broken across multiple lines
  inside parentheses, brackets, or braces; otherwise end line with backslash
  if it is continued on next line; multiple statements may appear on a single
  line if separated with a semicolon
  
* Comments: begin with a ``#`` symbol and continue to the end of the line

* Keywords: and as assert break class continue def del elif else
  except exec finally for from global if import in is lambda not or pass print
  raise return try while with yield (from ``keyword.kwlist``).

* Variable names: a sequence of one or more letters, digits, or underscore; must
  not begin with a digit.

* String literals:
  ``"won't"``,
  ``'Monty said: "Python"'``,
  ``'''Multi-line string'''``,
  ``"""Another multi-line string"""``.

* String literal prefixes: ``u`` for unicode strings; ``r`` for "raw" strings (backslash
  escapes are not processed by interpreter).
 
* Common escape sequences: ``\n`` (linefeed), ``\t`` (tab), ``\uxxxx`` (16-bit unicode
  character, e.g. ``\u03bb`` Greek lambda)

* Operators: ...

* Comparisons: ...

Data Types
----------

* Numeric types |mdash| ``int``, ``float``, ``long`` |mdash| ``3``, ``0.5772``, ``86267571272L``

* Strings |mdash| types ``str``, ``unicode`` |mdash| character sequences delimited with
  quotes as described above.

* Lists |mdash| type ``list`` |mdash| ``[]`` (empty list), ``['Python']``, ``[31, 9]``.

* Tuples |mdash| type ``tuple`` |mdash| ``()`` (empty tuple), ``('Python',)``, ``('the', 9)``



=================================================================================



--------------
NLTK Reference
--------------

This section gives a high-level summary of |NLTK| functionality.  Please see also
the |NLTK| API documentation, HOWTO documents, and source code, accessible
via |NLTK-URL|.



Corpora
-------

Corpus Readers

  =====================================  ===================================================
  Corpus Reader Name                     Corpus Type
  =====================================  ===================================================
  ``BracketParseCorpusReader``           Treebanks represented as nested bracketings
  ``CategorizedPlaintextCorpusReader``   Text collections with document-level categories
  ``CategorizedTaggedCorpusReader``      Categorized, tagged text collections
  ``ChunkedCorpusReader``                Treebank-style bracketed chunked corpora
  ``ConllChunkCorpusReader``             CoNLL-format chunked corpora
  ``NPSChatCorpusReader``                NPS format chat corpus
  ``PlaintextCorpusReader``              Text collections
  ``PPAttachmentCorpusReader``           Prepositional phrase attachment corpus
  ``PropbankCorpusReader``               Proposition Bank corpus
  ``RTECorpusReader``                    Textual entailment corpora
  ``StringCategoryCorpusReader``         Categorized strings (e.g. classified questions)
  ``SwadeshCorpusReader``                Comparative wordlist corpora
  ``SwitchboardCorpusReader``            Transcribed spoken dialogue corpora
  ``TaggedCorpusReader``                 Text collections with word-level tags
  ``ToolboxCorpusReader``                Toolbox and Shoebox data
  ``VerbnetCorpusReader``                Verbnet corpus
  ``WordListCorpusReader``               Wordlists with arbitrary delimiters
  ``WordNetCorpusReader``                WordNet corpus
  ``WordNetICCorpusReader``              Wordnet information content files
  ``XMLCorpusReader``                    Text collections with XML markup
  =====================================  ===================================================


Text Corpus Methods

Unless otherwise specified,
the following methods permit a file or list of files to be specified,
e.g. ``words('1789-Washington.txt')``, ``words(['ca01', 'ca02'])``.  Alternatively,
if the corpus is categorized, then
one or more categories can be specified, e.g. ``words(categories='news')``,
``words(categories=['platinum', 'zinc'])``.

  =========================  ============================================================
  Method Name                Function
  =========================  ============================================================
  ``categories([fileids])``  The categories for a given list of files
  ``raw()``                  A string containing the content of the files or categories
  ``words()``                A list of words and punctuation tokens
  ``sents()``                A list of the sentences of the corpus (not always available)
  ``paras()``                A list of the paragraphs of the corpus (not always available)
  =========================  ============================================================

Tagged Corpus Methods

The following methods all permit files (sometimes categories) to be specified.
Most tagged corpora have a simplified tagset, used if a named parameter
``simplify_tags=True`` is passed to the method.

  =========================  ============================================================
  Method Name                Function
  =========================  ============================================================
  ``tagged_words()``         A list of (token,tag) tuples
  ``tagged_sents()``         A list of the tagged sentences (not always available)
  ``tagged_paras()``         A list of the tagged paragraphs (not always available)
  =========================  ============================================================

Chunked Corpus Methods

Chunked corpora support the ``chunked_sents()`` method.

Parsed Corpus Methods

These support the ``words()``, ``sents()``, ``tagged_words()`` and
``tagged_sents()`` methods.  An additional method is
``parsed_sents()``, which permits the usual parameters.

Dialogue Corpus Methods

[Todo: chat and switchboard interfaces]

Lexical Corpus Methods

These all support the ``words()`` method.  Some have an additional ``entries()``
method which iterates over all entries.  Some have an additional ``dict()``
method which provides dictionary-style access.  For more specialized corpora,
such as PropBank, Senseval, Verbnet, consult the interactive help.

WordNet Corpus Methods

[table of methods]

Word-Level Processing
---------------------

Tokenizers

All tokenizers split a string into a list of strings.

  ===============================  ====================================================================
  Method Name                      Function
  ===============================  ====================================================================
  ``blankline_tokenize(s)``        Split at every blank line
  ``line_tokenize(s)``             Split on newline
  ``regexp_tokenize(s, pattern)``  Split into pieces matching pattern (use ``gaps=True`` to match gaps)
  ``word_tokenize(s)``             Use NLTK's recommended word-level tokenizer
  ===============================  ====================================================================

[sentence tokenization with Punkt]

Stemmers and Lemmatizers

[to do]

Taggers

[to do]


Interfaces to Third-Party Libraries
-----------------------------------

[weka, megam, prover9, maltparser, ...] 


.. include:: footer.rst

