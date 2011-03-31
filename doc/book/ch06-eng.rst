.. -*- mode: rst -*-
.. include:: ../definitions.rst

.. standard global imports

    >>> import nltk, re, pprint

.. _chap-engineering:

===============================
6. Language Engineering (Draft)
===============================

------------
Introduction
------------

**This chapter is a rough draft only**

----------
Evaluation
----------


Scoring Accuracy
----------------

Testing a language processing system over its training data is unwise.
A system which simply memorized the training data would get a perfect
score without doing any linguistic modeling.  Instead, we would like
to reward systems that make good generalizations, so we should test
against *unseen data*.
We can then define the two sets of data as follows:

    >>> train_sents  = nltk.corpus.brown.tagged_sents(categories='news')[:500]
    >>> unseen_sents = nltk.corpus.brown.tagged_sents(categories='news')[500:600] # sents 500-599

Now we train the tagger using ``train_sents`` and evaluate it using
``unseen_sents``, as follows:

    >>> default_tagger = nltk.DefaultTagger('NN')
    >>> unigram_tagger = nltk.UnigramTagger(backoff=default_tagger)
    >>> unigram_tagger.train(train_sents)
    >>> print tag.accuracy(unigram_tagger, unseen_sents)
    .746

The accuracy scores produced by this evaluation method are lower, but
they give a more realistic picture of the performance of the tagger.
Note that the performance of any statistical tagger is highly
dependent on the quality of its training set. In particular, if the
training set is too small, it will not be able to reliably estimate
the most likely tag for each word. Performance will also suffer if the
training set is significantly different from the texts we wish to tag.

Baseline Performance
--------------------

It is difficult to interpret an accuracy score in isolation.  For
example, is a person who scores 25% in a test likely to know a quarter
of the course material?  If the test is made up of 4-way multiple
choice questions, then this person has not performed any better than
chance.  Thus, it is clear that we should *interpret* an accuracy
score relative to a *baseline*.  The choice of baseline is somewhat
arbitrary, but it usually corresponds to minimal knowledge about the
domain.

In the case of tagging, a  possible baseline score can be found by
tagging every word with ``NN``, the most likely tag.

    >>> baseline_tagger = tag.Default('nn')
    >>> acc = tag.accuracy(baseline_tagger, nltk.corpus.brown.tagged_sents(categories='news'))
    >>> print 'Accuracy = %4.1f%%' % (100 * acc)
    Accuracy = 13.1%

Unfortunately this is not a very good baseline.  There are many
high-frequency words which are not nouns.  Instead we could use the standard
unigram tagger to get a baseline of 75%.  However, this does not seem
fully legitimate: the unigram's model covers all words seen during
training, which hardly seems like 'minimal knowledge'.  Instead, let's
only permit ourselves to store tags for the most frequent words.

The first step is to identify the most frequent words in the corpus,
and for each of these words, identify the most likely tag:

    >>> wordcounts = nltk.FreqDist()
    >>> wordtags = nltk.ConditionalFreqDist()
    >>> for (word, tag) in nltk.corpus.brown.tagged_words(categories='news'):
    ...         wordcounts.inc(word)    # count the word
    ...         wordtags[w].inc(tag)    # count the word's tag
    >>> frequent_words = wordcounts.sorted()[:1000]

Now we can create a lookup table (a dictionary) which maps words to
likely tags, just for these high-frequency words.  We can then define
a new baseline tagger which uses this lookup table:

    >>> table = dict((word, wordtags[word].max()) for word in frequent_words)
    >>> baseline_tagger = nltk.LookupTagger(table, nltk.DefaultTagger('nn'))
    >>> acc = tag.accuracy(baseline_tagger, nltk.corpus.brown.tagged_sents(categories='news'))
    >>> print 'Accuracy = %4.1f%%' % (100 * acc)
    Accuracy = 72.5%

This, then, would seem to be a reasonable baseline score for a
tagger.  When we build new taggers, we will only credit ourselves for
performance exceeding this baseline.

Error Analysis
--------------

While the accuracy score is certainly useful, it does not tell us how
to improve the tagger.  For this we need to undertake error analysis.
For instance, we could construct a *confusion matrix*, with a row and
a column for every possible tag, and entries that record how often a
word with tag *T*\ :subscript:`i` is incorrectly tagged as *T*\ :subscript:`j`
Another approach is to analyze the context of the errors, which is what
we do now.

Consider the following program, which catalogs all errors
along with the tag on the left and their frequency of occurrence.

    >>> errors = {}
    >>> for i in range(len(unseen_sents)):
    ...     raw_sent = tag.untag(unseen_sents[i])
    ...     test_sent = unigram_tagger.tag(raw_sent)
    ...     unseen_sent = unseen_sents[i]
    ...     for j in range(len(test_sent)):
    ...         if test_sent[j][1] != unseen_sent[j][1]:
    ...             test_context = test_sent[j-1:j+1]
    ...             gold_context = unseen_sent[j-1:j+1]
    ...             if None not in test_context:
    ...                 pair = (tuple(test_context), tuple(gold_context))
    ...                 if pair not in errors:
    ...                     errors[pair] = 0
    ...                 errors[pair] += 1

The ``errors`` dictionary has keys
of the form ``((t1,t2),(g1,g2))``, where ``(t1,t2)`` are the test
tags, and ``(g1,g2)`` are the gold-standard tags.  The values in the
``errors`` dictionary are simple counts of how often each error
occurred.  With some further processing, we construct the list
``counted_errors`` containing tuples consisting of counts and errors,
and then do a reverse sort to get the most significant errors first:

    >>> counted_errors = [(errors[k], k) for k in errors.keys()]
    >>> counted_errors.sort()
    >>> counted_errors.reverse()
    >>> for err in counted_errors[:5]:
    ...     print err
    (32, ((), ()))
    (5, ((('the', 'at'), ('Rev.', 'nn')),
         (('the', 'at'), ('Rev.', 'np'))))
    (5, ((('Assemblies', 'nn'), ('of', 'in')),
         (('Assemblies', 'nns-tl'), ('of', 'in-tl'))))
    (4, ((('of', 'in'), ('God', 'nn')),
         (('of', 'in-tl'), ('God', 'np-tl'))))
    (3, ((('to', 'to'), ('form', 'nn')),
         (('to', 'to'), ('form', 'vb'))))

The fifth line of output records the fact that there were 3 cases
where the unigram tagger mistakenly tagged a verb as a noun, following
the word `to`:lx:.  (We encountered the inverse of this mistake for the word
`increase`:lx: in the above evaluation table, where the unigram tagger tagged
`increase`:lx: as a verb instead of a noun since it occurred more often
in the training data as a verb.)  Here, when `form`:lx: appears
after the word `to`:lx:, it is invariably a verb.  Evidently, the performance
of the tagger would improve if it was modified to consider not just
the word being tagged, but also the tag of the word on the left.  Such
taggers are known as bigram taggers, and we consider them in the next section.


Exercises
---------

#. |soso| Read up on the TnT tagger, and experiment with ``nltk_contrib.tnt``.
   ``http://www.aclweb.org/anthology/A00-1031``

#. |hard| **Tagger context**:

   N-gram taggers choose a tag for a token based on its text and the
   tags of the *n-1* preceding tokens. This is a common context to use
   for tagging, but certainly not the only possible context.

   a) Construct a new tagger, sub-classed from ``SequentialTagger``, that
      uses a different context. If your tagger's context contains
      multiple elements, then you should combine them in a
      tuple. Some possibilities for elements to include are: (i)
      the current word or a previous word; (ii) the length
      of the current word text or of the previous word; (iii)
      the first letter of the current word or the previous word;
      or (iv) the previous tag.  Try to choose
      context elements that you believe will help the tagger decide which
      tag is appropriate. Keep in mind the trade-off between more
      specific taggers with accurate results; and more general taggers
      with broader coverage.  Combine your tagger with other taggers
      using the backoff method.

   #) How does the combined tagger's accuracy compare to the basic tagger? 

   #) How does the combined tagger's accuracy compare to the combined taggers you
      created in the previous exercise? 

#. |hard| **Tagging out-of-vocabulary words**:
   Develop a version of the n-gram backoff tagger that stores a vocabulary
   of the `n`:math: most frequent words seen during training, and maps
   all other words to the special word ``UNK`` (unknown).  This word will
   occur with a variety of tags, and the n-gram tagger will be able to use
   the context of the preceding tags to disambiguate.  For example,
   if the word `blog`:lx: is not in the vocabulary, a training sentence
   containing ``the/dt blog/nn`` would be treated as ``the/dt UNK/nn``,
   and ``to/to blog/vb`` would be treated as ``to/to UNK/vb``.
   The n-gram backoff taggers will work in the usual way, to tag
   ``UNK`` in contexts that were not observed during training.

#. |hard| **Reverse sequential taggers**:
   Since sequential taggers tag tokens in order, one at a time, they
   can only use the predicted tags to the *left* of the current token
   to decide what tag to assign to a token. But in some cases, the
   *right* context may provide more useful information than the left
   context.  A reverse sequential tagger starts with the last word of the
   sentence and, proceeding in right-to-left order, assigns tags to words
   on the basis of the tags it has already predicted to the right.
   By reversing texts at appropriate times, we can use NLTK's existing
   sequential tagging classes to perform reverse sequential
   tagging: reverse the training text before training the tagger;
   and reverse the text being tagged both before and after.

   a) Use this technique to create a bigram reverse sequential tagger.

   #) Measure its accuracy on a tagged section of the Brown corpus. Be
      sure to use a different section of the corpus for testing than you
      used for training.

   #) How does its accuracy compare to a left-to-right bigram
      tagger, using the same training data and test data?
        
#. |hard| **Alternatives to backoff**:
   Create a new kind of tagger that combines several taggers using
   a new mechanism other than backoff (e.g. voting).  For robustness
   in the face of unknown words, include a regexp tagger, a unigram
   tagger that removes a small number of prefix or suffix characters
   until it recognizes a word, or an n-gram tagger that does not
   consider the text of the token being tagged.
        
#. |hard| **Comparing n-gram taggers and Brill taggers**:
   Investigate the relative performance of n-gram taggers with backoff
   and Brill taggers as the size of the training data is increased.
   Consider the training time, running time, memory usage, and accuracy,
   for a range of different parameterizations of each technique.




Grammar Engineering
-------------------

* regression testing, test suites
* reliability

-----------------
Language Modeling
-----------------

* n-gram modeling, Maximum Likelihood Estimation ``nltk.MLEProbDist``
* sparse data problem
* smoothing, estimation
* simple estimation:
  Expected Likelihood Estimation ``nltk.ELEProbDist``,
  Laplace Estimation ``nltk.LaplaceProbDist``,
  Lidstone Estimatio ``nltk.LidstoneProbDist``.
* advanced estimation:
  Heldout Estimation ``nltk.HeldoutProbDist``,
  Good-Turing Estimation ``nltk.GoodTuringProbDist``,
  Witten-Bell Estimation ``nltk.WittenBellProbDist``.

----------------
Machine Learning
----------------

* Example problems in text classification, e.g. question classification, language identification
* supervised vs unsupervised
* knowledge engineering approach (rule-based; hand-crafted)
* machine learning approach (learn rules from annotated corpora)
* many NLP tasks can be easily construed as classification tasks, e.g. tagging
* even tokenization can be viewed as a boolean classification task: for each letter of the input, is the letter immediately followed by a token boundary?
* in tagging, we used the identity of the word, optionally with the tag(s) of preceding word(s)
* German example: capitalization a relevant feature for unknown words


Feature Selection and Extraction
--------------------------------

* features as attributes of linguistic entities
* boolean vs scalar
* dictionary representation

Example of some possible features for the word `Melbourne`:lx:.
Note that the feature names are arbitrary strings.

    >>> word123['initial_capital'] = True
    >>> word123['length'] = 9
    >>> word123['vowels'] = 4
    >>> word123['endswith(e)'] = True
    >>> word123['endswith(f)'] = False

Its obvious we can have a large number of features.
The issue becomes one of feature selection...


Text Classification
-------------------

* sequence classification (HMM, TBL)
* unsupervised learning (clusterers)

Hybrid Approaches
-----------------

* rules vs features
* refer back to introduction chapter


Problems with Tagging
---------------------

* what context is relevant?
* how best to combine taggers?
* sensitivity to lexical identity?
* ngram tagging produces large models, uninterpretable
  cf Brill tagging, which has smaller, linguistically-interpretable models

.. Discussion of how statistical methods have been used to
   reach a linguistically interpretable, symbolic result.
   Contrast between n-gram and Brill tagger about whether
   we can learn anything from inspecting the model itself
   (n-gram data vs transformational rules).


-------
Summary
-------

connection to Part II


---------------
Further Reading
---------------


-------------------------------
Old Material to be incorporated
-------------------------------

This chapter will cover evaluation, trade-offs between methods that
create large vs small models (e.g. n-gram tagging vs Brill tagging).

.. TODO: spell checking example	
.. TODO: confusion matrix


.. note:: Remember that our program samples assume you
   begin your interactive session or your program with: ``import nltk, re, pprint``
   

.. TODO: IE evaluations:
   
   TIPSTER (1991-1998) incl MUC
   ACE (since 2000)
   - entity detection and recognition (extract mentions, group references to same entities)
   - relation detection and recognition
   - event detection
   - Arabic, Chinese, English
   GALE (since 2005)
   - Global Autonomous Language Exploitation
   - information extracted from multilingual input
   - from transcribed or translated text
   - identify information relevant to a user's query
   - so no pre-defined ontology (challenge for current IE systems)
   CoNLL (since 1997) -- bottom up initiative


-----------
Conclusions
-----------

[To be written]

.. _sec-engineering-further-reading:

---------------
Further Reading
---------------

* probability, estimation (Manning and Schutze, ch 2, 6)

.. Sekine -- 140 types of NE.

.. include:: footer.rst

