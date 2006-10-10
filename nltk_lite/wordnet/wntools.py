# Module wordnet.py
#
# Original author: Oliver Steele <steele@osteele.com>
# Project Page: http://sourceforge.net/projects/pywordnet
#
# Copyright (c) 1998-2004 by Oliver Steele.  Use is permitted under
# the Artistic License
# <http://www.opensource.org/licenses/artistic-license.html>

"""Utility functions to use with the wordnet module.

Usage
-----
    >>> dog = N['dog'][0]

    # (First 10) adjectives that are transitively SIMILAR to the main sense of 'red'
    >>> closure(ADJ['red'][0], SIMILAR)[:10]
    ['red' in {adjective: red, reddish, ruddy, blood-red, carmine, cerise, cherry, cherry-red, crimson, ruby, ruby-red, scarlet}, {adjective: chromatic}, {adjective: amber, brownish-yellow, yellow-brown}, {adjective: amethyst}, {adjective: aureate, gilded, gilt, gold, golden}, {adjective: azure, cerulean, sky-blue, bright blue}, {adjective: blue, bluish, blueish, light-blue, dark-blue, blue-black}, {adjective: bluish green, blue-green, cyan, teal}, {adjective: blushful, rosy}, {adjective: bottle-green}]

    >>> # Adjectives that are transitively SIMILAR to any of the senses of 'red'
    >>> #flatten1(map(lambda sense:closure(sense, SIMILAR), ADJ['red']))    # too verbose

    >>> # Hyponyms of the main sense of 'dog'(n.) that are homophonous with verbs
    >>> filter(lambda sense:V.get(sense.form), flatten1(map(lambda e:e.getSenses(), hyponyms(N['dog'][0]))))
    ['dog' in {noun: dog, domestic dog, Canis familiaris}, 'pooch' in {noun: pooch, doggie, doggy, barker, bow-wow}, 'toy' in {noun: toy dog, toy}, 'hound' in {noun: hound, hound dog}, 'basset' in {noun: basset, basset hound}, 'cocker' in {noun: cocker spaniel, English cocker spaniel, cocker}, 'bulldog' in {noun: bulldog, English bulldog}]

    >>> # Find the senses of 'raise'(v.) and 'lower'(v.) that are antonyms
    >>> filter(lambda p:p[0] in p[1].pointerTargets(ANTONYM), product(V['raise'].getSenses(), V['lower'].getSenses()))
    [('raise' in {verb: raise, lift, elevate, get up, bring up}, 'lower' in {verb: lower, take down, let down, get down, bring down})]
"""

__author__  = "Oliver Steele <steele@osteele.com>"
__version__ = "2.0"

from wordnet import *

#
# Domain utilities
#

def _requireSource(entity):
    if not hasattr(entity, 'pointers'):
        if isinstance(entity, Word):
            raise TypeError, `entity` + " is not a Sense or Synset.  Try " + `entity` + "[0] instead."
        else:
            raise TypeError, `entity` + " is not a Sense or Synset"

def tree(source, pointerType):
    """
    >>> dog = N['dog'][0]
    >>> from pprint import pprint
    >>> pprint(tree(dog, HYPERNYM))
    ['dog' in {noun: dog, domestic dog, Canis familiaris},
     [{noun: canine, canid},
      [{noun: carnivore},
       [{noun: placental, placental mammal, eutherian, eutherian mammal},
        [{noun: mammal},
         [{noun: vertebrate, craniate},
          [{noun: chordate},
           [{noun: animal, animate being, beast, brute, creature, fauna},
            [{noun: organism, being},
             [{noun: living thing, animate thing},
              [{noun: object, physical object}, [{noun: entity}]]]]]]]]]]]]
    >>> #pprint(tree(dog, HYPONYM)) # too verbose to include here
    """
    if isinstance(source,  Word):
        return map(lambda s, t=pointerType:tree(s,t), source.getSenses())
    _requireSource(source)
    return [source] + map(lambda s, t=pointerType:tree(s,t), source.pointerTargets(pointerType))

def closure(source, pointerType, accumulator=None):
    """Return the transitive closure of source under the pointerType
    relationship.  If source is a Word, return the union of the
    closures of its senses.
    
    >>> dog = N['dog'][0]
    >>> closure(dog, HYPERNYM)
    ['dog' in {noun: dog, domestic dog, Canis familiaris}, {noun: canine, canid}, {noun: carnivore}, {noun: placental, placental mammal, eutherian, eutherian mammal}, {noun: mammal}, {noun: vertebrate, craniate}, {noun: chordate}, {noun: animal, animate being, beast, brute, creature, fauna}, {noun: organism, being}, {noun: living thing, animate thing}, {noun: object, physical object}, {noun: entity}]
    """
    if isinstance(source, Word):
        return reduce(union, map(lambda s, t=pointerType:tree(s,t), source.getSenses()))
    _requireSource(source)
    if accumulator is None:
        accumulator = []
    if source not in accumulator:
        accumulator.append(source)
        for target in source.pointerTargets(pointerType):
            closure(target, pointerType, accumulator)
    return accumulator

def hyponyms(source):
    """Return source and its hyponyms.  If source is a Word, return
    the union of the hyponyms of its senses."""
    return closure(source, HYPONYM)

def hypernyms(source):
    """Return source and its hypernyms.  If source is a Word, return
    the union of the hypernyms of its senses."""

    return closure(source, HYPERNYM)

def meet(a, b, pointerType=HYPERNYM):
    """Return the meet of a and b under the pointerType relationship.
    
    >>> meet(N['dog'][0], N['cat'][0])
    {noun: carnivore}
    >>> meet(N['dog'][0], N['person'][0])
    {noun: organism, being}
    >>> meet(N['thought'][0], N['belief'][0])
    {noun: content, cognitive content, mental object}
    """
    return (intersection(closure(a, pointerType), closure(b, pointerType)) + [None])[0]


#
# String Utility Functions
#
def startsWith(str, prefix):
    """Return true iff _str_ starts with _prefix_.
    
    >>> startsWith('unclear', 'un')
    1
    """
    return str[:len(prefix)] == prefix

def endsWith(str, suffix):
    """Return true iff _str_ ends with _suffix_.
    
    >>> endsWith('clearly', 'ly')
    1
    """
    return str[-len(suffix):] == suffix

def equalsIgnoreCase(a, b):
    """Return true iff a and b have the same lowercase representation.
    
    >>> equalsIgnoreCase('dog', 'Dog')
    1
    >>> equalsIgnoreCase('dOg', 'DOG')
    1
    """
    # test a == b first as an optimization where they're equal
    return a == b or string.lower(a) == string.lower(b)


#
# Sequence Utility Functions
#
def issequence(item):
    """Return true iff _item_ is a Sequence (a List, String, or Tuple).
    
    >>> issequence((1,2))
    1
    >>> issequence([1,2])
    1
    >>> issequence('12')
    1
    >>> issequence(1)
    0
    """
    return type(item) in (ListType, StringType, TupleType)

def intersection(u, v):
    """Return the intersection of _u_ and _v_.
    
    >>> intersection((1,2,3), (2,3,4))
    [2, 3]
    """
    w = []
    for e in u:
        if e in v:
            w.append(e)
    return w

def union(u, v):
    """Return the union of _u_ and _v_.
    
    >>> union((1,2,3), (2,3,4))
    [1, 2, 3, 4]
    """
    w = list(u)
    if w is u:
        import copy
        w = copy.copy(w)
    for e in v:
        if e not in w:
            w.append(e)
    return w

def product(u, v):
    """Return the Cartesian product of u and v.
    
    >>> product("123", "abc")
    [('1', 'a'), ('1', 'b'), ('1', 'c'), ('2', 'a'), ('2', 'b'), ('2', 'c'), ('3', 'a'), ('3', 'b'), ('3', 'c')]
    """
    return flatten1(map(lambda a, v=v:map(lambda b, a=a:(a,b), v), u))

def removeDuplicates(sequence):
    """Return a copy of _sequence_ with equal items removed.
    
    >>> removeDuplicates("this is a test")
    ['t', 'h', 'i', 's', ' ', 'a', 'e']
    >>> removeDuplicates(map(lambda tuple:apply(meet, tuple), product(N['story'].getSenses(), N['joke'].getSenses())))
    [{noun: message, content, subject matter, substance}, None, {noun: abstraction}, {noun: communication}]
    """
    accumulator = []
    for item in sequence:
        if item not in accumulator:
            accumulator.append(item)
    return accumulator


#
# Tree Utility Functions
#

def flatten1(sequence):
    accumulator = []
    for item in sequence:
        if type(item) == TupleType:
            item = list(item)
        if type(item) == ListType:
            accumulator.extend(item)
        else:
            accumulator.append(item)
    return accumulator


#
# WordNet utilities
#

GET_INDEX_SUBSTITUTIONS = ((' ', '-'), ('-', ' '), ('-', ''), (' ', ''), ('.', ''))

def getIndex(form, pos='noun'):
    """Search for _form_ in the index file corresponding to
    _pos_. getIndex applies to _form_ an algorithm that replaces
    underscores with hyphens, hyphens with underscores, removes
    hyphens and underscores, and removes periods in an attempt to find
    a form of the string that is an exact match for an entry in the
    index file corresponding to _pos_.  getWord() is called on each
    transformed string until a match is found or all the different
    strings have been tried. It returns a Word or None."""
    def trySubstitutions(trySubstitutions, form, substitutions, lookup=1, dictionary=dictionaryFor(pos)):
        if lookup and dictionary.has_key(form):
            return dictionary[form]
        elif substitutions:
            (old, new) = substitutions[0]
            substitute = string.replace(form, old, new) and substitute != form
            if substitute and dictionary.has_key(substitute):
                return dictionary[substitute]
            return              trySubstitutions(trySubstitutions, form, substitutions[1:], lookup=0) or \
                (substitute and trySubstitutions(trySubstitutions, substitute, substitutions[1:]))
    return trySubstitutions(returnMatch, form, GET_INDEX_SUBSTITUTIONS)


MORPHOLOGICAL_SUBSTITUTIONS = {
    NOUN:
    [('s', ''),
     ('ses', 's'),
     ('ves', 'f'),
     ('xes', 'x'),
     ('zes', 'z'),
     ('ches', 'ch'),
     ('shes', 'sh'),
     ('men', 'man'),
     ('ies', 'y')],
    VERB:
    [('s', ''),
     ('ies', 'y'),
     ('es', 'e'),
     ('es', ''),
     ('ed', 'e'),
     ('ed', ''),
     ('ing', 'e'),
     ('ing', '')],
    ADJECTIVE:
    [('er', ''),
     ('est', ''),
     ('er', 'e'),
     ('est', 'e')],
    ADVERB: []}

def morphy(form, pos='noun', collect=0):
    """Recursively uninflect _form_, and return the first form found
    in the dictionary.  If _collect_ is true, a sequence of all forms
    is returned, instead of just the first one.
    
    >>> morphy('dogs')
    'dog'
    >>> morphy('churches')
    'church'
    >>> morphy('aardwolves')
    'aardwolf'
    >>> morphy('abaci')
    'abacus'
    >>> morphy('hardrock', 'adv')
    """
    from wordnet import _normalizePOS, _dictionaryFor
    pos = _normalizePOS(pos)
    fname = os.path.join(WNSEARCHDIR, {NOUN: 'noun', VERB: 'verb', ADJECTIVE: 'adj', ADVERB: 'adv'}[pos] + '.exc')
    excfile = open(fname)
    substitutions = MORPHOLOGICAL_SUBSTITUTIONS[pos]
    def trySubstitutions(trySubstitutions,	# workaround for lack of nested closures in Python < 2.1
                         form,		  	# reduced form
                         substitutions,		# remaining substitutions
                         lookup=1,
                         dictionary=_dictionaryFor(pos),
                         excfile=excfile,
                         collect=collect,
                         collection=[]):
        import string
        exceptions = binarySearchFile(excfile, form)
        if exceptions:
            form = exceptions[string.find(exceptions, ' ')+1:-1]
        if lookup and dictionary.has_key(form):
            if collect:
                collection.append(form)
            else:
                return form
        elif substitutions:
            old, new = substitutions[0]
            substitutions = substitutions[1:]
            substitute = None
            if endsWith(form, old):
                substitute = form[:-len(old)] + new
                #if dictionary.has_key(substitute):
                #   return substitute
            form =              trySubstitutions(trySubstitutions, form, substitutions) or \
                (substitute and trySubstitutions(trySubstitutions, substitute, substitutions))
            return (collect and collection) or form
        elif collect:
            return collection
    return trySubstitutions(trySubstitutions, form, substitutions)

#
# Testing
#
def _test(reset=0):
    import doctest, wntools
    if reset:
        doctest.master = None # This keeps doctest from complaining after a reload.
    return doctest.testmod(wntools)
