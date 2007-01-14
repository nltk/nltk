# Natural Language Toolkit: Wordnet Interface: Part-of-speech Module
#
# Copyright (C) 2001-2006 University of Pennsylvania
# Author: Oliver Steele <steele@osteele.com>
#         David Ormiston Smith <daosmith@csse.unimelb.edu.au>>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

NOUN = 'noun'
VERB = 'verb'
ADJECTIVE = 'adj'
ADVERB = 'adv'

pos_abbrs = {NOUN: 'n.', VERB: 'v.', ADJECTIVE: 'adj.', ADVERB: 'adv.'}

_POSNormalizationTable = {}

for pos, abbreviations in (
    (NOUN, "noun n n."),
    (VERB, "verb v v."),
    (ADJECTIVE, "adjective adj adj. a s"),
    (ADVERB, "adverb adv adv. r")):
    tokens = abbreviations.split()

    for token in tokens:
        _POSNormalizationTable[token] = pos
        _POSNormalizationTable[token.upper()] = pos

def normalizePOS(pos):
    """
    Return the standard form of the supplied part of speech.

    @type  pos: C{string}
    @param pos: A (non-standard) part of speech string.
    @return: A standard form part of speech string.
    """
    try:
        norm = _POSNormalizationTable[pos]
    except KeyError:
        raise TypeError, `pos` + " is not a part of speech type"
    return norm


