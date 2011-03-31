
=======================
Computing with Language
=======================

* not a conventional introduction to programming where we work
  through language features one by one
  (in fact, features will be introduced in a rather unusual order)
* plenty of such books exist already (incl for Python)
* instead, a problem-oriented approach: a series of tasks each requiring some programming,
  each building on what has come before (so getting more difficult)
* starting point: we have lots of text and lots of computing cycles: what can we do?
* no prior programming ability assumed, just retyping examples

----------------------------------
Searching large quantities of text
----------------------------------

* most obvious: searching large amounts of text
* includes functionality for generating random text in this style
* first-hand experience with scale and diversity of corpora

Questions coming out of this:
* what makes texts different?
* what is a text?  seq of characters on a page (does page matter?)
  seq of words?  seq of chapters made up of seq of paras ...
* our simplification: text = sequence of words (plus punctuation 'words'): "tokens"
* explicit notation: ["the", "cat", "sat", "on", "the", "mat"]
* key concept: TEXT = LIST OF WORDS
* reuse material from 2.4.1

IDLE session:
* getting started with IDLE
* lists, str.split(), len()
* variables

-------------------
Counting vocabulary
-------------------

* one thing that makes texts different is the set of words used (vocabulary)
* vocabulary richness
* defining functions -- allows us to explain what the () are everywhere
  and gives inkling of the power of programming
* key concept: VOCABULARY = SET OF WORDS

IDLE session:
* str.lower()
* defining simple functions (diagram of unary function)


>>> sorted(set(word for word in text3 if word.endswith("eth")))
['Hazarmaveth', 'Heth', 'Japheth', 'Jetheth', 'Seth', 'aileth', 'asketh', 'biteth', 'blesseth', 'breaketh', 'cometh', 'compasseth', 'creepeth', 'crieth', 'curseth', 'divineth', 'doeth', 'drinketh', 'faileth', 'findeth', 'giveth', 'goeth', 'knoweth', 'lieth', 'liveth', 'longeth', 'loveth', 'meeteth', 'moveth', 'needeth', 'pleaseth', 'proceedeth', 'remaineth', 'repenteth', 'seeth', 'sheddeth', 'sheweth', 'slayeth', 'speaketh', 'teeth', 'togeth', 'toucheth', 'twentieth', 'walketh', 'wotteth']



-------
Corpora
-------

* definition
* accessing
    


--------------
Changing Tense
--------------

* convert a verb into past tense (perfect)
* motivation?
* key concepts: CONDITIONAL EXPRESSIONS, STRINGS

IDLE session:
* string concatenation
* string indexing
* conditional expressions
* function past(word) -> past-tense form

--------------
Classification
--------------

* informal study of how texts differ
* genre, author, language
* FreqDists initialized with list comprehensions
* key concept: COMPREHENSIONS (ITERATION)

IDLE session:
* word length distribution plot: FreqDist(len(word) for word in text).plot()
  (comparing languages, text difficulties)
  (need to permit >1 plot to be overlaid)
* character distribution plot: FreqDist(char for word in text for char in word).plot()
  (comparing languages)
* relative frequency of modals: FreqDist(word for word in text if word in modals).plot()
  (comparing Brown corpus genres)


  


