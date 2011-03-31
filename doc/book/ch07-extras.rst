
From: Information Extraction
----------------------------

Assuming the data in ``Locations`` is a table within a relational
database, the question ex-ie1_ can be translated into the SQL query
ex-ie2_.

.. _ex-ie1:
.. ex::
   Which organizations operate in Atlanta?

.. _ex-ie2:
.. ex:: 
   ``select OrgName from locations where LocationName = 'Atlanta'``

When executed, ex-ie2_ will return the required values:

.. table:: tab-db-answers

   +--------------------+
   | OrgName            |
   +====================+
   |BBDO South          |
   +--------------------+
   |Georgia-Pacific     |
   +--------------------+

   Companies that operate in Atlanta

If instead 

From: Tag Patterns
------------------

[...]
except for two differences that make them easier to use for chunking.
First, angle brackets group their contents into atomic
units, so "``<NN>+``" matches one or more repetitions of the tag
``NN``; and "``<NN|JJ>``" matches ``NN`` or ``JJ``.  
Second, the period wildcard operator is
constrained not to cross tag delimiters, so that "``<N.*>``" 
does not match the pair of tags"``<NN><DT>``".


From: Chinking etc
------------------

Two other operations that can be used
for forming chunks are splitting and merging.
A permissive chunking rule might put
`the cat the dog chased`:lx: into a single ``NP`` chunk
because it does not detect that determiners introduce new chunks.
For this we would need a rule to split an ``NP`` chunk
prior to any determiner, using a pattern like: ``"NP: <.*>}{<DT>"``.
Conversely, we can craft rules to merge adjacent chunks under
particular circumstances, e.g. ``"NP: <NN>{}<NN>"``.

A chunk grammar can use any number of chunking, chinking, splitting
and merging patterns in any order.

Multiple Chunk Types
--------------------

So far we have only developed ``NP`` chunkers.  However, it can also
be useful to find other chunk types, including ``PP`` chunks 
(e.g., "because of"), ``VP``
chunks (e.g., "has already delivered"), 
and proper noun chunks
(e.g., "Dewey, Cheatem, and Howe").  Here is an example of a chunked
sentence from the CoNLL-2000 corpus 
that contains ``NP``, ``VP``, and ``PP`` chunk types.

    >>> print conll2000.chunked_sents('train.txt')[99]
    (S
      (PP Over/IN)
      (NP a/DT cup/NN)
      (PP of/IN)
      (NP coffee/NN)
      ,/,
      (NP Mr./NNP Stone/NNP)
      (VP told/VBD)
      (NP his/PRP$ story/NN)
      ./.)

We can generate these chunks using 
a multi-stage chunk grammar, as shown in
code-multistage-chunker_.  It has a stage for each of the chunk types.
We turn on tracing and see the input and output for each stage.
The tracing output shows the rules that are applied,
and inserts braces to identify the chunks that are created at each
stage of processing.
The resulting tree has the expected ``NP``, ``VP`` and ``PP`` chunks.

.. pylisting:: code-multistage-chunker
   :caption: A Multistage Chunker

   cp = nltk.RegexpParser(r"""
     NP: {<DT>?<JJ>*<NN.*>+}    # noun phrase chunks
     VP: {<TO>?<VB.*>}          # verb phrase chunks
     PP: {<IN>}                 # prepositional phrase chunks
     """)
   >>> from nltk.corpus import conll2000
   >>> example = conll2000.chunked_sents('train.txt')[99]
   >>> print cp.parse(example.flatten(), trace=1)
   # Input:
    <IN>  <DT>  <NN>  <IN>  <NN>  <,>  <NNP>  <NNP>  <VBD>  <PRP$>  <NN>  <.> 
   # noun phrase chunks:
    <IN> {<DT>  <NN>} <IN> {<NN>} <,> {<NNP>  <NNP>} <VBD>  <PRP$> {<NN>} <.> 
   # Input:
    <IN>  <NP>  <IN>  <NP>  <,>  <NP>  <VBD>  <PRP$>  <NP>  <.> 
   # verb phrase chunks:
    <IN>  <NP>  <IN>  <NP>  <,>  <NP> {<VBD>} <PRP$>  <NP>  <.> 
   # Input:
    <IN>  <NP>  <IN>  <NP>  <,>  <NP>  <VP>  <PRP$>  <NP>  <.> 
   # prepositional phrase chunks:
   {<IN>} <NP> {<IN>} <NP>  <,>  <NP>  <VP>  <PRP$>  <NP>  <.> 
   (S
     (PP Over/IN)
     (NP a/DT cup/NN)
     (PP of/IN)
     (NP coffee/NN)
     ,/,
     (NP Mr./NNP Stone/NNP)
     (VP told/VBD)
     his/PRP$
     (NP story/NN)
     ./.)


FIND A PLACE FOR THIS:??

Chunking vs Parsing
-------------------

Chunking is akin to parsing (chap-parse_) in the sense
that it serves to build hierarchical structure over text.
However, there are some important differences.
Chunking is not exhaustive, and typically ignores some
items in the input sequence.
Additionally,
chunking creates structures of fixed depth (typically depth 2),
instead of the arbitrarily deep trees created by a parser.
In particular, ``NP`` chunks usually correspond to the
lowest level of ``NP`` grouping identified in a full parse tree,
as illustrated in ex-parsing-chunking_, where (a) shows the full parse
and (b) shows the corresponding chunking:

.. XXX check tree sizes here:

.. _ex-parsing-chunking:
.. ex::
  .. ex::
     .. tree:: (S (NP (CD one) (JJ congressional) (NN aide)) (WP who) (VBD attended)
                     (NP (DT the) (JJ two-hour) (NN meeting)) (VBD said) \.\.\. )
        :scale: 110:110:80

  .. ex::
     .. tree:: (S (NP (CD one) (NBAR (NBAR (JJ congressional) (NN aide)) (SBAR (WP who) (VP (VBD attended)
                     (NP (DT the) (JJ two-hour) (NN meeting)))))) (VP (VBD said) \.\.\.) )

.. XXX there's a big space here in the (current) pdf, after the
   example and before the note -- why?  Might go away with repagination.

.. note::
   A significant motivation for chunking is its robustness and efficiency.
   As we will see in chap-parse_, parsing has problems with robustness,
   given the difficulty in gaining broad coverage while minimizing
   ambiguity.  Parsing is also relatively inefficient: the time taken to
   parse a sentence grows with the cube of the length of the sentence,
   while the time taken to chunk a sentence only grows linearly.



Evaluating Chunk Parsers
------------------------

An easy way to evaluate a chunk parser is to take some already chunked
text, strip off the chunks, rechunk it, and compare the result with
the original chunked text.  The ``ChunkScore.score()`` function takes
the correctly chunked sentence as its first argument, and the newly
chunked version as its second argument, and compares them.  It reports
the fraction of actual chunks that were found (recall), the fraction
of hypothesized chunks that were correct (precision), and the
F-score (see sec-evaluation_).

During evaluation of a chunk parser, it is useful to flatten a chunk
structure into a tree consisting only of a root node and leaves:

    >>> correct = nltk.chunk.tagstr2tree(
    ...    "[ the/DT little/JJ cat/NN ] sat/VBD on/IN [ the/DT mat/NN ]")
    >>> print correct.flatten()
    (S the/DT little/JJ cat/NN sat/VBD on/IN the/DT mat/NN)

We run a chunker over this flattened data, and compare the
resulting chunked sentences with the originals, as follows:


    >>> grammar = r"NP: {<PRP|DT|POS|JJ|CD|N.*>+}"
    >>> cp = nltk.RegexpParser(grammar)
    >>> sentence = [("the", "DT"), ("little", "JJ"), ("cat", "NN"),
    ... ("sat", "VBD"), ("on", "IN"), ("the", "DT"), ("mat", "NN")]
    >>> chunkscore = nltk.chunk.ChunkScore()
    >>> guess = cp.parse(correct.flatten())
    >>> chunkscore.score(correct, guess)
    >>> print chunkscore
    ChunkParse score:
        Precision: 100.0%
        Recall:    100.0%
        F-Measure: 100.0%

``ChunkScore`` is a class for scoring chunk parsers.  It can be used
to evaluate the output of a chunk parser, using precision, recall,
f-measure, missed chunks, and incorrect chunks.  It can also be used
to combine the scores from the parsing of multiple texts.  This is
quite useful if we are parsing a text one sentence at a time.  The
following program listing shows a typical use of the ``ChunkScore``
class.  In this example, ``chunkparser`` is being tested on each
sentence from the Wall Street Journal tagged files.

    >>> grammar = r"NP: {<DT|JJ|NN>+}"
    >>> cp = nltk.RegexpParser(grammar)
    >>> chunkscore = nltk.chunk.ChunkScore()
    >>> for fileid in nltk.corpus.treebank_chunk.fileids()[:5]:
    ...     for chunk_struct in nltk.corpus.treebank_chunk.chunked_sents(fileid):
    ...         test_sent = cp.parse(chunk_struct.flatten())
    ...         chunkscore.score(chunk_struct, test_sent)
    >>> print chunkscore
    ChunkParse score:
        Precision:  42.3%
        Recall:     29.9%
        F-Measure:  35.0%

The overall results of the evaluation can be viewed by printing the
``ChunkScore``.  Each evaluation metric is also returned by an
accessor method: ``precision()``, ``recall``, ``f_measure``,
``missed``, and ``incorrect``.  The ``missed`` and ``incorrect``
methods can be especially useful when trying to improve the
performance of a chunk parser.  Here are the missed chunks:

.. doctest-ignore::
    >>> from random import shuffle
    >>> missed = chunkscore.missed()
    >>> shuffle(missed)
    >>> print missed[:10]
    [(('A', 'DT'), ('Lorillard', 'NNP'), ('spokeswoman', 'NN')),
     (('even', 'RB'), ('brief', 'JJ'), ('exposures', 'NNS')),
     (('its', 'PRP$'), ('Micronite', 'NN'), ('cigarette', 'NN'), ('filters', 'NNS')),
     (('30', 'CD'), ('years', 'NNS')),
     (('workers', 'NNS'),),
     (('preliminary', 'JJ'), ('findings', 'NNS')),
     (('Medicine', 'NNP'),),
     (('Consolidated', 'NNP'), ('Gold', 'NNP'), ('Fields', 'NNP'), ('PLC', 'NNP')),
     (('its', 'PRP$'), ('Micronite', 'NN'), ('cigarette', 'NN'), ('filters', 'NNS')),
     (('researchers', 'NNS'),)]

Here are the incorrect chunks:

.. doctest-ignore::
    >>> incorrect = chunkscore.incorrect()
    >>> shuffle(incorrect)
    >> print incorrect[:10]
    [(('New', 'JJ'), ('York-based', 'JJ')),
     (('Micronite', 'NN'), ('cigarette', 'NN')),
     (('a', 'DT'), ('forum', 'NN'), ('likely', 'JJ')),
     (('later', 'JJ'),),
     (('preliminary', 'JJ'),),
     (('New', 'JJ'), ('York-based', 'JJ')),
     (('resilient', 'JJ'),),
     (('group', 'NN'),),
     (('the', 'DT'),),
     (('Micronite', 'NN'), ('cigarette', 'NN'))]

.. Note: By default, only the first 100 missed chunks and the first
   100 incorrect chunks will be remembered by the ``ChunkScore``.  You
   can tell ``ChunkScore`` to record more chunk examples with the
   ``max_fp_examples`` (maximum false positive examples) and the
   ``max_fn_examples`` (maximum false negative examples) keyword
   arguments to the ``ChunkScore`` constructor:

    >>> chunkscore = nltk.chunk.ChunkScore(max_fp_examples=1000,
    ...                                    max_fn_examples=1000)


Manual Unigram Code
-------------------
In
order to develop a more data-driven approach, code-chunker3_
defines a function ``chunked_tags()`` that takes some chunked data
and sets up a conditional frequency distribution.
For each tag, it counts up the number of times the tag
occurs inside an ``NP`` chunk (the ``True`` case, where ``chtag`` is
``B-NP`` or ``I-NP``), or outside a chunk (the ``False`` case, where
``chtag`` is ``O``).  It returns a list of those tags that occur
inside chunks more often than outside chunks inside-tags_.
We see these tags at line chunked-tags_.
The ``baseline_chunker()`` function obtains this list of tags and
escapes any necessary characters re-escape_,
and constructs a chunk grammar chunk-grammar_ having a single
``NP`` rule whose right hand side is a disjunction of these tags.
Finally, we train the chunker train-chunker_
and test its accuracy test-chunker-accuracy_. 

.. pylisting:: code-chunker3
   :caption: Capturing the conditional frequency of NP Chunk Tags

   def chunked_tags(train):
       """Generate a list of tags that tend to appear inside chunks"""
       cfdist = nltk.ConditionalFreqDist()
       for t in train:
           for word, tag, chtag in nltk.chunk.tree2conlltags(t):
               if chtag == "O":
                   cfdist[tag].inc(False)
               else:
                   cfdist[tag].inc(True)
       return [tag for tag in cfdist.conditions() if cfdist[tag].max() == True] # [_inside-tags]

   def baseline_chunker(train):
       chunk_tags = [re.escape(tag) # [_re-escape]
                     for tag in chunked_tags(train)]
       grammar = 'NP: {<%s>+}' % '|'.join(chunk_tags) # [_chunk-grammar]
       return nltk.RegexpParser(grammar)

   >>> train_sents = conll2000.chunked_sents('train.txt', chunk_types=('NP',))
   >>> print chunked_tags(train_sents) # [_chunked-tags]
   ['#', '$', 'CD', 'DT', 'EX', 'FW', 'JJ', 'JJR', 'JJS', 'NN', 'NNP', 'NNPS', 'NNS',
   'PDT', 'POS', 'PRP', 'PRP$', 'RBS', 'WDT', 'WP', 'WP$']

   >>> train_sents = conll2000.chunked_sents('train.txt', chunk_types=('NP',))
   >>> test_sents  = conll2000.chunked_sents('test.txt', chunk_types=('NP',))
   >>> cp = baseline_chunker(train_sents) # [_train-chunker]
   >>> print nltk.chunk.accuracy(cp, test_sents) # [_test-chunker-accuracy]
   0.914262194736



Training N-Gram Chunkers
------------------------

Our approach to chunking has been to try to detect structure based on
the part-of-speech tags.  We have seen that the IOB format represents
this extra structure using another kind of tag.  The question arises
as to whether we could use the same n-gram tagging methods we saw in
chap-tag_, applied to a different vocabulary. In this case,
rather than trying to determine the correct part-of-speech tag, given
a word, we are trying to determine the correct chunk tag, given a
part-of-speech tag.

From n-gram chunkers
--------------------
Let's look at some of 
the errors it makes.  Consider the opening phrase of the first
sentence of the CONLL chunking data, here shown with part-of-speech
tags:

  Confidence/NN in/IN the/DT pound/NN is/VBZ widely/RB expected/VBN
  to/TO take/VB another/DT sharp/JJ dive/NN

We can try out the unigram chunker on this first sentence by creating
some "tokens" using ``[t for t,c in chunk_data[0]]``, then running
our chunker over them using ``list(unigram_chunker.tag(tokens))``.
The unigram chunker only looks at the tags, and tries to add chunk
tags.  Here is what it comes up with:

  NN/I-NP IN/B-PP DT/B-NP NN/I-NP VBZ/B-VP RB/O VBN/I-VP TO/B-PP
  VB/I-VP DT/B-NP JJ/I-NP NN/I-NP

Notice that it tags all instances of ``NN`` with ``I-NP``, because
nouns usually do not appear at the beginning of noun phrases in
the training data.  Thus, the first noun ``Confidence/NN`` is
tagged incorrectly.  However, ``pound/NN`` and ``dive/NN`` are
correctly tagged as ``I-NP``; they are not in the initial position
that should be tagged ``B-NP``.  The chunker incorrectly tags
``widely/RB`` as ``O``, and it incorrectly tags the
infinitival ``to/TO`` as ``B-PP``, as if it was a preposition starting a
prepositional phrase.

.. [Why these problems might go away if we look at the previous chunk tag?]

Now let's run a bigram chunker:

    >>> bigram_chunker = nltk.BigramTagger(chunk_data, backoff=unigram_chunker)
    >>> eval_tagging_chunker(bigram_chunker)
    Accuracy: 87.6%
    ChunkParse score:
        Precision:  80.6%
        Recall:     87.3%
        F-Measure:  83.8%

We can run the bigram chunker over the same sentence as before
using ``list(bigram_chunker.tag(tokens))``.
Here is what it comes up with:

  NN/B-NP IN/B-PP DT/B-NP NN/I-NP VBZ/B-VP RB/I-VP VBN/I-VP TO/I-VP
  VB/I-VP DT/B-NP JJ/I-NP NN/I-NP

This is 100% correct.


Developing Chunkers
-------------------

Creating a good chunker usually requires several rounds of development
and testing, during which existing rules are refined and new rules are added.
In code-chunker2_, two chunk patterns are applied to the input
sentence.  The first rule finds all sequences of three tokens whose
tags are ``DT``, ``JJ``, and ``NN``, and the second rule finds any
sequence of tokens whose tags are either ``DT`` or ``NN``.
We set up two chunkers, one for each rule ordering,
and test them on the same input.

.. pylisting:: code-chunker2
   :caption: Two Noun Phrase Chunkers Having Identical Rules in Different Orders

   sentence = [("The", "DT"), ("enchantress", "NN"), ("clutched", "VBD"),
                   ("the", "DT"), ("beautiful", "JJ"), ("hair", "NN")]
   cp1 = nltk.RegexpParser(r"""
     NP: {<DT><JJ><NN>}      # Chunk det+adj+noun
         {<DT|NN>+}          # Chunk sequences of NN and DT
     """)
   cp2 = nltk.RegexpParser(r"""
     NP: {<DT|NN>+}          # Chunk sequences of NN and DT
         {<DT><JJ><NN>}      # Chunk det+adj+noun
     """)

   >>> print cp1.parse(sentence, trace=1)
   # Input:
    <DT>  <NN>  <VBD>  <DT>  <JJ>  <NN> 
   # Chunk det+adj+noun:
    <DT>  <NN>  <VBD> {<DT>  <JJ>  <NN>}
   # Chunk sequences of NN and DT:
   {<DT>  <NN>} <VBD> {<DT>  <JJ>  <NN>}
   (S
     (NP The/DT enchantress/NN)
     clutched/VBD
     (NP the/DT beautiful/JJ hair/NN))
   >>> print cp2.parse(sentence, trace=1)
   # Input:
    <DT>  <NN>  <VBD>  <DT>  <JJ>  <NN> 
   # Chunk sequences of NN and DT:
   {<DT>  <NN>} <VBD> {<DT>} <JJ> {<NN>}
   # Chunk det+adj+noun:
   {<DT>  <NN>} <VBD> {<DT>} <JJ> {<NN>}
   (S
     (NP The/DT enchantress/NN)
     clutched/VBD
     (NP the/DT)
     beautiful/JJ
     (NP hair/NN))

Observe that when we chunk material that is already partly chunked,
the chunker will only create chunks that do not partially overlap
existing chunks.  In the case of ``cp2``, the second rule
did not find any chunks, because all chunks that matched
its tag pattern overlapped existing chunks.  As you can see,
you need to be careful to put chunk rules in the right order. 

You might want to test out some of your rules on a corpus. One option
is to use the Brown corpus. However, you need to remember that the
Brown tagset is different from the Penn Treebank tagset that we
have been using for our examples so far in this chapter (see
``nltk.help.brown_tagset()`` and ``nltk.help.upenn_tagset()``
for details).  Because the Brown tagset
uses ``NP`` for proper nouns, in this example we have followed Abney
in labeling noun chunks as ``NX``.

    >>> grammar = (r"""
    ...    NX: {<AT|AP|PP\$>?<JJ.*>?<NN.*>}  # Chunk article/numeral/possessive+adj+noun
    ...        {<NP>+}                       # Chunk one or more proper nouns                   
    ... """)
    >>> cp = nltk.RegexpParser(grammar)
    >>> sent = nltk.corpus.brown.tagged_sents(categories='news')[112]
    >>> print cp.parse(sent)
    (S
      (NX His/PP$ contention/NN)
      was/BEDZ
      denied/VBN
      by/IN
      (NX several/AP bankers/NNS)
      ,/,
      including/IN
      (NX Scott/NP Hudson/NP)
      of/IN
      (NX Sherman/NP)
      ,/,
      (NX Gaynor/NP B./NP Jones/NP)
      of/IN
      (NX Houston/NP)
      ,/,
      (NX J./NP B./NP Brady/NP)
      of/IN
      (NX Harlingen/NP)
      and/CC
      (NX Howard/NP Cox/NP)
      of/IN
      (NX Austin/NP)
      ./.)


----------
Conclusion
----------

In this chapter we have explored efficient and robust methods that can
identify linguistic structures in text.  Using only part-of-speech
information for words in the local context, a "chunker" can
successfully identify simple structures such as noun phrases and verb
groups.  We have seen how chunking methods extend the same lightweight
methods that were successful in tagging.  The resulting structured
information is useful in information extraction tasks and in the
description of the syntactic environments of words.  The latter will
be invaluable as we move to full parsing.

There are a surprising number of ways to chunk a sentence using
regular expressions.  The patterns can add, shift and remove chunks in
many ways, and the patterns can be sequentially ordered in many ways.
One can use a small number of very complex rules, or a long sequence
of much simpler rules.  One can hand-craft a collection of rules, and
one can write programs to analyze a chunked corpus to help in the
development of such rules.  The process is painstaking, but generates
very compact chunkers that perform well and that transparently encode
linguistic knowledge.

It is also possible to chunk a sentence using the techniques of n-gram
tagging.  Instead of assigning part-of-speech tags to words, we assign
IOB tags to the part-of-speech tags.  Bigram tagging turned out to be
particularly effective, as it could be sensitive to the chunk tag on
the previous word.  This statistical approach requires far less effort
than rule-based chunking, but creates large models and delivers few
linguistic insights.

Like tagging, chunking cannot be done perfectly.  For example, as
pointed out by Abney, we cannot correctly analyze the structure
of the sentence *I turned off the spectroroute* without knowing the
meaning of *spectroroute*; is it a kind of road or a type of device?
Without knowing this, we cannot tell whether *off* is part of a
prepositional phrase indicating direction (tagged ``B-PP``), or
whether *off* is part of the verb-particle construction *turn off*
(tagged ``I-VP``).

A recurring theme of this chapter has been `diagnosis`:dt:.  The simplest
kind is manual, when we inspect the tracing output of a chunker and
observe some undesirable behavior that we would like to fix.
Sometimes we discover cases where we cannot hope to get the correct
answer because the part-of-speech tags are too impoverished and do not
give us sufficient information about the lexical item.  A second
approach is to write utility programs to analyze the training data,
such as counting the number of times a given part-of-speech tag occurs
inside and outside an ``NP`` chunk.  A third approach is to evaluate the
system against some gold standard data to obtain an overall
performance score.  We can even use this to parameterize the system,
specifying which chunk rules are used on a given run, and tabulating
performance for different parameter combinations.  Careful use of
these diagnostic methods permits us to optimize the performance of our
system.  We will see this theme emerge again later in chapters dealing
with other topics in natural language processing.
