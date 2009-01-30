# Natural Language Toolkit: Wordnet Stemmer
#
# Copyright (C) 2001-2009 NLTK Project
# Author: Oliver Steele <steele@osteele.com>
#         Steven Bird <sb@csse.unimelb.edu.au>
#         David Ormiston Smith <daosmith@csse.unimelb.edu.au>
#         Jussi Salmela <jtsalmela@users.sourceforge.net>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

from itertools import islice

import nltk.data
from nltk.util import binary_search_file
from nltk import defaultdict

from dictionary import dictionaryFor
from util import *

MORPHOLOGICAL_SUBSTITUTIONS = {
    NOUN:
      [('s', ''),      ('ses', 's'),   ('ves', 'f'),
       ('xes', 'x'),   ('zes', 'z'),   ('ches', 'ch'),
       ('shes', 'sh'), ('men', 'man'), ('ies', 'y')],
    VERB:
      [('s', ''),      ('ies', 'y'),   ('es', 'e'),    ('es', ''),
       ('ed', 'e'),    ('ed', ''),     ('ing', 'e'),   ('ing', '')],
    ADJECTIVE:
      [('er', ''),     ('est', ''),    ('er', 'e'),    ('est', 'e')],
    ADVERB:
      []}

def morphy(form, pos=NOUN):
    '''Identify the base forms for a given word-form with a given POS.
    First it checks if the word is found in the exception list for this POS.
    If so, it identifies all the exception's base forms.
    Next it recurses with the word-form and a list of
    suffix substitutions for that POS.
    For every (old,new) pair of strings in the substitution list, if
    the form ends with old, a new form is created by replacing old with
    new and doing a recursive call.
    
    >>> morphy('dogs')
    'dog'
    >>> morphy('churches')
    'church'
    >>> morphy('aardwolves')
    'aardwolf'
    >>> morphy('abaci')
    'abacus'
    >>> morphy('hardrock', ADVERB)
    '''
    
    first = list(islice(_morphy(form, pos), 1))
    if len(first) == 1:
        return first[0]
    else:
        return None

def _morphy(form, pos=NOUN):
    pos = normalizePOS(pos)
    section = {NOUN: NOUN, VERB: VERB, ADJECTIVE: ADJECTIVE, ADVERB: ADVERB}[pos]
    excfile = open(nltk.data.find('corpora/wordnet/%s.exc' % section))
    substitutions = MORPHOLOGICAL_SUBSTITUTIONS[pos]
    dictionary=dictionaryFor(pos)
    collection=[]
    def trySubstitutions(form,                # reduced form
                         substitutions):      # remaining substitutions
        if dictionary.has_key(form):
            yield form
        for n,(old,new) in enumerate(substitutions):
            if form.endswith(old):
                new_form = form[:-len(old)] + new
                for f in trySubstitutions(new_form, substitutions[:n] +
                                                    substitutions[n+1:]):
                    yield f
            
    exceptions = binary_search_file(excfile, form)
    if exceptions:
        forms = exceptions[exceptions.find(' ')+1:-1].split()
        for f in forms:
            yield f
    if pos == NOUN and form.endswith('ful'):
        suffix = 'ful'
        form = form[:-3]
    else:
        suffix = ''
    for f in trySubstitutions(form, substitutions):
        yield f + suffix

# Demo

def p(word):
    word = word.lower()
    print '\n===================='
    print 'Word is', word
    print '===================='
    pos_forms = defaultdict(set)
    #          ['noun', 'verb', 'adj', 'adv']
    for pos in [NOUN, VERB, ADJECTIVE, ADVERB]:
        for form in _morphy(word, pos=pos):
            pos_forms[pos].add(form)
    for pos in [NOUN, VERB, ADJECTIVE, ADVERB]:
        if pos in pos_forms:
            print '%s: ' % pos.capitalize(),
            for f in pos_forms[pos]:
                print f,
            print
    print '===================='

def demo():
    for word in ['dogs', 'churches', 'aardwolves', 'abaci', 'hardrock']:
        p(word)
    while True:
        word = raw_input('Enter a word: ')
        if word == '': break
        p(word)

if __name__ == '__main__':
    demo()

__all__ = ['demo', 'morphy', '_morphy']
