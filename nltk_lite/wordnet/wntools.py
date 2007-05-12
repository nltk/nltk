# Natural Language Toolkit: Wordnet Interface: Tools
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Oliver Steele <steele@osteele.com>
#         David Ormiston Smith <daosmith@csse.unimelb.edu.au>>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

from pos import *
from nltk_lite.wordnet import *

#
# WordNet utilities
#

GET_INDEX_SUBSTITUTIONS = ((' ', '-'), ('-', ' '), ('-', ''), (' ', ''), ('.', ''))

def getIndex(form, pos=NOUN):
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
      [('s', ''),        ('ses', 's'),     ('ves', 'f'),     ('xes', 'x'),   ('zes', 'z'),
       ('ches', 'ch'),   ('shes', 'sh'),   ('men', 'man'),   ('ies', 'y')],
    VERB:
      [('s', ''),        ('ies', 'y'),     ('es', 'e'),      ('es', ''),
       ('ed', 'e'),      ('ed', ''),       ('ing', 'e'),     ('ing', '')],
    ADJECTIVE:
      [('er', ''),       ('est', ''),      ('er', 'e'),      ('est', 'e')],
    ADVERB:
      []}

def morphy(form, pos=NOUN, collect=0):
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
    >>> morphy('hardrock', ADVERB)
    """
    pos = normalizePOS(pos)
    fname = os.path.join(WNSEARCHDIR, {NOUN: NOUN, VERB: VERB, ADJECTIVE: ADJECTIVE, ADVERB: ADVERB}[pos] + '.exc')
    excfile = open(fname)
    substitutions = MORPHOLOGICAL_SUBSTITUTIONS[pos]
    def trySubstitutions(trySubstitutions,	# workaround for lack of nested closures in Python < 2.1
                         form,		  	# reduced form
                         substitutions,		# remaining substitutions
                         lookup=1,
                         dictionary=dictionaryFor(pos),
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
            if form.endswith(old):
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

if __name__ == '__main__':
    _test()
