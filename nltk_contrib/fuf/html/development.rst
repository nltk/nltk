
`nltk.fuf` Development
======================

:Last Update: August 5th, 2008
:Author: Petro Verkhogliad <vpetro@gmail.com>

This document details the current state of development of the ``nltk.fuf`` module
found in the ``nltk/nltk_contrib/fuf`` directory. In short, this code currently capable
of processing simple grammars (``tests/gr0.fuf`` as grammar and ``tests/ir0.fuf`` as input or 
``tests/gr1.fuf`` with ``tests/ir1.fuf``).

Overall Structure
=================
- **fufconvert.py** - converts a FUF grammar s-expression into an ``nltk.FeatStruct``. 
  From here on, all of the work is done on feature structure found in ``nltk.featstruct`` module.
- **fuf.py** - uses the input feature structure and the grammar feature stucture and unifies them 
  according to the FUF unification guidlines (more on this later).
- **linearizer.py** - uses the results of the unification to produce the final text output 
  with the help of the **morphology.py**


fufconvert.py or Parsing the input
----------------------------------
The ``fufconvert.py`` module is responsible for converting a given s-expression into a feature 
structure. There are two main entry points for ``fufconvert.py``.

- ``fufconvert.fuf_to_featstruct`` function.
  This function a single s-expression into an NLTK feature structure.

    >>> import fufconvert
    >>> # read a line from the text file
    >>> line = open('tests/gr0.fuf').readlines()[0]
    >>> print line
    >>> # convert the line to feature structure
    >>> fstruct = fufconvert.fuf_to_featstruct(line)
    >>> print fstruct


- ``fufconvert.fuf_file_to_featstruct`` function.
  This function converts a grammar file that contains the grammar s-expression as well as 
  feature type declarations.

    >>> import fufconvert
    >>> type_table, grammar = fufconvert.fuf_file_to_featstruct('tests/typed_gr4.fuf')

  If there are not type definitions in the file then the ``type_table`` varible will contain
  an empty dictionary.

Both of the functions rely on ``sexp.py`` to parse and convert the file. The ``sexp.py`` module
uses a stack based state machine defined in ``statemachine.py`` file. The state machine does
bracket matching and will throw a ``ValueError`` if the brackets are mismatched.

At the same time, FUF defined some special keys and values that must be handled diffferently from 
the usual key, value grammar pairs. They are:

- `alt`

  This key defines alternations. There is no direct way to represent alternations within 
  the NLTK feature structures. ``nltk.fuf`` uses the following scheme:
  - if the `alt` does not have a specific name it is represented like this:

    ::

        [           [     [ cat     = 's'                        ]            ] ]
        [           [     [                                      ]            ] ]
        [           [     [ goal    = [ cat = 'np' ]             ]            ] ]
        [           [     [                                      ]            ] ]
        [           [ 1 = [ pattern = (prot, verb, goal)         ]            ] ]
        [           [     [                                      ]            ] ]
        [           [     [ prot    = [ cat = 'np' ]             ]            ] ]
        [           [     [                                      ]            ] ]
        [           [     [ verb    = [ cat    = 'vp'          ] ]            ] ]
        [           [     [           [ number = {prot number} ] ]            ] ]
        [           [                                                         ] ]
        [           [     [       [ 1 = [ pattern = (n)   ]               ] ] ] ]
        [           [     [       [     [ proper  = 'yes' ]               ] ] ] ]
        [           [     [       [                                       ] ] ] ]
        [           [     [ alt = [     [ det     = [ cat = 'article' ] ] ] ] ] ]
        [           [     [       [     [           [ lex = 'the'     ] ] ] ] ] ]
        [           [     [       [ 2 = [                               ] ] ] ] ]
        [ alt     = [ 2 = [       [     [ pattern = (det, n)            ] ] ] ] ]
        [           [     [       [     [ proper  = 'no'                ] ] ] ] ]
        [           [     [                                                 ] ] ]
        [           [     [ cat = 'np'                                      ] ] ]
        [           [     [                                                 ] ] ]
        [           [     [ n   = [ cat    = 'noun'     ]                   ] ] ]
        [           [     [       [ number = {^^number} ]                   ] ] ]
        [           [                                                         ] ]
        [           [     [ cat     = 'vp'             ]                      ] ]
        [           [ 3 = [ pattern = (v)              ]                      ] ]
        [           [     [                            ]                      ] ]
        [           [     [ v       = [ cat = 'verb' ] ]                      ] ]
        [           [                                                         ] ]
        [           [ 4 = [ cat = 'noun' ]                                    ] ]
        [           [                                                         ] ]
        [           [ 5 = [ cat = 'verb' ]                                    ] ]
        [           [                                                         ] ]
        [           [ 6 = [ cat = 'article' ]                                 ] ]

    Note that there are two `alt` features in this grammar.

  - if the `alt` does have a specific name it is represented like this:

    ::

        [           [     [ cat     = 's'                        ]            ] ]
        [           [     [                                      ]            ] ]
        [           [     [ goal    = [ cat = 'np' ]             ]            ] ]
        [           [     [                                      ]            ] ]
        [           [ 1 = [ pattern = (prot, verb, goal)         ]            ] ]
        [           [     [                                      ]            ] ]
        [           [     [ prot    = [ cat = 'np' ]             ]            ] ]
        [           [     [                                      ]            ] ]
        [           [     [ verb    = [ cat    = 'vp'          ] ]            ] ]
        [           [     [           [ number = {prot number} ] ]            ] ]
        [           [                                                         ] ]
        [           [     [       [ 1 = [ pattern = (n)   ]               ] ] ] ]
        [           [     [       [     [ proper  = 'yes' ]               ] ] ] ]
        [           [     [       [                                       ] ] ] ]
        [           [     [ alt = [     [ det     = [ cat = 'article' ] ] ] ] ] ]
        [           [     [       [     [           [ lex = 'the'     ] ] ] ] ] ]
        [           [     [       [ 2 = [                               ] ] ] ] ]
        [ alt_top = [ 2 = [       [     [ pattern = (det, n)            ] ] ] ] ]
        [           [     [       [     [ proper  = 'no'                ] ] ] ] ]
        [           [     [                                                 ] ] ]
        [           [     [ cat = 'np'                                      ] ] ]
        [           [     [                                                 ] ] ]
        [           [     [ n   = [ cat    = 'noun'     ]                   ] ] ]
        [           [     [       [ number = {^^number} ]                   ] ] ]
        [           [                                                         ] ]
        [           [     [ cat     = 'vp'             ]                      ] ]
        [           [ 3 = [ pattern = (v)              ]                      ] ]
        [           [     [                            ]                      ] ]
        [           [     [ v       = [ cat = 'verb' ] ]                      ] ]
        [           [                                                         ] ]
        [           [ 4 = [ cat = 'noun' ]                                    ] ]
        [           [                                                         ] ]
        [           [ 5 = [ cat = 'verb' ]                                    ] ]
        [           [                                                         ] ]
        [           [ 6 = [ cat = 'article' ]                                 ] ]

    The difference is the ``_name`` in the `alt` string.

- the next key is the `opt` key. It is very similar to `alt` in that it may have a name
  and it also specifies a list of alternations (the unification for `opt` works slightly differently
  , but more on this in the unification section). Since `opt` and `alt` are very similar ``nltk.fuf``
  uses the same `alt` syntax for the `opt` key. For example:

  ::

        [       [ 1 = [ punctuation = [ after = '.' ] ] ] ]
        [ alt = [                                       ] ]
        [       [ 2 = []                                ] ]
  
  If the `opt` is named then it is represented like this:

  ::

        [                [ 1 = [ punctuation = [ after = '.' ] ] ] ]
        [ alt_somename = [                                       ] ]
        [                [ 2 = []                                ] ]

The special parsing code for `opt` and `alt` is located in ``nltk.fuf.speacialfs``. It is important to note
that the altenation keys (ie 1,2,3,4) are specified based on the other each altenation appears in the `alt` or `opt`
structure. The empty feature structure in the converted `opt` feature always appears last in the list
of alternations.

Another possible special value of the converted feature structure is the relative or absolute `link`.
The links may appear as a value of any feature key. The link value is enclosed in ``{}``. During parsing, 
the links are converted into Python objects through the ``nltk.fuf.link.ReentranceLink`` class.  Looking
at the converted feature structure below one of the links is found at ``alt_top['2']['n']['number']`` key. 
Another link is located at ``alt_top['1']['verb']['number']``. The link syntax and resolution is discussed later.

::

    [           [     [ cat     = 's'                        ]            ] ]
    [           [     [                                      ]            ] ]
    [           [     [ goal    = [ cat = 'np' ]             ]            ] ]
    [           [     [                                      ]            ] ]
    [           [ 1 = [ pattern = (prot, verb, goal)         ]            ] ]
    [           [     [                                      ]            ] ]
    [           [     [ prot    = [ cat = 'np' ]             ]            ] ]
    [           [     [                                      ]            ] ]
    [           [     [ verb    = [ cat    = 'vp'          ] ]            ] ]
    [           [     [           [ number = {prot number} ] ]            ] ]
    [           [                                                         ] ]
    [           [     [       [ 1 = [ pattern = (n)   ]               ] ] ] ]
    [           [     [       [     [ proper  = 'yes' ]               ] ] ] ]
    [           [     [       [                                       ] ] ] ]
    [           [     [ alt = [     [ det     = [ cat = 'article' ] ] ] ] ] ]
    [           [     [       [     [           [ lex = 'the'     ] ] ] ] ] ]
    [           [     [       [ 2 = [                               ] ] ] ] ]
    [ alt_top = [ 2 = [       [     [ pattern = (det, n)            ] ] ] ] ]
    [           [     [       [     [ proper  = 'no'                ] ] ] ] ]
    [           [     [                                                 ] ] ]
    [           [     [ cat = 'np'                                      ] ] ]
    [           [     [                                                 ] ] ]
    [           [     [ n   = [ cat    = 'noun'     ]                   ] ] ]
    [           [     [       [ number = {^^number} ]                   ] ] ]
    [           [                                                         ] ]
    [           [     [ cat     = 'vp'             ]                      ] ]
    [           [ 3 = [ pattern = (v)              ]                      ] ]
    [           [     [                            ]                      ] ]
    [           [     [ v       = [ cat = 'verb' ] ]                      ] ]
    [           [                                                         ] ]
    [           [ 4 = [ cat = 'noun' ]                                    ] ]
    [           [                                                         ] ]
    [           [ 5 = [ cat = 'verb' ]                                    ] ]
    [           [                                                         ] ]
    [           [ 6 = [ cat = 'article' ]                                 ] ]


Finally, when the input feature structure and the grammar have been converted, we can proceed to 
their unification.

fuf.py or Towards a Result
--------------------------

Preprocessing
~~~~~~~~~~~~~

Unification is perfomed by the ``nltk.fuf.fuf.Unifier`` class. Before the unfication can start 
some housekeeping must be done. Currently, the housekeeping revolves around processing the `alt`
features. Thus, before the unification start the code goes through all the possible alternations
in the grammar and creates a list of those paths. This is done with the ``nltk.fuf.fuf.GrammarPathResolver``.
The result of the resolution is a a list of all possible feature stuctures generated through the alternations.
The original LISP FUF does not do this, rather it just picks up one `alt` path after another and tries to unify
the alternation with the input. This is clearly not the optimal solution as the size of the returned list
grows exponentially based on the number of `alt` features within the grammar. This is fertile ground 
for improvements.

Types and their use during unification
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Once the alt paths have been generated, the next step is a check for feature value types. 
Feature value type handling is done through the ``nltk.fuf.fstypes`` module. The two classes contained
within the module are:

- ``FeatureValueTypeTable``
  The type table does all the maintenace of the value types. For a better discussion on feature value types
  as they are defined in FUF please refer to the the FUF Manual (v5.2). The example below shows the 
  definition of several types. The syntax means that `finite` and `non-finite` are specializations
  of the `mood`.
  
  In ``FeatureValueTypeTable`` these relationships are stored within a ``dict`` object.

  ::

    (define-feature-type mood (finite non-finite))
    (define-feature-type finite (declarative interrogative bound relative))
    (define-feature-type non-finite (imperative present-participle infinitive))
    (define-feature-type interrogative (yes-no wh))

  Using the ``tests/types.fuf`` file the result type table is this (the same result can be seen by running
  ``python fstypes.py``):

  ::

    relative <--- ['simple-relative', 'embedded-relative', 'be-deleted-relative', 'wh-nominal-relative', 'wh-ever-nominal-relative']
    mood <--- ['finite', 'non-finite']
    non-finite <--- ['imperative', 'present-participle', 'infinitive']
    deontic-modality <--- ['duty', 'authorization']
    pronp <--- ['personal-pronoun', 'question-pronoun', 'quantified-pronoun', 'demonstrative-pronoun']
    det <--- ['possessive-det', 'demonstrative-det', 'regular-det']
    interrogative <--- ['yes-no', 'wh']
    process-type <--- ['action', 'mental', 'attributive', 'equative']
    np <--- ['pronp', 'common', 'proper']
    finite <--- ['declarative', 'interrogative', 'bound', 'relative']
    possessive-det <--- ['np']
    modality <--- ['epistemic-modality', 'deontic-modality']
    epistemic-modality <--- ['fact', 'inference', 'possible']
 
  We can use the ``FeatureTypeTable`` to check for subsumption. Working with the above table, we can do this by:

  ::
   
    >>> type_table.subsume('np', 'common')
    >>> # or
    >>> types_table.subsume('mood', 'imperative')

  Both of the function calls to ``subsume`` on this table return ``True``. During the unfication
  the unifier off-loads the unification of typed features to the ``TypeFeatureValue`` class.

- ``TypedFeatureValue``

  This class is used to represent the value within a feature structure. If the type table is present 
  with within the grammar file that is undergoing unification. The ``TypedFeatureValue`` is a subclass
  of the ``CustomFeatureValue`` class defined ``nltk.featstruct``. The ``CustomeFeatureValue`` allows 
  us to defined special unification on the value that are instances of this class. 

As in the case with the `alt` unpacking, before the grammar can be unified with the input feature 
structure, feature values which are defined in the type table have to be instantiated in with in the grammar.
This work is performed by the ``fstypes.assign_types`` function. It traverses the given feature structure
and replaces the primitive values with instances of ``TypedFeatureValue``.

Unification
~~~~~~~~~~~

Once all of housekeeping tasks are finished we can proceed to the actual unfication of the input and grammar
feature structures. The process of unification is defined in the ``nltk.fuf.fuf.Unifier`` class and more 
specifically the ``unify`` method of the class. 

The unifier attempts to unify one of the alternations from the alternations list generated by ``GrammarPathResolver`` 
with the input. If all of the attempts to unify with the input fail then unification has failed. If one of 
the attepts succeeds, the resultant feature structure must be checked for relative or absolute `links`.

Relative and Absolute Links
+++++++++++++++++++++++++++

As mentioned previously, the class that represents either the relative or the absolute link in ``nltk.fuf``
is ``nltk.fuf.link.ReentraceLink``. When viewing a human-readable version of a feature strucuture they 
can be identifed as feature values that are enclosed in ``{}``. There are two types of links `relative` and
`absolute`. Relative links are have ``^`` following the ``{`` and absolute links have a feature key 
following the ``{``. For example, ``number = {^^number}`` is an relative link, whereas  ``number = {prot number}`` 
is a absolute link. The ``^`` refers to the feature structure that has within it ``number = {^^number}``. 
The more ``^`` character there are the further the link goes up the structure. In absolute links, 
the contents of ``{}`` define a path from the root feature structure to the the value they are pointing to.
There is no change here form the relative or absolute links as they used in the LISP FUF.

Link resolution is performed by the ``nltk.fuf.link.LinkResolver`` class, and the ``resolve`` method in particular.
This class is capable of handling both types of links. It is worth noting that the ``resolve`` method 
will try to find the value of the link whether it is another feature structure or a primitive value. However,
if the value cannot be the link will be repaced with ``nltk.sem.Variable``. Counts of the variables are done 
during the lifetime of the ``LinkResolver`` object, thus they do not clash. If the value of the link is 
a variable the varialbe will be copied. If the value of the link is another link, the resolver will attempt to 
resolve the newly found link first and then copy the value to the link that it encountered first. 


Unification Continued
~~~~~~~~~~~~~~~~~~~~~
Once the link resolution has been performed on the result of the unification, the unifier goes 
through the sub-features of the result and attepts to unify the sub-features with the features
that represent grammar paths. Only those features which are considered to be `constituents` are 
unified. A `constituent` feature is one that either contains a `cat` feature or is mentioned in 
the `pattern` value or contains a `lex` feature or is specifically mentioned in the `cset` feature 
value. Attemping to unfify features that are not constituents may result in infinite recursion.

The overall process of unification is illustrated in the example below (note that this exaple does not use the 
feature types):

::

    >>> itext, gtext = open('tests/uni.fuf').readlines()
    # set up the input structure
    >>> fsinput = fuf_to_featstruct(itext)
    >>> print fsinput
    [ cat  = 's'                      ]
    [                                 ]
    [ goal = [ n = [ lex = 'mary' ] ] ]
    [                                 ]
    [ prot = [ n = [ lex = 'john' ] ] ]
    [                                 ]
    [ verb = [ v = [ lex = 'link' ] ] ]
    # set up the grammar structure
    >>> fsgrammar = fuf_to_featstruct(gtext)
    >>> print fsgrammar
    [           [     [ cat     = 's'                        ]            ] ]
    [           [     [                                      ]            ] ]
    [           [     [ goal    = [ cat = 'np' ]             ]            ] ]
    [           [     [                                      ]            ] ]
    [           [ 1 = [ pattern = (prot, verb, goal)         ]            ] ]
    [           [     [                                      ]            ] ]
    [           [     [ prot    = [ cat = 'np' ]             ]            ] ]
    [           [     [                                      ]            ] ]
    [           [     [ verb    = [ cat    = 'vp'          ] ]            ] ]
    [           [     [           [ number = {prot number} ] ]            ] ]
    [           [                                                         ] ]
    [           [     [       [ 1 = [ pattern = (n)   ]               ] ] ] ]
    [           [     [       [     [ proper  = 'yes' ]               ] ] ] ]
    [           [     [       [                                       ] ] ] ]
    [           [     [ alt = [     [ det     = [ cat = 'article' ] ] ] ] ] ]
    [           [     [       [     [           [ lex = 'the'     ] ] ] ] ] ]
    [           [     [       [ 2 = [                               ] ] ] ] ]
    [ alt_top = [ 2 = [       [     [ pattern = (det, n)            ] ] ] ] ]
    [           [     [       [     [ proper  = 'no'                ] ] ] ] ]
    [           [     [                                                 ] ] ]
    [           [     [ cat = 'np'                                      ] ] ]
    [           [     [                                                 ] ] ]
    [           [     [ n   = [ cat    = 'noun'     ]                   ] ] ]
    [           [     [       [ number = {^^number} ]                   ] ] ]
    [           [                                                         ] ]
    [           [     [ cat     = 'vp'             ]                      ] ]
    [           [ 3 = [ pattern = (v)              ]                      ] ]
    [           [     [                            ]                      ] ]
    [           [     [ v       = [ cat = 'verb' ] ]                      ] ]
    [           [                                                         ] ]
    [           [ 4 = [ cat = 'noun' ]                                    ] ]
    [           [                                                         ] ]
    [           [ 5 = [ cat = 'verb' ]                                    ] ]
    [           [                                                         ] ]
    [           [ 6 = [ cat = 'article' ]                                 ] ]
    # unify the input and the grammar
    >>> fuf = Unifier(fsinput, fsgrammar)
    >>> result = fuf.unify()
    # show the result
    >>> print result
    [ cat     = 's'                               ]
    [                                             ]
    [           [ cat     = 'np'                ] ]
    [           [                               ] ]
    [           [           [ cat    = 'noun' ] ] ]
    [           [ n       = [ lex    = 'mary' ] ] ]
    [ goal    = [           [ number = ?x2    ] ] ]
    [           [                               ] ]
    [           [ number  = ?x2                 ] ]
    [           [ pattern = (n)                 ] ]
    [           [ proper  = 'yes'               ] ]
    [                                             ]
    [ pattern = (prot, verb, goal)                ]
    [                                             ]
    [           [ cat     = 'np'                ] ]
    [           [                               ] ]
    [           [           [ cat    = 'noun' ] ] ]
    [           [ n       = [ lex    = 'john' ] ] ]
    [ prot    = [           [ number = ?x1    ] ] ]
    [           [                               ] ]
    [           [ number  = ?x1                 ] ]
    [           [ pattern = (n)                 ] ]
    [           [ proper  = 'yes'               ] ]
    [                                             ]
    [           [ cat     = 'vp'             ]    ]
    [           [ number  = ?x1              ]    ]
    [ verb    = [ pattern = (v)              ]    ]
    [           [                            ]    ]
    [           [ v       = [ cat = 'verb' ] ]    ]
    [           [           [ lex = 'link' ] ]    ]

Having obtained the result of unification we can proceed to linerarization of the output in order to generate
the final text output.

linearizer.py or Reaching for the Final Output
----------------------------------------------
The linearization of the output produces the final output. The code for this is in ``nltk.fuf.linearizer``, 
specifically the ``linearize`` function.
The process starts by selecting the top level `pattern` feature value. The `pattern` features 
spread through out the unification result define the order of the text. For example, in the structure
below:

::

  [ cat     = 's'                               ]
  [                                             ]
  [           [ cat     = 'np'                ] ]
  [           [                               ] ]
  [           [           [ cat    = 'noun' ] ] ]
  [           [ n       = [ lex    = 'mary' ] ] ]
  [ goal    = [           [ number = ?x2    ] ] ]
  [           [                               ] ]
  [           [ number  = ?x2                 ] ]
  [           [ pattern = (n)                 ] ]
  [           [ proper  = 'yes'               ] ]
  [                                             ]
  [ pattern = (prot, verb, goal)                ]
  [                                             ]
  [           [ cat     = 'np'                ] ]
  [           [                               ] ]
  [           [           [ cat    = 'noun' ] ] ]
  [           [ n       = [ lex    = 'john' ] ] ]
  [ prot    = [           [ number = ?x1    ] ] ]
  [           [                               ] ]
  [           [ number  = ?x1                 ] ]
  [           [ pattern = (n)                 ] ]
  [           [ proper  = 'yes'               ] ]
  [                                             ]
  [           [ cat     = 'vp'             ]    ]
  [           [ number  = ?x1              ]    ]
  [ verb    = [ pattern = (v)              ]    ]
  [           [                            ]    ]
  [           [ v       = [ cat = 'verb' ] ]    ]
  [           [           [ lex = 'link' ] ]    ]

the top level `pattern` has the value ``(prot, verb, goal)``. Thefore the order of linearization is ``prot`` feature
first, ``verb`` feature second, and finally the ``goal`` feature. Following this path the linearizer 
looks for `pattern` values in the sub-features until it finds the `lex` feature. At this stage the 
morphology must be applied. Once the morphology has been applied the result is returned and the generation
process is finished.


Morphology
~~~~~~~~~~
The morpholgy module, ``nltk.fuf.morphology`` coupled with ``nltk.fuf.lexicon``, is a direct port of the LISP FUF ``morphology.scm`` code. It is currently implemented
as a set of heurirstics. However, it has decent converage. The code is quite self-descriptive.
  

Further Research/Work
---------------------------------

There are a number of improvements and features that can be made/added to the ``nltk.fuf`` library.

- the `index` sub-feature in the `alt` feature is largely ignored at the moment. In LISP FUF this is 
  used to control the size of the possible paths through grammar. While this is parsed at the moment
  it is not used to help the unifier.

- it should be possible to do the unification without unpacking all the `alt` paths through the grammar.
  ie, expand a little bit and go from there.

- changing the `alt` handling requires changes timing for the link resolution.

- currently during parsing all the comments and tracing calls are removed. It would be nice 
  to be able to enable tracing all stages of processing.

- there are utility functions defined in LISP FUF to controll backtracking. These should be implemented as well.


Further Reading
---------------

- API documntation - ``nltk_contrib/fuf/doc/api.html``

- Home of LISP FUF/SURGE - http://www.cs.bgu.ac.il/surge/index.html

- Grammars with Feature Strutures - http://nltk.org/doc/en/featgram.html

- NLTK Feature STructure Guide - http://nltk.org/doc/guides/featstruct.html
