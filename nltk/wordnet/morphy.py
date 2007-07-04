# Natural Language Toolkit: Wordnet Stemmer
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Oliver Steele <steele@osteele.com>
#         Steven Bird <sb@csse.unimelb.edu.au>
#         David Ormiston Smith <daosmith@csse.unimelb.edu.au>>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

from dictionary import dictionaryFor
from util import *

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
    section = {NOUN: NOUN, VERB: VERB, ADJECTIVE: ADJECTIVE, ADVERB: ADVERB}[pos]
    excfile = open(find_corpus_file('wordnet', section, extension=".exc"))
    substitutions = MORPHOLOGICAL_SUBSTITUTIONS[pos]
    def trySubstitutions(trySubstitutions,    # workaround for lack of nested closures in Python < 2.1
                         form,                # reduced form
                         substitutions,       # remaining substitutions
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

if __name__ == '__main__':
    from nltk.wordnet import morphy
    print 'dogs ->', morphy('dogs')
    print 'churches ->', morphy('churches')
    print 'aardwolves ->', morphy('aardwolves')
    print 'abaci ->', morphy('abaci')
    print 'hardrock ->', morphy('hardrock')
    
    
    
    

