.. -*- mode: rst -*-
.. include:: ../definitions.rst

.. standard global imports

    >>> from __future__ import division
    >>> import nltk, re, pprint


.. TODO:
   discuss applications of unify() to dicts, lists, and mixtures of dicts and lists
   FeatureValueTuple: '[x=(1,2,3)]'
   FeatureValueSet: '[x={1,2,3}]'
   NB: Unification does *not* descend into tuples or sets; but variable
   substitution from bindings does.  Generally speaking, tuples and set
   feature values should never contain feature structures.
   FeatureValueUnion: '{?a+?b}', which will automatically collapse to a
   FeatureValueSet as soon as all top-level variables are replaced with set values.
   As with FeatureValueSet, unification does not descend into FeatureValueUnion,
   but variable binding does.
   More examples are in Edward's email of 25 August

.. _chap-featgram:

==================================
9. Building Feature Based Grammars
==================================

------------
Introduction
------------

Imagine you are building a spoken dialogue
system to answer queries about train schedules in Europe. ex-train0_
illustrates one of the input
sentences that the system should handle.

.. _ex-train0:
.. ex::
      Which stations does the 9.00 express from Amsterdam to Paris stop at?

The information that the customer is seeking is not exotic |mdash| the
system back-end just needs to look up the list of stations on the
route, and reel them off. But you have to be careful in giving the
correct semantic interpretation to
ex-train0_. You don't want to end up with the
system trying to answer ex-train1_ instead: 

.. _ex-train1:
.. ex::
      Which station does the 9.00 express from Amsterdam terminate at?

Part of your solution might use domain knowledge to figure out that if
a speaker knows that the train is a train to Paris, then she probably
isn't asking about the terminating station in ex-train0_. But the
solution will also involve recognizing the syntactic structure of the
speaker's query.  In particular, your analyzer must recognize that
there is a syntactic connection between the question phrase `which
stations`:lx:, and the phrase `stop at`:lx: at the end ex-train0_. The
required interpretation is made clearer in the "quiz question version
shown in ex-train2_, where the question phrase fills the "gap" that is
implicit in ex-train0_:

.. _ex-train2:
.. ex::
      The 9.00 express from Amsterdam to Paris stops at which stations?

The `long-distance dependency`:dt: between an initial question phrase
and the gap that it semantically connects to cannot be recognized by
techniques we have presented in earlier chapters. For example, we
can't use n-gram based language models; in practical terms, it is
infeasible to observe the n-grams for a big enough value of
*n*. Similarly, chunking grammars only attempt to capture local
patterns, and therefore just don't "see" long-distance dependencies.
In this chapter, we will show how syntactic features can be used to
provide a simple yet effective technique for keeping track of
long-distance dependencies in sentences.

Features are helpful too for dealing with purely local dependencies.
Consider the German questions ex-germanagr_:

.. _ex-germanagr:
.. ex::
   .. _ex-germanagra:
   .. gloss::
      Welche  |  Studenten       | kennen  | Franz?
      which   |  student.PL      | know.PL  | Franz
      'which students know Franz?'               

   .. _ex-germanagrb:
   .. gloss::
      Welche  |  Studenten       | kennt   | Franz?
      which   |  student.PL      | know.SG  | Franz
      'which students does Franz know?' 

The only way of telling which noun phrase is the subject of
`kennen`:lx: ('know') and which is the object is by looking at the
agreement inflection on the verb |mdash| word order is no help to us
here. Since verbs in German agree in number with their subjects, the
plural form `kennen`:lx: requires `Welche Studenten`:lx: as subject,
while the singular form `kennt`:lx: requires `Franz`:lx: as
subject. The fact that subjects and verbs must agree in number can be
expressed within the |CFG|\ s that we presented in Chapter
chap-parse_. But capturing the fact that the interpretations of
ex-germanagra_ and ex-germanagrb_ differ is more challenging. In this
chapter, we will only examine the syntactic aspect of local
dependencies such as number agreement. In Chapter chap-semantics_, we
will demonstrate how feature-based grammars can be extended so that
they build a representation of meaning in parallel with a
representation of syntactic structure.

-------------
Why Features?
-------------

We have already used the term "feature" a few times, without saying
what it means. What's special about feature-based grammars? The core
ideas are probably already familiar to you. To make things concrete,
let's look at the simple phrase `these dogs`. It's composed of two
words. We'll be a bit abstract for the moment, and call these words
`a` and `b`. We'll be modest, and assume that we do not know
`everything`:em: about them, but we can at least give a partial
description. For example, we know that the orthography of `a` is
`these`:lx:, its phonological form is `DH IY Z`,  its part-of-speech is
``Det``, and its number is plural. We can use dot notation to record
these observations: 

.. _ex-feat0:
.. ex::
   .. parsed-literal::

      `a.spelling` = `these`:lx:
      `a.phonology` = `DH IY Z`
      `a.pos` = ``Det``
      `a.number` = plural

Thus ex-feat0_ is a `partial description` of a word; it lists some
attributes, or features, of the word, and declares their values. There
are other attributes that we might be interested in, which have
not been specified; for example, what head the word is dependent on
(using the notion of dependency discussed in Chapter chap-parse_), and
what the lemma of the word is. But this omission of some attributes is
exactly what you would expect from a partial description! 

.. 
 The framework of context-free grammars that we presented in Chapter
 chap-parse_ describes syntactic constituents with the help of a
 limited set of category labels. These atomic labels are adequate for
 talking about the gross structure of sentences. But when we start to
 make finer grammatical distinctions it becomes awkward to enrich the
 set of categories in a systematic manner. In this chapter we will
 address this challenge by decomposing categories using features
 (somewhat similar to the key-value pairs of Python dictionaries). 

We will start off this chapter by looking more closely at the
phenomenon of syntactic agreement; we will show how agreement
constraints can be expressed elegantly using features, and illustrate
their use in a simple grammar. Feature structures are a general data
structure for representing information of any kind; we will briefly
look at them from a more formal point of view, and explain how to
create feature structures in Python. In the final part of the chapter,
we demonstrate that the additional expressiveness of features opens
out a wide spectrum of possibilities for describing sophisticated
aspects of linguistic structure.


Syntactic Agreement
-------------------

Consider the following contrasts:

.. _ex-thisdog:
.. ex::
   .. ex::
      this dog
   .. ex::
      \*these dog

.. _ex-thesedogs:
.. ex::
   .. ex::
      these dogs
   .. ex::
      \*this dogs

|nopar| In English, nouns are usually morphologically marked as being singular
or plural. The form of the demonstrative also varies:
`this`:lx: (singular) and `these`:lx: (plural).
Examples ex-thisdog_ and ex-thesedogs_ show that there are constraints on
the use of demonstratives and nouns within a noun phrase:
either both are singular or both are plural. A similar
constraint holds between subjects and predicates:

.. _ex-subjpredsg:
.. ex::
   .. ex::
      the dog runs
   .. ex::
      \*the dog run

.. _ex-subjpredpl:
.. ex::
   .. ex::
      the dogs run
   .. ex::
      \*the dogs runs


.. Proposed for deletion: The element which determines the
   agreement, here the subject noun phrase, is called the agreement
   `controller`:dt:, while the element whose form is determined by
   agreement, here the verb, is called the `target`:dt:.

|nopar| Here we can see that morphological properties of the verb co-vary
with syntactic properties of the subject noun phrase.  This co-variance is
called `agreement`:dt:.
If we look further at verb agreement in English, we will see that
present tense verbs typically have two inflected forms: one for third person
singular, and another for every other combination of person and number:

.. table:: tab-agreement-paradigm

    +------------+-------------+----------+
    |            |**singular** |**plural**|
    +------------+-------------+----------+
    |**1st per** |*I run*      |*we run*  |
    |            |             |          |
    +------------+-------------+----------+
    |**2nd per** |*you run*    |*you run* |
    |            |             |          |
    +------------+-------------+----------+
    |**3rd per** |*he/she/it   |*they run*|
    |            |runs*        |          |
    +------------+-------------+----------+

    Agreement Paradigm for English Regular Verbs

We can make the role of morphological properties a bit more explicit
as illustrated in ex-runs_ and ex-run_. These representations indicate that
the verb agrees with its subject in person and number. (We use "3" as
an abbreviation for 3rd person, "SG" for singular and "PL" for plural.)

.. _ex-runs:
.. gloss::
   the | dog       |run-s
       | dog.3.SG  |run-3.SG

.. _ex-run:
.. gloss::
   the | dog-s     |run          
       | dog.3.PL  |run-3.PL 

Let's see what happens when we encode these agreement constraints in a
context-free grammar.  We will begin with the simple CFG in ex-agcfg0_.

.. _ex-agcfg0:
.. ex::
   .. parsed-literal::

     ``S`` |rarr| ``NP VP``
     ``NP`` |rarr| `Det n`:gc: 
     ``VP`` |rarr| ``V`` 

     ``Det`` |rarr| 'this'
     ``N`` |rarr| 'dog'
     ``V`` |rarr| 'runs'

|nopar| Example ex-agcfg0_ allows us to generate the sentence `this dog runs`:lx:;
however, what we really want to do is also generate `these dogs
run`:lx: while blocking unwanted strings such as `*this dogs run`:lx:
and `*these dog runs`:lx:. The most straightforward approach is to
add new non-terminals and productions to the grammar:

.. _ex-agcfg1:
.. ex::
   .. parsed-literal::

     `S_SG`:gc: |rarr| `NP_SG VP_SG`:gc:
     `S_PL`:gc: |rarr| `NP_PL VP_PL`:gc:
     `NP_SG`:gc: |rarr| `Det_SG N_SG`:gc: 
     `NP_PL`:gc: |rarr| `Det_PL N_PL`:gc: 
     `VP_SG`:gc: |rarr| `V_SG`:gc: 
     `VP_PL`:gc: |rarr| `V_PL`:gc: 

     `Det_SG`:gc: |rarr| 'this'
     `Det_PL`:gc: |rarr| 'these'
     `N_SG`:gc: |rarr| 'dog'
     `N_PL`:gc: |rarr| 'dogs'
     `V_SG`:gc: |rarr| 'runs'
     `V_PL`:gc: |rarr| 'run'

|nopar| It should be clear that this grammar will do the required
task, but only at the cost of duplicating our previous set of
productions.

.. Rule multiplication is of course more severe if we add in
   person agreement constraints.
   "rule multiplication" will be meaningless to some readers.
   We need to be consistent in referring to these as productions.


Using Attributes and Constraints
--------------------------------

We spoke informally of linguistic categories having *properties*; for
example, that a noun has the property of being plural. Let's
make this explicit:

.. _ex-num0:
.. ex::
   .. parsed-literal::

     ``N``\ [`num`:feat:\ =\ `pl`:fval:\ ]

|nopar| In ex-num0_, we have introduced some new notation which says that the
category ``N`` has a `feature`:dt: called `num`:feat: (short for
'number') and that the value of this feature is `pl`:fval: (short for
'plural'). We can add similar annotations to other categories, and use
them in lexical entries:

.. _ex-agcfg2:
.. ex::
   .. parsed-literal::

     ``Det``\ [`num`:feat:\ =\ `sg`:fval:\ ] |rarr| 'this'
     ``Det``\ [`num`:feat:\ =\ `pl`:fval:\ ]  |rarr| 'these'
     ``N``\ [`num`:feat:\ =\ `sg`:fval:\ ] |rarr| 'dog'
     ``N``\ [`num`:feat:\ =\ `pl`:fval:\ ] |rarr| 'dogs'
     ``V``\ [`num`:feat:\ =\ `sg`:fval:\ ] |rarr| 'runs'
     ``V``\ [`num`:feat:\ =\ `pl`:fval:\ ] |rarr| 'run'

|nopar| Does this help at all? So far, it looks just like a slightly more
verbose alternative to what was specified in ex-agcfg1_. Things become
more interesting when we allow *variables* over feature values, and use
these to state constraints:

.. _ex-agcfg3:
.. ex::
   .. _ex-srule:
   .. ex::
      .. parsed-literal::

        ``S`` |rarr| ``NP``\ [`num`:feat:\ =\ `?n`:math:\ ] ``VP``\ [`num`:feat:\ =\ `?n`:math:\ ]

   .. _ex-nprule:
   .. ex::
      .. parsed-literal::

       ``NP``\ [`num`:feat:\ =\ `?n`:math:\ ] |rarr| ``Det``\ [`num`:feat:\ =\ `?n`:math:\ ] ``N``\ [`num`:feat:\ =\ `?n`:math:\ ]

   .. _ex-vprule:
   .. ex::
      .. parsed-literal::

       ``VP``\ [`num`:feat:\ =\ `?n`:math:\ ] |rarr| ``V``\ [`num`:feat:\ =\ `?n`:math:\ ]

|nopar| We are using "`?n`:math:" as a variable over values of `num`:feat:; it can
be instantiated either to `sg`:fval: or `pl`:fval:. Its scope is
limited to individual productions. That is, within ex-srule_, for example,
`?n`:math: must be instantiated to the same constant value; we can
read the production as saying that whatever value ``NP`` takes for the feature
`num`:feat:, ``VP`` must take the same value. 

In order to understand how these feature constraints work, it's
helpful to think about how one would go about building a tree. Lexical
productions will admit the following local trees (trees of
depth one):

.. ex::
   .. _ex-this:
   .. ex:: 
      .. tree:: (Det[NUM=sg] this) 
   .. _ex-these:
   .. ex:: 
      .. tree:: (Det[NUM=pl] these) 

.. ex::
   .. _ex-dog:
   .. ex:: 
      .. tree:: (N[NUM=sg] dog) 
   .. _ex-dogs:
   .. ex:: 
      .. tree:: (N[NUM=pl] dogs) 

|nopar| Now ex-nprule_ says that whatever the `num`:feat: values of ``N`` and
``Det`` are, they have to be the same. Consequently, ex-nprule_ will
permit ex-this_ and ex-dog_ to be combined into an ``NP`` as shown in
ex-good1_ and it will also allow ex-these_ and ex-dogs_ to be combined, as in
ex-good2_. By contrast, ex-bad1_ and ex-bad2_ are prohibited because the roots
of their
constituent local trees differ in their values for the `num`:feat: feature.

.. ex::
   .. _ex-good1:
   .. ex::
      .. tree:: (NP[NUM=pl] (Det[NUM=sg] this)(N[NUM=sg] dog))

   .. _ex-good2:
   .. ex::
      .. tree:: (NP[NUM=pl] (Det[NUM=pl] these)(N[NUM=pl] dogs))

.. ex::
   .. _ex-bad1:
   .. ex::
      .. tree:: (NP[NUM=...] (Det[NUM=sg] this)(N[NUM=pl] dogs))

   .. _ex-bad2:
   .. ex::
      .. tree:: (NP[NUM=...] (Det[NUM=PL] these)(N[NUM=SG] dog))

Production ex-vprule_ can be thought of as saying that the `num`:feat: value of the
head verb has to be the same as the `num`:feat: value of the ``VP``
mother. Combined with ex-srule_, we derive the consequence that if the
`num`:feat: value of the subject head noun is `pl`:fval:, then so is
the `num`:feat: value of the ``VP``\ 's head verb.

.. ex::
   .. tree:: (S (NP[NUM=pl] (Det[NUM=pl] these)(N[NUM=pl] dogs))(VP[NUM=pl] (V[NUM=pl] run)))

The grammar in Example code-feat0cfg_ illustrates most of the ideas we have introduced so
far in this chapter, plus a couple of new ones.

.. pylisting:: code-feat0cfg
   :caption: Example Feature-Based Grammar

   >>> nltk.data.show_cfg('grammars/book_grammars/feat0.fcfg')
   % start S
   # ############################
   # Grammar Rules
   # ############################
   # S expansion rules
   S -> NP[NUM=?n] VP[NUM=?n]
   # NP expansion rules
   NP[NUM=?n] -> N[NUM=?n] 
   NP[NUM=?n] -> PropN[NUM=?n] 
   NP[NUM=?n] -> Det[NUM=?n] N[NUM=?n]
   NP[NUM=pl] -> N[NUM=pl] 
   # VP expansion rules
   VP[TENSE=?t, NUM=?n] -> IV[TENSE=?t, NUM=?n]
   VP[TENSE=?t, NUM=?n] -> TV[TENSE=?t, NUM=?n] NP
   # ############################
   # Lexical Rules
   # ############################
   Det[NUM=sg] -> 'this' | 'every'
   Det[NUM=pl] -> 'these' | 'all'
   Det -> 'the' | 'some'
   PropN[NUM=sg]-> 'Kim' | 'Jody'
   N[NUM=sg] -> 'dog' | 'girl' | 'car' | 'child'
   N[NUM=pl] -> 'dogs' | 'girls' | 'cars' | 'children' 
   IV[TENSE=pres,  NUM=sg] -> 'disappears' | 'walks'
   TV[TENSE=pres, NUM=sg] -> 'sees' | 'likes'
   IV[TENSE=pres,  NUM=pl] -> 'disappear' | 'walk'
   TV[TENSE=pres, NUM=pl] -> 'see' | 'like'
   IV[TENSE=past, NUM=?n] -> 'disappeared' | 'walked'
   TV[TENSE=past, NUM=?n] -> 'saw' | 'liked'

|nopar| Notice that a syntactic category can have more than one feature; for example,
``V``\ [`tense`:feat:\ =\ `pres`:fval:, `num`:feat:\ =\ `pl`:fval:\ ].
In general, we can add as many features as we like.

Notice also that we have used feature variables in lexical entries as well
as grammatical productions. For example, `the`:lx: has been assigned the
category ``Det``\ [`num`:feat:\ =\ `?n`:math:]. Why is this?  Well,
you know that the definite article `the`:lx: can combine with both
singular and plural nouns. One way of describing this would be to add
two lexical entries to the grammar, one each for the singular and
plural versions of `the`:lx:. However, a more elegant solution is to
leave the `num`:feat: value `underspecified`:dt: and letting it agree
in number with whatever noun it combines with.

A final detail about Example code-feat0cfg_ is the statement ``%start S``.
This a "directive" that tells the parser to take ``S`` as the
start symbol for the grammar.

In general, when we are trying to develop even a very small grammar,
it is convenient to put the productions in a file where they can be edited,
tested and revised.  We have saved Example code-feat0cfg_ as a file named
``'feat0.fcfg'`` in the NLTK data distribution, and it
can be accessed using ``nltk.data.load()``.

.. TODO: why two print statements here, print vs pprint?
.. TODO: first mention of earley in this chapter

|nopar| We can inspect the productions and the lexicon using the commands ``print
g.earley_grammar()`` and  ``pprint(g.earley_lexicon())``.

Next, we can tokenize a sentence and use the ``nbest_parse()`` function to
invoke the Earley chart parser.

.. pylisting:: code-featurecharttrace
   :caption: Trace of Feature-Based Chart Parser

    >>> tokens = 'Kim likes children'.split()
    >>> from nltk.parse import load_parser
    >>> cp = load_parser('grammars/book_grammars/feat0.fcfg', trace=2)
    >>> trees = cp.nbest_parse(tokens)
              |.K.l.c.|
    Processing queue 0
    Predictor |> . . .| [0:0] S[] -> * NP[NUM=?n] VP[NUM=?n] {}
    Predictor |> . . .| [0:0] NP[NUM=?n] -> * N[NUM=?n] {}
    Predictor |> . . .| [0:0] NP[NUM=?n] -> * PropN[NUM=?n] {}
    Predictor |> . . .| [0:0] NP[NUM=?n] -> * Det[NUM=?n] N[NUM=?n] {}
    Predictor |> . . .| [0:0] NP[NUM='pl'] -> * N[NUM='pl'] {}
    Scanner   |[-] . .| [0:1] 'Kim'
    Scanner   |[-] . .| [0:1] PropN[NUM='sg'] -> 'Kim' *
    Processing queue 1
    Completer |[-] . .| [0:1] NP[NUM='sg'] -> PropN[NUM='sg'] *
    Completer |[-> . .| [0:1] S[] -> NP[NUM=?n] * VP[NUM=?n] {?n: 'sg'}
    Predictor |. > . .| [1:1] VP[NUM=?n, TENSE=?t] -> * IV[NUM=?n, TENSE=?t] {}
    Predictor |. > . .| [1:1] VP[NUM=?n, TENSE=?t] -> * TV[NUM=?n, TENSE=?t] NP[] {}
    Scanner   |. [-] .| [1:2] 'likes'
    Scanner   |. [-] .| [1:2] TV[NUM='sg', TENSE='pres'] -> 'likes' *
    Processing queue 2
    Completer |. [-> .| [1:2] VP[NUM=?n, TENSE=?t] -> TV[NUM=?n, TENSE=?t] * NP[] {?n: 'sg', ?t: 'pres'}
    Predictor |. . > .| [2:2] NP[NUM=?n] -> * N[NUM=?n] {}
    Predictor |. . > .| [2:2] NP[NUM=?n] -> * PropN[NUM=?n] {}
    Predictor |. . > .| [2:2] NP[NUM=?n] -> * Det[NUM=?n] N[NUM=?n] {}
    Predictor |. . > .| [2:2] NP[NUM='pl'] -> * N[NUM='pl'] {}
    Scanner   |. . [-]| [2:3] 'children'
    Scanner   |. . [-]| [2:3] N[NUM='pl'] -> 'children' *
    Processing queue 3
    Completer |. . [-]| [2:3] NP[NUM='pl'] -> N[NUM='pl'] *
    Completer |. [---]| [1:3] VP[NUM='sg', TENSE='pres'] -> TV[NUM='sg', TENSE='pres'] NP[] *
    Completer |[=====]| [0:3] S[] -> NP[NUM='sg'] VP[NUM='sg'] *
    Completer |[=====]| [0:3] [INIT][] -> S[] *

.. TODO: discussion of underspecified productions, compilation etc presumes specialized CL knowledge.
   Do we need to make this point?  Its just an implementation detail.

|nopar| Observe that the parser works directly with
the underspecified productions given by the grammar. That is, the
Predictor rule does not attempt to compile out all admissible feature
combinations before trying to expand the non-terminals on the left hand
side of a production. However, when the Scanner matches an input word
against a lexical production that has been predicted, the new edge will
typically contain fully specified features; e.g., the edge
[PropN[`num`:feat: = `sg`:fval:] |rarr| 'Kim', (0, 1)]. Recall from
Chapter chap-parse_ that the Fundamental (or Completer) Rule in
standard CFGs is used to combine an incomplete edge that's expecting a
nonterminal *B* with a following, complete edge whose left hand side
matches *B*. In our current setting, rather than checking for a
complete match, we test whether the expected category *B* will
`unify`:dt: with the left hand side *B'* of a following complete
edge. We will explain in more detail in Section sec-feat-comp_ how
unification works; for the moment, it is enough to know that as a
result of unification, any variable values of features in *B* will be
instantiated by constant values in the corresponding feature structure
in *B'*, and these instantiated values will be used in the new edge
added by the Completer. This instantiation can be seen, for example,
in the edge 
[``NP``\ [`num`:feat:\ =\ `sg`:fval:] |rarr| PropN[`num`:feat:\ =\ `sg`:fval:] |dot|, (0, 1)]
in code-featurecharttrace_,
where the feature `num`:feat: has been assigned the value `sg`:fval:.

Finally, we can inspect the resulting parse trees (in this case, a
single one).

.. doctest-ignore::
    >>> for tree in trees: print tree
    (S[]
      (NP[NUM='sg'] (PropN[NUM='sg'] Kim))
      (VP[NUM='sg', TENSE='pres']
        (TV[NUM='sg', TENSE='pres'] likes)
        (NP[NUM='pl'] (N[NUM='pl'] children))))

.. TODO: delete the [INIT] and Start non terminals from the tree display!

Terminology
-----------

So far, we have only seen feature values like `sg`:fval: and
`pl`:fval:. These simple values are usually called `atomic`:dt:
|mdash| that is, they can't be decomposed into subparts. A special
case of atomic values are `boolean`:dt: values, that is, values that
just specify whether a property is true or false of a category. For
example, we might want to distinguish `auxiliary`:dt: verbs such as
`can`:lx:, `may`:lx:, `will`:lx: and `do`:lx: with the boolean feature
`aux`:feat:. Then our lexicon for verbs could include entries such as
ex-lex_. (Note that we follow the convention that boolean
features are not written `f`:feat: +, `f`:feat: `-`:math: but simply
`+f`:feat:, `-f`:feat:, respectively.)

.. _ex-lex:
.. ex::
      .. parsed-literal::

        ``V``\ [`tense`:feat:\ =\ `pres`:fval:, `+aux`:feat:\ =\ `+`:math:\ ] |rarr| 'can'
        ``V``\ [`tense`:feat:\ =\ `pres`:fval:, `+aux`:feat:\ =\ `+`:math:\ ] |rarr| 'may'

        ``V``\ [`tense`:feat:\ =\ `pres`:fval:, `-aux`:feat: `-`:math:\ ] |rarr| 'walks'
        ``V``\ [`tense`:feat:\ =\ `pres`:fval:, `-aux`:feat: `-`:math:\ ] |rarr| 'likes'

We have spoken informally of attaching "feature annotations" to
syntactic categories. A more general
approach is to treat the whole category |mdash| that is, the
non-terminal symbol plus the annotation |mdash| as a bundle of
features. Consider, for example, the object we have written as ex-ncat0_.

.. _ex-ncat0:
.. ex::
      .. parsed-literal::

        ``N``\ [`num`:feat:\ =\ `sg`:fval:\ ] 

|nopar| The syntactic category ``N``, as we have seen before, provides part
of speech information. This information can itself be captured as a
feature value pair, using  `pos`:feat: to represent "part of speech":

.. _ex-ncat1:
.. ex::
      .. parsed-literal::

        [`pos`:feat:\ =\ `N`:fval:, `num`:feat:\ =\ `sg`:fval:\ ] 

|nopar| In fact, we  regard ex-ncat1_ as our "official" representation of a
feature-based linguistic category, and ex-ncat0_ as a convenient abbreviation.
A bundle of feature-value pairs is called a `feature structure`:dt:
or an `attribute value matrix`:dt: (AVM). A feature structure that
contains a specification for the feature `pos`:feat: is a `linguistic
category`:dt:. 

In addition to atomic-valued features, we allow features whose values
are themselves feature structures. For example, we might want to group
together agreement features (e.g., person, number and gender) as a
distinguished part of a category, as shown in ex-agr0_.

.. _ex-agr0:
.. ex::
      .. avm:: 
        [pos = N           ]
        [                  ]
        [agr = [per = 3   ]]
        [      [num = pl  ]]
        [      [gnd = fem ]]


*AVM as included figure:*

.. _fig-avm1:
.. image:: ../images/avm1.png
   :scale: 60


|nopar| In this case, we say that the feature `agr`:feat: has a `complex`:dt: value.

There is no particular significance to the *order* of features in a
feature structure. So ex-agr0_ is equivalent to ex-agr0_.

.. _ex-agr1:
.. ex::
      .. avm::
        [agr = [num = pl  ]]
        [      [per = 3   ]]
        [      [gnd = fem ]]
        [                  ]
        [pos = N           ]

Once we have the possibility of using features like `agr`:feat:, we
can refactor a grammar like Example code-feat0cfg_ so that agreement features are
bundled together. A tiny grammar illustrating this point is shown in ex-agr2_.

.. _ex-agr2:
.. ex::
    .. parsed-literal::

      ``S`` |rarr| ``NP``\ [`agr`:feat:\ =\ `?n`:fval:\ ] ``VP``\ [`agr`:feat:\ =\ `?n`:fval:]
      ``NP``\ [`agr`:feat:\ =\ `?n`:fval:] |rarr| ``PropN``\ [`agr`:feat:\ =\ `?n`:fval:] 
      ``VP``\ [`tense`:feat:\ =\ `?t`:fval:, `agr`:feat:\ =\ `?n`:fval:] |rarr| `Cop`:gc:\ [`tense`:feat:\ =\ `?t`:fval:, `agr`:feat:\ =\ `?n`:fval:] Adj
      `Cop`:gc:\ [`tense`:feat:\ =\ `pres`:fval:,  `agr`:feat:\ =\ [`num`:feat:\ =\ `sg`:fval:, `per`:feat:\ =\ `3`:fval:]] |rarr| 'is' 
      ``PropN``\ [`agr`:feat:\ =\ [`num`:feat:\ =\ `sg`:fval:, `per`:feat:\ =\ `3`:fval:]] |rarr| 'Kim'
      ``Adj`` |rarr| 'happy'


.. _sec-feat-comp:

---------------------------------
Computing with Feature Structures
---------------------------------

In this section, we will show how feature structures can be
constructed and manipulated in Python. We will also discuss the
fundamental operation of unification, which allows us to combine the
information contained in two different feature structures.

Feature Structures in Python
----------------------------

Feature structures are declared with the
``FeatStruct()`` constructor. Atomic feature values can be strings or
integers.

    >>> fs1 = nltk.FeatStruct(TENSE='past', NUM='sg') 
    >>> print fs1
    [ NUM   = 'sg'   ]
    [ TENSE = 'past' ]

|nopar| A feature structure is actually just a kind of dictionary,
and so we access its values by indexing in the usual way.
We can use our familiar syntax to *assign* values to features:

    >>> fs1 = nltk.FeatStruct(PER=3, NUM='pl', GND='fem')
    >>> print fs1['GND']
    fem
    >>> fs1['CASE'] = 'acc'

|nopar| We can also define feature structures that have complex values, as
discussed earlier.

    >>> fs2 = nltk.FeatStruct(POS='N', AGR=fs1)
    >>> print fs2
    [       [ CASE = 'acc' ] ]
    [ AGR = [ GND  = 'fem' ] ]
    [       [ NUM  = 'pl'  ] ]
    [       [ PER  = 3     ] ]
    [                        ]
    [ POS = 'N'              ]
    >>> print fs2['AGR']
    [ CASE = 'acc' ]
    [ GND  = 'fem' ]
    [ NUM  = 'pl'  ]
    [ PER  = 3     ]
    >>> print fs2['AGR']['PER']
    3

An alternative method of specifying feature structures is to
use a bracketed string consisting of feature-value pairs in the format
``feature=value``, where values may themselves be feature structures:

    >>> nltk.FeatStruct("[POS='N', AGR=[PER=3, NUM='pl', GND='fem']]")
    [AGR=[GND='fem', NUM='pl', PER=3], POS='N']


Feature Structures as Graphs
----------------------------

Feature structures are not inherently tied to linguistic objects; they are
general purpose structures for representing knowledge. For example, we
could encode information about a person in a feature structure:

    >>> person01 = nltk.FeatStruct(name='Lee', telno='01 27 86 42 96', age=33)

.. _ex-person01:
.. ex::
      .. avm:: 

        [name = `Lee'            ]
        [telno = 01 27 86 42 96  ]
        [age = 33                ]


It is sometimes helpful to view feature structures as graphs; more
specifically, `directed acyclic graphs`:dt: (DAGs). ex-dag01_ is equivalent to
the AVM ex-person01_.

.. _ex-dag01:
.. ex::
   .. image:: ../images/dag01.png
      :scale: 40

|nopar| The feature names appear as labels on the directed arcs, and feature
values appear as labels on the nodes that are pointed to by the arcs.

Just as before, feature values can be complex:

.. _ex-dag02:
.. ex::
   .. image:: ../images/dag02.png
      :scale: 40

|nopar| When we look at such graphs, it is natural to think in terms of
paths through the graph. A `feature path`:dt: is a sequence of arcs
that can be followed from the root node. We will represent paths as
tuples. Thus, ``('address', 'street')`` is a feature path whose value
in ex-dag02_ is the string "rue Pascal".

Now let's consider a situation where Lee has a spouse named "Kim", and
Kim's address is the same as Lee's.
We might represent this as ex-dag04_.

.. _ex-dag04:
.. ex::
   .. image:: ../images/dag04.png
      :scale: 40

|nopar| However, rather than repeating the address
information in the feature structure, we can "share" the same
sub-graph between different arcs:

.. _ex-dag03:
.. ex::
   .. image:: ../images/dag03.png
      :scale: 40


|nopar| In other words, the value of the path ``('ADDRESS')`` in ex-dag03_ is
identical to the value of the path ``('SPOUSE', 'ADDRESS')``.  DAGs
such as ex-dag03_ are said to involve `structure sharing`:dt: or
`reentrancy`:dt:. When two paths have the same value, they are said to
be `equivalent`:dt:.

There are a number of notations for representing reentrancy in
matrix-style representations of feature structures. We adopt
the following convention: the first occurrence of a shared feature structure 
is prefixed with an integer in parentheses, such as ``(1)``, and any
subsequent reference to that structure uses the notation
``->(1)``, as shown below.

    >>> fs = nltk.FeatStruct("""[NAME='Lee', ADDRESS=(1)[NUMBER=74, STREET='rue Pascal'], 
    ...                         SPOUSE=[NAME='Kim', ADDRESS->(1)]]""")
    >>> print fs
    [ ADDRESS = (1) [ NUMBER = 74           ] ]
    [               [ STREET = 'rue Pascal' ] ]
    [                                         ]
    [ NAME    = 'Lee'                         ]
    [                                         ]
    [ SPOUSE  = [ ADDRESS -> (1)  ]           ]
    [           [ NAME    = 'Kim' ]           ]


|nopar| This is similar to more conventional displays of AVMs, as shown in
ex-reentrant01_.

.. _ex-reentrant01:
.. ex::
      .. avm:: 

	 [ address = (1) [ number = 74           ] ]
	 [               [ street = 'rue Pascal' ] ]
	 [                                         ]
	 [ name    = 'Lee'                         ]
	 [                                         ]
	 [ spouse  = [ address -> (1)  ]           ]
	 [           [ name    = 'Kim' ]           ]

|nopar| The bracketed integer is sometimes called a `tag`:dt: or a
`coindex`:dt:. The choice of integer is not significant.
There can be any number of tags within a single feature structure.

    >>> fs1 = nltk.FeatStruct("[A='a', B=(1)[C='c'], D->(1), E->(1)]")

.. _ex-reentrant02:
.. ex::
      .. avm::

	 [ A = 'a'             ]
	 [                     ]
	 [ B = (1) [ C = 'c' ] ]
	 [                     ]
	 [ D -> (1)            ]
	 [ E -> (1)            ]


.. TODO following AVM doesn't currently parse
..
    |nopar| We can also share empty structures:

	>>> fs2 = nltk.FeatStruct("[A=(1)[], B=(2)[], C->(1), D->(2)]")

    .. _ex-reentrant03:
    .. ex::
	  .. avm:: 

	     [ A = (1) [ ] ]
	     [ B = (2) [ ] ]
	     [ C -> (1)    ]
	     [ D -> (2)    ]



Subsumption and Unification
---------------------------

It is standard to think of feature structures as providing `partial
information`:dt: about some object, in the sense that we can order
feature structures according to how general they are. For example,
ex-fs01_ is more general (less specific) than ex-fs02_, which in turn is more general than ex-fs03_.

.. ex::
   .. _ex-fs01:
   .. ex::
      .. avm::

         [number = 74]

   .. _ex-fs02:
   .. ex::
      .. avm::

         [number = 74          ]
         [street = 'rue Pascal']

   .. _ex-fs03:
   .. ex::
      .. avm::

         [number = 74          ]
         [street = 'rue Pascal']
         [city = 'Paris'       ]

|nopar| This ordering is called `subsumption`:dt:; a more general feature
structure `subsumes`:dt: a less general one. If `FS`:math:\
:subscript:`0` subsumes `FS`:math:\ :subscript:`1` (formally, we write
`FS`:math:\ :subscript:`0` |SquareSubsetEqual| `FS`:math:\
:subscript:`1`), then `FS`:math:\ :subscript:`1` must have all the
paths and path equivalences of `FS`:math:\ :subscript:`0`, and may
have additional paths and equivalences as well. Thus, ex-dag04_ subsumes
ex-dag03_, since the latter has additional path equivalences.. It should
be obvious that subsumption only provides a partial ordering on
feature structures, since some feature structures are
incommensurable. For example, ex-fs04_ neither subsumes nor is subsumed
by ex-fs01_.


.. _ex-fs04:
.. ex::
   .. avm::

         [telno = 01 27 86 42 96]

So we have seen that some feature structures are more specific than
others. How do we go about specializing a given feature structure?
For example, we might decide that addresses should
consist of not just a street number and a street name, but also a
city. That is, we might want to *merge*  graph ex-dag042_ with ex-dag041_ to
yield ex-dag043_.

.. ex::
     .. _ex-dag041:
     .. ex::
	.. image:: ../images/dag04-1.png
	   :scale: 40

     .. _ex-dag042:
     .. ex::
	.. image:: ../images/dag04-2.png
	   :scale: 40

     .. _ex-dag043:
     .. ex::
	.. image:: ../images/dag04-3.png
	   :scale: 40

|nopar| Merging information from two feature structures is called
`unification`:dt: and is supported by the ``unify()`` method.

    >>> fs1 = nltk.FeatStruct(NUMBER=74, STREET='rue Pascal')
    >>> fs2 = nltk.FeatStruct(CITY='Paris')
    >>> print fs1.unify(fs2)
    [ CITY   = 'Paris'      ]
    [ NUMBER = 74           ]
    [ STREET = 'rue Pascal' ]

Unification is formally defined as a binary operation: `FS`:math:\
:subscript:`0` |SquareIntersection| `FS`:math:\
:subscript:`1`. Unification is symmetric, so 

.. ex::
    `FS`:math:\ :subscript:`0` |SquareIntersection| `FS`:math:\
    :subscript:`1` = `FS`:math:\ :subscript:`1` |SquareIntersection|
    `FS`:math:\ :subscript:`0`.

|nopar| The same is true in Python:

    >>> print fs2.unify(fs1)
    [ CITY   = 'Paris'      ]
    [ NUMBER = 74           ]
    [ STREET = 'rue Pascal' ]

.. TODO: also mention commutativity

.. but >>> fs1.unify(fs2) is fs2.unify(fs1)
       False
   only works with repr()

If we unify two feature structures which stand in the subsumption
relationship, then the result of unification is the most specific of
the two:

.. ex::
    If `FS`:math:\ :subscript:`0` |SquareSubsetEqual| `FS`:math:\
    :subscript:`1`,  then `FS`:math:\ :subscript:`0`
    |SquareIntersection| `FS`:math:\ :subscript:`1` = `FS`:math:\
    :subscript:`1` 

|nopar| For example, the result of unifying ex-fs02_ with ex-fs03_ is ex-fs03_.

Unification between `FS`:math:\ :subscript:`0` and `FS`:math:\
:subscript:`1` will fail if the two feature structures share a path |pi|,
but the value of |pi| in `FS`:math:\ :subscript:`0` is a distinct
atom from the value of |pi| in `FS`:math:\ :subscript:`1`.
This is implemented by setting the result of unification to be ``None``.

    >>> fs0 = nltk.FeatStruct(A='a')
    >>> fs1 = nltk.FeatStruct(A='b')
    >>> fs2 = fs0.unify(fs1)
    >>> print fs2
    None

Now, if we look at how unification interacts with structure-sharing,
things become really interesting. First, let's define ex-dag04_ in Python:

    >>> fs0 = nltk.FeatStruct("""[NAME=Lee, 
    ...                           ADDRESS=[NUMBER=74, 
    ...                                    STREET='rue Pascal'], 
    ...                           SPOUSE= [NAME=Kim,
    ...                                    ADDRESS=[NUMBER=74, 
    ...                                             STREET='rue Pascal']]]""")

.. _ex-unification01:
.. ex::
      .. avm:: 

	 [ address = [ number = 74           ]               ]
	 [           [ street = `rue Pascal' ]               ]
	 [                                                   ]
	 [ name    = `Lee'                                   ]
	 [                                                   ]
	 [           [ address = [ number = 74           ] ] ]
	 [ spouse  = [           [ street = `rue Pascal' ] ] ]
	 [           [                                     ] ]
	 [           [ name    = `Kim'                     ] ]

|nopar| What happens when we augment Kim's address with a specification
for `city`:feat:? (Notice that ``fs1`` includes the whole path from the root of
the feature structure down to `city`:feat:.)

    >>> fs1 = nltk.FeatStruct("[SPOUSE = [ADDRESS = [CITY = Paris]]]")

ex-unification02_ shows the result of unifying ``fs0`` with ``fs1``:

.. _ex-unification02:
.. ex::
      .. avm:: 

	 [ address = [ number = 74           ]               ]
	 [           [ street = `rue Pascal' ]               ]
	 [                                                   ]
	 [ name    = `Lee'                                   ]
	 [                                                   ]
	 [           [           [ city   = `Paris'      ] ] ]
	 [           [ address = [ number = 74           ] ] ]
	 [ spouse  = [           [ street = `rue Pascal' ] ] ]
	 [           [                                     ] ]
	 [           [ name    = `Kim'                     ] ]

|nopar| By contrast, the result is very different if ``fs1`` is unified with
the structure-sharing version ``fs2`` (also shown as ex-dag03_):

    >>> fs2 = nltk.FeatStruct("""[NAME=Lee, ADDRESS=(1)[NUMBER=74, STREET='rue Pascal'],
    ...                           SPOUSE=[NAME=Kim, ADDRESS->(1)]]""")

.. _ex-unification03:
.. ex::
      .. avm:: 

	 [               [ city   = `Paris'      ] ]
	 [ address = (1) [ number = 74           ] ]
	 [               [ street = `rue Pascal' ] ]
	 [                                         ]
	 [ name    = `Lee'                         ]
	 [                                         ]
	 [ spouse  = [ address -> (1)  ]           ]
	 [           [ name    = `Kim' ]           ]

|nopar| Rather than just updating what was in effect Kim's "copy" of Lee's address,
we have now updated `both`:em: their addresses at the same time. More
generally, if a unification involves specializing the value of some
path |pi|, then that unification simultaneously specializes the value
of `any path that is equivalent to`:em: |pi|.

As we have already seen, structure sharing can also be stated
using variables such as ``?x``. 

    >>> fs1 = nltk.FeatStruct("[ADDRESS1=[NUMBER=74, STREET='rue Pascal']]")
    >>> fs2 = nltk.FeatStruct("[ADDRESS1=?x, ADDRESS2=?x]")
    >>> print fs2
    [ ADDRESS1 = ?x ]
    [ ADDRESS2 = ?x ]
    >>> print fs2.unify(fs1)
    [ ADDRESS1 = (1) [ NUMBER = 74           ] ]
    [                [ STREET = 'rue Pascal' ] ]
    [                                          ]
    [ ADDRESS2 -> (1)                          ]




.. _sec-extending-a-feature-based-grammar:

---------------------------------
Extending a Feature-Based Grammar
---------------------------------

.. TODO: I think this section needs an opening

Subcategorization
-----------------

In Chapter chap-parse_, we proposed to augment our
category labels to represent different kinds of verb.
We introduced labels such as ``IV`` and ``TV`` for intransitive
and transitive verbs respectively.  This allowed us to write productions
like the following:

.. _ex-subcatcfg0:
.. ex::
   .. parsed-literal::

      ``VP`` |rarr| ``IV`` 
      ``VP`` |rarr| `tv np`:gc: 

|nopar| Although we know that ``IV`` and ``TV`` are two
kinds of ``V``, from a formal point of view
``IV`` has no closer relationship with ``TV`` than it does
with ``NP``. As it stands, ``IV`` and ``TV`` are just atomic
nonterminal symbols from a CFG.  This approach doesn't allow us
to say anything about the class of verbs in general.
For example, we cannot say something like "All lexical
items of category ``V`` can be marked for tense", since `bark`:lx:,
say, is an item of category ``IV``, not ``V``.
A simple solution, originally developed for a grammar framework
called Generalized Phrase Structure Grammar (GPSG), stipulates that lexical
categories may bear a `subcat`:feat: feature whose values are integers.
This is illustrated in a modified portion of Example code-feat0cfg_, shown in ex-subcatgpsg_.

.. _ex-subcatgpsg:
.. ex::
   ::

     VP[TENSE=?t, NUM=?n] -> V[SUBCAT=0, TENSE=?t, NUM=?n]
     VP[TENSE=?t, NUM=?n] -> V[SUBCAT=1, TENSE=?t, NUM=?n] NP
     VP[TENSE=?t, NUM=?n] -> V[SUBCAT=2, TENSE=?t, NUM=?n] Sbar

     V[SUBCAT=0, TENSE=pres, NUM=sg] -> 'disappears' | 'walks'
     V[SUBCAT=1, TENSE=pres, NUM=sg] -> 'sees' | 'likes'
     V[SUBCAT=2, TENSE=pres, NUM=sg] -> 'says' | 'claims'

     V[SUBCAT=0, TENSE=pres, NUM=pl] -> 'disappear' | 'walk'
     V[SUBCAT=1, TENSE=pres, NUM=pl] -> 'see' | 'like'
     V[SUBCAT=2, TENSE=pres, NUM=pl] -> 'say' | 'claim'

     V[SUBCAT=0, TENSE=past, NUM=?n] -> 'disappeared' | 'walked'
     V[SUBCAT=1, TENSE=past, NUM=?n] -> 'saw' | 'liked'
     V[SUBCAT=2, TENSE=past, NUM=?n] -> 'said' | 'claimed'

|nopar| When we see a lexical category like ``V``\ [`subcat`:feat: 
`1`:fval:\ ], we can interpret the `subcat`:feat: specification as a
pointer to the production in which ``V``\ [`subcat`:feat: `1`:fval:\ ]
is introduced as the head daughter in a ``VP`` production.
By convention, there is a one-to-one correspondence between
`subcat`:feat: values and the productions that introduce lexical heads.
It's worth noting that the choice of integer which acts as a value for
`subcat`:feat: is completely arbitrary |mdash| we could equally well
have chosen 3999, 113 and 57 as our two values in ex-subcatgpsg_.  On this
approach, `subcat`:feat: can *only* appear on lexical categories; it
makes no sense, for example, to specify a `subcat`:feat: value on
``VP``.

In our third class of verbs above, we have specified a category
``S-BAR``. This is a label for subordinate clauses such as the
complement of `claim`:lx: in the example `You claim that you like
children`:lx:. We require two further productions to analyze such sentences:

.. _ex-sbar:
.. ex::
   ::

     S-BAR -> Comp S
     Comp -> 'that'

|nopar| The resulting structure is the following.

.. _ex-sbartree:
.. ex::
      .. tree::  (S (NP you)(VP (V[-AUX,\ SUBCAT\ 2] claim)(S-BAR (Comp that) (S (NP you)(VP (V[-AUX,\ SUBCAT\ 1] like)(NP children))))))

An alternative treatment of subcategorization, due originally to a framework
known as categorial grammar, is represented in feature-based frameworks such as PATR
and Head-driven Phrase Structure Grammar. Rather than using
`subcat`:feat: values as a way of indexing productions, the `subcat`:feat:
value directly encodes the valency of a head (the list of
arguments that it can combine with). For example, a verb like
`put`:lx: that takes  ``NP`` and ``PP`` complements (`put the
book on the table`:lx:) might be represented as ex-subcathpsg0_:

.. TODO: angle brackets don't appear

.. _ex-subcathpsg0:
.. ex::  ``V``\ [`subcat`:feat: |langle|\ ``NP``, ``NP``, ``PP``\ |rangle| ] 

|nopar| This says that the verb can combine with three  arguments. The
leftmost element in the list is the subject ``NP``, while everything
else |mdash| an ``NP`` followed by a ``PP`` in this case |mdash| comprises the
subcategorized-for complements. When a verb like `put`:lx: is combined
with appropriate complements, the requirements which are specified in
the  `subcat`:feat: are discharged, and only a subject ``NP`` is
needed. This category, which corresponds to what is traditionally
thought of as ``VP``, might be represented as follows.

.. _ex-subcathpsg1:
.. ex::  ``V``\ [`subcat`:feat: |langle|\ ``NP``\ |rangle| ] 

Finally, a sentence is a kind of verbal category that has *no*
requirements for further arguments, and hence has a `subcat`:feat:
whose value is the empty list. The tree ex-subcathpsg2_ shows how these
category assignments combine in a parse of `Kim put the book on the table`:lx:.

.. _ex-subcathpsg2:
.. ex::
      .. tree:: (V[SUBCAT\ \<\>] (NP Kim)(V[SUBCAT\ \<NP\>](V[SUBCAT\ \<NP,\ NP,\ VP\>] put)<NP the\ book><PP on\ the\ table>))

Heads Revisited
---------------

We noted in the previous section that by factoring subcategorization
information out of the main category label, we could express more
generalizations about properties of verbs. Another property of this
kind is the following: expressions of category ``V`` are heads of
phrases of category ``VP``. Similarly (and more informally) ``N``\
s are heads of ``NP``\ s,  ``A``\
s (i.e., adjectives) are heads of ``AP``\ s,  and ``P``\
s (i.e., adjectives) are heads of ``PP``\ s. Not all phrases have
heads |mdash| for example, it is standard to say that coordinate
phrases (e.g., `the book and the bell`:lx:) lack heads |mdash|
nevertheless, we would like our grammar formalism to express the
mother / head-daughter
relation where it holds. Now, although it looks as though there is
something in common  between, say, ``V`` and ``VP``, this is more
of a handy convention than a real claim, since  ``V`` and ``VP``
formally have no more in common than ``V`` and ``Det``. 

X-bar syntax (cf. [Chomsky1970RN]_, [Jackendoff1977XS]_) addresses
this issue by abstracting out the notion of `phrasal level`:dt:. It is
usual to recognize three such levels. If ``N`` represents the
lexical level, then ``N``\ ' represents the next level up,
corresponding to the more traditional category ``Nom``, while
``N``\ '' represents the phrasal level, corresponding to the
category ``NP``. (The primes here replace the typographically more
demanding horizontal bars of [Chomsky1970RN]_). ex-xbar0_ illustrates a
representative structure.

.. _ex-xbar0:
.. ex::
   .. tree:: (N''(Det a)(N'(N student)(P'' of\ French)))

|nopar| The head of the structure ex-xbar0_ is ``N`` while ``N``\ '
and ``N``\ '' are called `(phrasal) projections`:dt: of ``N``. ``N``\ ''
is the `maximal projection`:dt:, and ``N`` is sometimes called the
`zero projection`:dt:. One of the central claims of X-bar syntax is
that all constituents share a structural similarity. Using ``X`` as
a variable over ``N``, ``V``, ``A`` and ``P``, we say that
directly subcategorized `complements`:em: of the head are always
placed as sisters of the lexical head, whereas `adjuncts`:em: are
placed as sisters of the intermediate category, ``X``\ '. Thus, the
configuration of the ``P``\ '' adjunct in ex-xbar1_ contrasts with that
of the complement ``P``\ '' in ex-xbar0_.

.. _ex-xbar1:
.. ex::
   .. tree:: (N''(Det a)(N'(N'(N student))(P'' from\ france)))

The productions in ex-xbar2_ illustrate how bar levels can be encoded
using feature structures.

.. _ex-xbar2:
.. ex::
   .. parsed-literal::

     ``S`` |rarr| ``N``\ [`bar`:feat:\ =\ `2`:fval:] ``V``\ [`bar`:feat:\ =\ `2`:fval:]
     ``N``\ [`bar`:feat:\ =\ `2`:fval:] |rarr| `Det n`:gc:\ [`bar`:feat:\ =\ `1`:fval:]
     ``N``\ [`bar`:feat:\ =\ `1`:fval:] |rarr| ``N``\ [`bar`:feat:\ =\ `1`:fval:] ``P``\ [`bar`:feat:\ =\ `2`:fval:] 
     ``N``\ [`bar`:feat:\ =\ `1`:fval:] |rarr| ``N``\ [`bar`:feat:\ =\ `0`:fval:] ``P``\ [`bar`:feat:\ =\ `2`:fval:] 


Auxiliary Verbs and Inversion
-----------------------------

Inverted clauses |mdash| where the order of subject and verb is
switched |mdash| occur in English interrogatives and also after
'negative' adverbs:

.. _ex-inv1:
.. ex::
   .. _ex-inv1a:
   .. ex::

      Do you like children?

   .. _ex-inv1b:
   .. ex::

      Can Jody walk?

.. _ex-inv2:
.. ex::
   .. _ex-inv2a:
   .. ex::

      Rarely do you see Kim.

   .. _ex-inv2b:
   .. ex::

      Never have I seen this dog.

|nopar| However, we cannot place just any verb in pre-subject position:

.. _ex-inv3:
.. ex::
   .. _ex-inv3a:
   .. ex::

      \*Like you children?

   .. _ex-inv3b:
   .. ex::

      \*Walks Jody?

.. _ex-inv4:
.. ex::
   .. _ex-inv4a:
   .. ex::

      \*Rarely see you Kim.

   .. _ex-inv4b:
   .. ex::

      \*Never saw I this dog.

Verbs that can be positioned initially in inverted clauses belong to
the class known as `auxiliaries`:dt:, and as well as  `do`:lx:,
`can`:lx: and `have`:lx:  include `be`:lx:, `will`:lx:  and
`shall`:lx:. One way of capturing such structures is with the
following production:

.. _ex-sinv:
.. ex::
   ::

     S[+inv] -> V[+AUX] NP VP

|nopar| That is, a clause marked as [`+inv`:feat:] consists of an auxiliary
verb followed by a ``VP``. (In a more detailed grammar, we would
need to place some constraints on the form of the ``VP``, depending
on the choice of auxiliary.) ex-invtree_ illustrates the structure of an
inverted clause.

.. _ex-invtree:
.. ex::
      .. tree:: (S[+INV](V[+AUX,\ SUBCAT=3] do)(NP you)(VP(V[-AUX,\ SUBCAT=1] like)(NP children)))



Unbounded Dependency Constructions
----------------------------------

Consider the following contrasts: 

.. _ex-gap1:
.. ex::
   .. _ex-gap1a:
   .. ex::

      You like Jody.

   .. _ex-gap1b:
   .. ex::

      \*You like.

.. _ex-gap2:
.. ex::
   .. _ex-gap2a:
   .. ex::

      You put the card into the slot.

   .. _ex-gap2b:
   .. ex::

      \*You put into the slot.

   .. _ex-gap2c:
   .. ex::

      \*You put the card.

   .. _ex-gap2d:
   .. ex::

      \*You put.

The verb `like`:lx: requires an ``NP`` complement, while
`put`:lx: requires both a following ``NP`` and ``PP``. Examples
ex-gap1_ and ex-gap2_ show that these complements are *obligatory*:
omitting them leads to ungrammaticality. Yet there are contexts in
which obligatory complements can be omitted, as ex-gap3_ and ex-gap4_
illustrate.

.. _ex-gap3:
.. ex::
   .. _ex-gap3a:
   .. ex::

      Kim knows who you like.

   .. _ex-gap3b:
   .. ex::

      This music, you really like.

.. _ex-gap4:
.. ex::
   .. _ex-gap4a:
   .. ex::

      Which card do you put into the slot?

   .. _ex-gap4b:
   .. ex::

      Which slot do you put the card into?

|nopar| That is, an obligatory complement can be omitted if there is an
appropriate `filler`:dt: in the sentence, such as the question word
`who`:lx: in ex-gap3a_, the preposed topic `this music`:lx: in ex-gap3b_, or
the `wh`:lx: phrases `which card/slot`:lx: in ex-gap4_. It is common to
say that sentences like ex-gap3_ |ndash| ex-gap4_ contain `gaps`:dt: where
the obligatory complements have been omitted, and these gaps are
sometimes made explicit using an underscore:

.. _ex-gap5:
.. ex::
   .. _ex-gap5a:
   .. ex::

      Which card do you put __ into the slot?

   .. _ex-gap5b:
   .. ex::

      Which slot do you put the card into __?

|nopar| So, a gap can occur if it is `licensed`:dt: by a filler. Conversely,
fillers can only occur if there is an appropriate gap elsewhere  in
the sentence, as shown by the following examples.

.. _ex-gap6:
.. ex::
   .. _ex-gap6a:
   .. ex::

      \*Kim knows who you like Jody.

   .. _ex-gap6b:
   .. ex::

      \*This music, you really like hip-hop.

.. _ex-gap7:
.. ex::
   .. _ex-gap7a:
   .. ex::

      \*Which card do you put this into the slot?

   .. _ex-gap7b:
   .. ex::

      \*Which slot do you put the card into this one?

The mutual co-occurence between filler and gap leads to ex-gap3_ |ndash|
ex-gap4_ is sometimes termed a "dependency". One issue of considerable
importance in theoretical linguistics has been the nature of the
material that can intervene between a filler and the gap that it
licenses; in particular, can we simply list a finite set of strings
that separate the two? The answer is No: there is no upper bound on
the distance between filler and gap. This fact can be easily
illustrated with constructions involving sentential complements, as
shown in ex-gap8_. 

.. _ex-gap8:
.. ex::
   .. _ex-gap8a:
   .. ex::

      Who do you like __?

   .. _ex-gap8b:
   .. ex::

      Who do you claim that you like __?

   .. _ex-gap8c:
   .. ex::

      Who do you claim that Jody says that you like __?

|nopar| Since we can have indefinitely deep recursion of sentential
complements, the gap can be embedded indefinitely far inside the whole
sentence. This constellation of properties leads to the notion of an
`unbounded dependency construction`:dt:; that is, a filler-gap
dependency where there is no upper bound on the distance between
filler and gap.

A variety of mechanisms have been suggested for handling unbounded
dependencies in formal grammars; we shall adopt an approach due to
Generalized Phrase Structure Grammar that involves something called
`slash categories`:dt:. A slash category is something of the form
`y/xp`:gc:; we interpret this as a phrase of category ``Y`` that
is missing a sub-constituent of category ``XP``. For example,
`s/np`:gc: is an ``S`` that is missing an ``NP``. The use of
slash categories is illustrated in ex-gaptree1_. 

.. _ex-gaptree1:
.. ex::
      .. tree:: (S(NP[+WH] who)(S[+INV]\/NP (V[+AUX,\ SUBCAT=3] do)(NP[-WH] you)(VP/NP(V[-AUX,\ SUBCAT=1] like)(NP/NP e))))

|nopar| The top part of the tree introduces the filler `who`:lx: (treated as
an expression of category ``NP``\ [`+wh`:feat:]) together with a
corresponding gap-containing constituent `s/np`:gc:. The gap information is
then "percolated" down the tree via the `vp/np`:gc: category, until it
reaches the category ``NP/NP``. At this point, the dependency 
is discharged by realizing the gap information as the empty string `e`
immediately dominated by ``NP/NP``.

Do we need to think of slash categories as a completely new kind of
object in our grammars?  Fortunately, no, we don't |mdash| in fact, we
can accommodate them within our existing feature-based framework. We
do this by treating slash as a feature, and the category to its right
as a value. In other words, our "official" notation for `s/np`:gc:
will be ``S``\ [`slash`:feat:\ =\ `NP`:fval:\ ]. Once we have taken this
step, it is straightforward to write a small grammar for
analyzing unbounded dependency constructions.  Example code-slashcfg_ illustrates
the main principles of slash categories, and also includes productions for
inverted clauses. To simplify presentation, we have omitted any
specification of tense on the verbs.


.. pylisting:: code-slashcfg
   :caption: Grammar for Simple Long-distance Dependencies

   >>> nltk.data.show_cfg('grammars/book_grammars/feat1.fcfg')
   % start S
   # ############################
   # Grammar Rules
   # ############################
   S[-INV] -> NP  S/NP
   S[-INV]/?x -> NP VP/?x
   S[+INV]/?x -> V[+AUX] NP VP/?x
   S-BAR/?x -> Comp S[-INV]/?x
   NP/NP ->
   VP/?x -> V[SUBCAT=1, -AUX] NP/?x
   VP/?x -> V[SUBCAT=2, -AUX] S-BAR/?x
   VP/?x -> V[SUBCAT=3, +AUX] VP/?x
   # ############################
   # Lexical Rules
   # ############################
   V[SUBCAT=1, -AUX] -> 'see' | 'like'
   V[SUBCAT=2, -AUX] -> 'say' | 'claim'
   V[SUBCAT=3, +AUX] -> 'do' | 'can'
   NP[-WH] -> 'you' | 'children' | 'girls'
   NP[+WH] -> 'who'
   Comp -> 'that'

The grammar in Example code-slashcfg_ contains one gap-introduction production, namely

.. ex::
   .. parsed-literal::

      `s[-inv]`:gc: |rarr| ``NP`` `s/np`:gc: 

In order to percolate the slash feature correctly, we need to add
slashes with variable values to both sides of the arrow in productions
that expand ``S``, ``VP`` and ``NP``. For example,

.. ex::
   .. parsed-literal::

      `vp/?x`:gc: |rarr| ``V`` `s-bar/?x`:gc: 

|nopar| says that a slash value can be specified on the ``VP`` mother of a
constituent if the same value is also specified on the ``S-BAR``
daughter. Finally, empty_ allows the slash information on ``NP`` to
be discharged as the empty string.

..  _empty:
.. ex::
   .. parsed-literal::

      ``NP/NP`` |rarr|

Using code-slashcfg_, we can parse the string `who do you claim that you
like`:lx:  into the tree shown in ex-gapparse_.

.. _ex-gapparse:
.. ex::
    .. tree:: (S[-INV](NP[+WH] who)(S[SLASH=NP,+INV](V[+AUX,SUBCAT=3] do)(NP[-WH] you)(VP[SLASH=NP](V[-AUX,SUBCAT=2] claim)(S-BAR[SLASH=NP](Comp that)(S[SLASH=NP,-INV](NP[-WH] you)(VP[SLASH=NP](V[-AUX,SUBCAT=1] like)(NP[SLASH=NP] )))))))


Case and Gender in German
-------------------------

Compared with English, German has a relatively rich morphology for
agreement. For example, the definite article in German varies with
case, gender and number, as shown in Table tab-german-def-art_.

.. table:: tab-german-def-art

    +-----------+-----------+-----------+-----------+------------+
    | **Case**  | **Masc**  | **Fem**   |  **Neut** | **Plural** |
    +-----------+-----------+-----------+-----------+------------+
    |  *Nom*    |  der      |  die      |   das     |   die      |
    +-----------+-----------+-----------+-----------+------------+
    |  *Gen*    |  des      |  der      |   des     |   der      |
    +-----------+-----------+-----------+-----------+------------+
    |  *Dat*    |  dem      |  der      |   dem     |   den      |
    +-----------+-----------+-----------+-----------+------------+
    |  *Acc*    |  den      |  die      |   das     |   die      |
    +-----------+-----------+-----------+-----------+------------+

    Morphological Paradigm for the German definite Article

|nopar| Subjects in German take the nominative case, and most verbs
govern their objects in the accusative case. However, there are
exceptions like `helfen`:lx: that govern the dative case:

.. ex::

   .. gloss::
         Die                          | Katze                  | sieht            | den                          | Hund            
         the.NOM.FEM.SG               | cat.3.FEM.SG           | see.3.SG         | the.ACC.MASC.SG              | dog.3.MASC.SG   
         'the cat sees the dog'

   .. gloss::
         \*Die                        | Katze                  | sieht            |  dem                         | Hund
         the.NOM.FEM.SG               | cat.3.FEM.SG           | see.3.SG         |  the.DAT.MASC.SG             | dog.3.MASC.SG

   .. gloss::
         Die                         | Katze                  | hilft             | dem                          | Hund            
         the.NOM.FEM.SG              | cat.3.FEM.SG           | help.3.SG         | the.DAT.MASC.SG              | dog.3.MASC.SG   
         'the cat helps the dog'

   .. gloss::
         \*Die                       | Katze                  | hilft             | den                          | Hund
         the.NOM.FEM.SG              | cat.3.FEM.SG           | help.3.SG         | the.ACC.MASC.SG              | dog.3.MASC.SG


The grammar in Example code-germancfg_ illustrates the interaction of agreement
(comprising person, number and gender) with case. 

.. pylisting:: code-germancfg
   :caption: Example Feature-Based Grammar

   >>> nltk.data.show_cfg('grammars/book_grammars/german.fcfg')
   % start S
   # Grammar Rules
   S -> NP[CASE=nom, AGR=?a] VP[AGR=?a]
   NP[CASE=?c, AGR=?a] -> PRO[CASE=?c, AGR=?a]
   NP[CASE=?c, AGR=?a] -> Det[CASE=?c, AGR=?a] N[CASE=?c, AGR=?a]
   VP[AGR=?a] -> IV[AGR=?a]
   VP[AGR=?a] -> TV[OBJCASE=?c, AGR=?a] NP[CASE=?c]
   # Lexical Rules
   # Singular determiners
   # masc
   Det[CASE=nom, AGR=[GND=masc,PER=3,NUM=sg]] -> 'der' 
   Det[CASE=dat, AGR=[GND=masc,PER=3,NUM=sg]] -> 'dem'
   Det[CASE=acc, AGR=[GND=masc,PER=3,NUM=sg]] -> 'den'
   # fem
   Det[CASE=nom, AGR=[GND=fem,PER=3,NUM=sg]] -> 'die' 
   Det[CASE=dat, AGR=[GND=fem,PER=3,NUM=sg]] -> 'der'
   Det[CASE=acc, AGR=[GND=fem,PER=3,NUM=sg]] -> 'die' 
   # Plural determiners
   Det[CASE=nom, AGR=[PER=3,NUM=pl]] -> 'die' 
   Det[CASE=dat, AGR=[PER=3,NUM=pl]] -> 'den' 
   Det[CASE=acc, AGR=[PER=3,NUM=pl]] -> 'die' 
   # Nouns
   N[AGR=[GND=masc,PER=3,NUM=sg]] -> 'hund'
   N[CASE=nom, AGR=[GND=masc,PER=3,NUM=pl]] -> 'hunde'
   N[CASE=dat, AGR=[GND=masc,PER=3,NUM=pl]] -> 'hunden'
   N[CASE=acc, AGR=[GND=masc,PER=3,NUM=pl]] -> 'hunde'
   N[AGR=[GND=fem,PER=3,NUM=sg]] -> 'katze'
   N[AGR=[GND=fem,PER=3,NUM=pl]] -> 'katzen'
   # Pronouns
   PRO[CASE=nom, AGR=[PER=1,NUM=sg]] -> 'ich'
   PRO[CASE=acc, AGR=[PER=1,NUM=sg]] -> 'mich'
   PRO[CASE=dat, AGR=[PER=1,NUM=sg]] -> 'mir'
   PRO[CASE=nom, AGR=[PER=2,NUM=sg]] -> 'du'
   PRO[CASE=nom, AGR=[PER=3,NUM=sg]] -> 'er' | 'sie' | 'es'
   PRO[CASE=nom, AGR=[PER=1,NUM=pl]] -> 'wir'
   PRO[CASE=acc, AGR=[PER=1,NUM=pl]] -> 'uns'
   PRO[CASE=dat, AGR=[PER=1,NUM=pl]] -> 'uns'
   PRO[CASE=nom, AGR=[PER=2,NUM=pl]] -> 'ihr'
   PRO[CASE=nom, AGR=[PER=3,NUM=pl]] -> 'sie'
   # Verbs
   IV[AGR=[NUM=sg,PER=1]] -> 'komme'
   IV[AGR=[NUM=sg,PER=2]] -> 'kommst'
   IV[AGR=[NUM=sg,PER=3]] -> 'kommt'
   IV[AGR=[NUM=pl, PER=1]] -> 'kommen'
   IV[AGR=[NUM=pl, PER=2]] -> 'kommt'
   IV[AGR=[NUM=pl, PER=3]] -> 'kommen'
   TV[OBJCASE=acc, AGR=[NUM=sg,PER=1]] -> 'sehe' | 'mag'
   TV[OBJCASE=acc, AGR=[NUM=sg,PER=2]] -> 'siehst' | 'magst'
   TV[OBJCASE=acc, AGR=[NUM=sg,PER=3]] -> 'sieht' | 'mag'
   TV[OBJCASE=dat, AGR=[NUM=sg,PER=1]] -> 'folge' | 'helfe'
   TV[OBJCASE=dat, AGR=[NUM=sg,PER=2]] -> 'folgst' | 'hilfst'
   TV[OBJCASE=dat, AGR=[NUM=sg,PER=3]] -> 'folgt' | 'hilft'

|nopar| As you will see, the feature `objcase`:feat: is used to
specify the case that the verb governs on its object.


-------
Summary
-------

* The traditional categories of context-free grammar are atomic
  symbols. An important motivation for feature structures is to capture
  fine-grained distinctions that would otherwise require a massive
  multiplication of atomic categories.

* By using variables over feature values, we can express constraints
  in grammar productions that allow the realization of different feature
  specifications to be inter-dependent.

* Typically we specify fixed values of features at the lexical level
  and constrain the values of features in phrases to unify with the
  corresponding values in their daughters. 

* Feature values are either atomic or complex. A particular sub-case of
  atomic value is the Boolean value, represented by convention as [+/-
  `f`:feat:]. 

* Two features can share a value (either atomic or
  complex). Structures with shared values are said to be
  re-entrant. Shared values are represented by numerical indexes (or
  tags) in AVMs.

* A path in a feature structure is a tuple of features
  corresponding to the labels on  a sequence of arcs from the root of the graph
  representation.

* Two paths are equivalent if they share a value.

* Feature structures are partially ordered by subsumption.
  `FS`:math:\ :subscript:`0` subsumes `FS`:math:\ :subscript:`1` when
  `FS`:math:\ :subscript:`0` is more general (less informative) than
  `FS`:math:\ :subscript:`1`. 

* The unification of two structures `FS`:math:\ :subscript:`0` and
  `FS`:math:\ :subscript:`1`, if successful, is the feature
  structure `FS`:math:\ :subscript:`2` that contains the combined
  information of both `FS`:math:\ :subscript:`0` and `FS`:math:\
  :subscript:`1`.

* If unification specializes a path |pi| in `FS`:math:, then it also
  specializes every path |pi|\ ' equivalent to |pi|.

* We can use feature structures to build succinct analyses of a wide
  variety of linguistic phenomena, including verb subcategorization,
  inversion constructions, unbounded dependency constructions and case government.

-----------------
 Further Reading
-----------------

Consult [URL] for further materials on this chapter.

For more examples of feature-based parsing with |NLTK|, please see the
HOWTOs for feature structures, feature grammars and grammar test suites
at |NLTK-HOWTO-URL|.

For an excellent introduction to the phenomenon of agreement, see
[Corbett2006A]_. 

The earliest use of features in theoretical linguistics was designed
to capture phonological properties of phonemes. For example, a sound
like /**b**/ might be decomposed into the structure [`+labial`:feat:,
`+voice`:feat:]. An important motivation was to capture
generalizations across classes of segments; for example, that /**n**/ gets
realized as /**m**/ preceding any `+labial`:feat: consonant.
Within Chomskyan grammar, it was standard to use atomic features for
phenomena like agreement, and also to capture generalizations across
syntactic categories, by analogy with phonology.
A radical expansion of the use of features in theoretical syntax was
advocated by Generalized Phrase Structure Grammar (GPSG;
[Gazdar1985GPS]_), particularly in the use of features with complex values.

Coming more from the perspective of computational linguistics,
[Kay1984UG]_ proposed that functional aspects of language could be
captured by unification of attribute-value structures, and a similar
approach was elaborated by [Shieber1983FIP]_ within the PATR-II
formalism. Early work in Lexical-Functional grammar (LFG;
[Kaplan1982LFG]_) introduced the notion of an `f-structure`:dt: that
was primarily intended to represent the grammatical relations and
predicate-argument structure associated with a constituent structure
parse.  [Shieber1986IUB]_ provides an excellent introduction to this
phase of research into feature-based grammars.

One conceptual difficulty with algebraic approaches to feature
structures arose when researchers attempted to model negation. An
alternative perspective, pioneered by [Kasper1986LSF]_ and
[Johnson1988AVL]_, argues that grammars involve `descriptions`:em: of
feature structures rather than the structures themselves. These
descriptions are combined using logical operations such as
conjunction, and negation is just the usual logical operation over
feature descriptions. This description-oriented perspective was
integral to LFG from the outset (cf. [Kaplan1989FAL]_, and was also adopted by later
versions of Head-Driven Phrase Structure Grammar (HPSG;
[Sag1999ST]_). A comprehensive bibliography of HPSG literature can be
found at `<http://www.cl.uni-bremen.de/HPSG-Bib/>`_.

Feature structures, as presented in this chapter, are unable to
capture important constraints on linguistic information. For example,
there is no way of saying that the only permissible values for
`num`:feat: are `sg`:fval: and `pl`:fval:, while a specification such
as [`num`:feat:\ =\ `masc`:fval:] is anomalous. Similarly, we cannot say
that the complex value of `agr`:feat: `must`:em: contain
specifications for the features `per`:feat:, `num`:feat: and
`gnd`:feat:, but `cannot`:em: contain a specification such as
[`subcat`:feat:\ =\ `3`:fval:].  `Typed feature structures`:dt: were developed to
remedy this deficiency. To begin with, we stipulate that feature
values are always typed. In the case of atomic values, the values just
are types. For example, we would say that the value of `num`:feat: is
the type *num*. Moreover, *num* is the most general type of value for
`num`:feat:. Since types are organized hierarchically, we can be more
informative by specifying the value of `num`:feat: is a `subtype`:dt:
of *num*, namely either *sg* or *pl*.

In the case of complex values, we say that feature structures are
themselves typed. So for example the value of `agr`:feat: will be a
feature structure of type *agr*. We also stipulate that all and only
`per`:feat:, `num`:feat: and `gnd`:feat: are `appropriate`:dt: features for
a structure of type *agr*.  A good early review of work on typed
feature structures is [Emele1990TUG]_. A more comprehensive examination of
the formal foundations can be found in [Carpenter1992LTF]_, while
[Copestake2002ITF]_ focuses on implementing an HPSG-oriented approach
to typed feature structures.

There is a copious literature on the analysis of German within
feature-based grammar frameworks. [Nerbonne1994GHD]_ is a good
starting point for the HPSG literature on this topic, while
[Mueller2002CP]_ gives a very extensive and detailed analysis of
German syntax in HPSG.

Chapter 15 of [JurafskyMartin2008]_ discusses feature structures,
the unification algorithm, and the integration of unification into
parsing algorithms.

---------
Exercises
---------

#. |easy| What constraints are required to correctly parse strings like `I am
   happy`:lx: and `she is happy`:lx: but not `*you is happy`:lx: or
   `*they am happy`:lx:? Implement two solutions for the present tense
   paradigm of the verb `be`:lx: in English, first taking Grammar
   ex-agcfg1_ as your starting point, and then taking Grammar ex-agr2_
   as the starting point. 

#. |easy| Develop a variant of grammar in Example code-feat0cfg_ that uses a
   feature `count`:feat: to make the distinctions shown below:

   .. ex:: 
       .. ex:: The boy sings.
       .. ex:: \*Boy sings.

   .. ex:: 
       .. ex:: The boys sing.
       .. ex:: Boys sing.

   .. ex:: 
       .. ex:: The boys sing.
       .. ex:: Boys sing.

   .. ex::
       .. ex:: The water is precious.
       .. ex:: Water is precious.

#. |soso| Develop a feature-based grammar that will correctly describe the following
   Spanish noun phrases:

   .. gloss::
	  un                              | cuadro      | hermos-o
	  INDEF.SG.MASC                   | picture     | beautiful-SG.MASC
	  'a beautiful picture'               

   .. gloss::
	  un-os                           | cuadro-s    | hermos-os           
	  INDEF-PL.MASC                   | picture-PL  | beautiful-PL.MASC   
	  'beautiful pictures'                  

   .. gloss::
	  un-a                            | cortina     | hermos-a
	  INDEF-SG.FEM                    | curtain     | beautiful-SG.FEM
	  'a beautiful curtain'     

   .. gloss::
	  un-as                           | cortina-s   | hermos-as
	  INDEF-PL.FEM                    | curtain     | beautiful-PL.FEM
	  'beautiful curtains'     


#. |soso| Develop a wrapper for the ``earley_parser`` so that a trace
   is only printed if the input string fails to parse.

#. |easy| Write a function `subsumes()` which holds of two feature
   structures ``fs1`` and ``fs2`` just in case ``fs1`` subsumes ``fs2``.

#. |soso| Consider the feature structures shown in Example code-featstructures_.

   .. XX NOTE: This example is somewhat broken -- nltk doesn't support
      reentrance for base feature values.  (See email ~7/23/08 to the
      nltk-users mailing list for details.)
      Now updated to avoid this problem. EK

   .. pylisting:: code-featstructures
      :caption: Exploring Feature Structures

      fs1 = nltk.FeatStruct("[A = ?x, B= [C = ?x]]")
      fs2 = nltk.FeatStruct("[B = [D = d]]")
      fs3 = nltk.FeatStruct("[B = [C = d]]")
      fs4 = nltk.FeatStruct("[A = (1)[B = b], C->(1)]")
      fs5 = nltk.FeatStruct("[A = (1)[D = ?x], C = [E -> (1), F = ?x] ]")
      fs6 = nltk.FeatStruct("[A = [D = d]]")
      fs7 = nltk.FeatStruct("[A = [D = d], C = [F = [D = d]]]")
      fs8 = nltk.FeatStruct("[A = (1)[D = ?x, G = ?x], C = [B = ?x, E -> (1)] ]")
      fs9 = nltk.FeatStruct("[A = [B = b], C = [E = [G = e]]]")
      fs10 = nltk.FeatStruct("[A = (1)[B = b], C -> (1)]")

   Work out on paper what the result is of the following
   unifications. (Hint: you might find it useful to draw the graph structures.)

   #) ``fs1`` and ``fs2``
   #) ``fs1`` and ``fs3``
   #) ``fs4`` and ``fs5``
   #) ``fs5`` and ``fs6``
   #) ``fs5`` and ``fs7``
   #) ``fs8`` and ``fs9``
   #) ``fs8`` and ``fs10``

   Check your answers using Python.


#. |soso| List two feature structures that subsume [A=?x, B=?x].

#. |soso| Ignoring structure sharing, give an informal algorithm for unifying
   two feature structures. 

#. |easy| Modify the grammar illustrated in ex-subcatgpsg_ to
   incorporate a `bar`:feat: feature for dealing with phrasal projections.

#. |easy| Modify the German grammar in Example code-germancfg_ to incorporate the
   treatment of subcategorization presented in sec-extending-a-feature-based-grammar_. 

#. |soso| Extend the German grammar in Example code-germancfg_ so that it can
   handle so-called verb-second structures like the following:

   .. ex:: Heute sieht der hund die katze.

#. |hard| Morphological paradigms are rarely completely regular, in
   the sense of every cell in the matrix having a different
   realization. For example, the present tense conjugation of the
   lexeme `walk`:lex: only has two distinct forms: `walks`:lx: for the
   3rd person singular, and `walk`:lx: for all other combinations of
   person and number. A successful analysis should not require
   redundantly specifying that 5 out of the 6 possible morphological
   combinations have the same realization.  Propose and implement a
   method for dealing with this.

#. |hard| So-called `head features`:dt: are shared between the mother
   and head daughter. For example, `tense`:feat: is a head feature
   that is shared between a ``VP`` and its head ``V``
   daughter. See [Gazdar1985GPS]_ for more details. Most of the
   features we have looked at are head features |mdash| exceptions are
   `subcat`:feat: and `slash`:feat:. Since the sharing of head
   features is predictable, it should not need to be stated explicitly
   in the grammar productions. Develop an approach that automatically
   accounts for this regular behavior of head features.  


.. include:: footer.rst
