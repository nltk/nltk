# Natural Language Toolkit: Tagger Utilities
#
# Copyright (C) 2001-2008 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT

import re

from nltk.internals import deprecated

def str2tuple(s, sep='/'):
    """
    Given the string representation of a tagged token, return the
    corresponding tuple representation.  The rightmost occurence of
    C{sep} in C{s} will be used to divide C{s} into a word string and
    a tag string.  If C{sep} does not occur in C{s}, return
    C{(s, None)}.

    @type s: C{str}
    @param s: The string representaiton of a tagged token.
    @type sep: C{str}
    @param sep: The separator string used to separate word strings
        from tags.
    """
    loc = s.rfind(sep)
    if loc >= 0:
        return (s[:loc], s[loc+1:].upper())
    else:
        return (s, None)

def tuple2str(tagged_token, sep='/'):
    """
    Given the tuple representation of a tagged token, return the
    corresponding string representation.  This representation is
    formed by concatenating the token's word string, followed by the
    separator, followed by the token's tag.  (If the tag is None,
    then just return the bare word string.)
    
    @type tagged_token: C{(str, str)}
    @param tagged_token: The tuple representation of a tagged token.
    @type sep: C{str}
    @param sep: The separator string used to separate word strings
        from tags.
    """
    word, tag = tagged_token
    if tag is None:
        return word
    else:
        assert sep not in tag, 'tag may not contain sep!'
        return '%s%s%s' % (word, sep, tag)

def untag(tagged_sentence):
    """
    Given a tagged sentence, return an untagged version of that
    sentence.  I.e., return a list containing the first element
    of each tuple in C{tagged_sentence}.

    >>> untag([('John', 'NNP'), ('saw', 'VBD'), ('Mary', 'NNP')]
    ['John', 'saw', 'mary']
    """
    return [w for (w, t) in tagged_sentence]

from nltk import evaluate
def accuracy(tagger, gold):
    """
    Score the accuracy of the tagger against the gold standard.
    Strip the tags from the gold standard text, retag it using
    the tagger, then compute the accuracy score.

    @type tagger: C{TaggerI}
    @param tagger: The tagger being evaluated.
    @type gold: C{list} of C{Token}
    @param gold: The list of tagged tokens to score the tagger on.
    @rtype: C{float}
    """
    tagged_sents = tagger.batch_tag([untag(sent) for sent in gold])
    gold_tokens = sum(gold, [])
    test_tokens = sum(tagged_sents, [])
    return evaluate.accuracy(gold_tokens, test_tokens)

######################################################################
#{ Mapping tags to simplified tags
######################################################################

# http://khnt.hit.uib.no/icame/manuals/brown/INDEX.HTM

def simplify_brown_tag(tag):
    tag = tag.lower()
    tag = re.sub(r'fw-',      '',   tag)  # foreign word
    tag = re.sub(r'-[th]l',   '',   tag)  # headlines, titles
    tag = re.sub(r'-nc',      '',   tag)  # cited
    tag = re.sub(r'ber?',     'vb', tag)  # verb "to be"
    tag = re.sub(r'hv',       'vb', tag)  # verb "to have"
    tag = re.sub(r'do',       'vb', tag)  # verb "to do"
    tag = re.sub(r'nc',       'nn', tag)  # cited word
    tag = re.sub(r'z',        '',   tag)  # third-person singular
    tag = re.sub(r'\bj[^-+]*', 'J', tag)  # adjectives
    tag = re.sub(r'\bp[^-+]*', 'PR', tag)  # pronouns
    tag = re.sub(r'\bm[^-+]*', 'M', tag)  # modals
    tag = re.sub(r'\bq[^-+]*', 'Q', tag)  # qualifiers
    tag = re.sub(r'\babl',     'Q', tag)  # qualifiers
    tag = re.sub(r'\bab[nx]',  'D', tag)  # determiners
    tag = re.sub(r'\bap',      'D', tag)  # determiners
    tag = re.sub(r'\bd[^-+]*', 'D', tag)  # determiners
    tag = re.sub(r'\bat',      'D', tag)  # determiners
    tag = re.sub(r'\bw[^-+]*', 'W', tag)  # wh words
    tag = re.sub(r'\br[^-+]*', 'R', tag)  # adverbs
    tag = re.sub(r'\bto',      'T', tag)  # "to"
    tag = re.sub(r'\bc[cs]',   'C', tag)  # conjunctions
    tag = re.sub(r's',         '',  tag)  # plurals
    tag = re.sub(r'\bin',      'P', tag)  # prepositions
    tag = re.sub(r'\buh',      'U', tag)  # interjections (uh)
    tag = re.sub(r'\bex',      'E', tag)  # existential "there"
    tag = re.sub(r'\bvbn',     'VN', tag) # past participle
    tag = re.sub(r'\bvbd',     'VD', tag) # past tense
    tag = re.sub(r'\bvbg',     'VG', tag) # gerund
    tag = re.sub(r'\bvb',      'V', tag)  # verb
    tag = re.sub(r'\bnn',      'N', tag)  # noun
    tag = re.sub(r'\bnp',      'NP', tag) # proper noun
    tag = re.sub(r'\bnr',      'NR', tag) # adverbial noun
    tag = re.sub(r'\bex',      'E', tag)  # existential "there"
    tag = re.sub(r'\bod',      'OD', tag) # ordinal
    tag = re.sub(r'\bcd',      'CD', tag) # cardinal
    tag = re.sub(r'-t',        '', tag)   # misc
    tag = re.sub(r'[a-z\*]',   '', tag)   # misc
    return tag

# Wall Street Journal tags (Penn Treebank)

wsj_mapping = {
    '-lrb-': 'B',   '-rrb-': 'B',    '-lsb-': 'B',
    '-rsb-': 'B',   '-lcb-': 'B',    '-rcb-': 'B',
    '-none-': '',   'cc': 'CC',      'cd': 'CD',
    'dt': 'D',      'ex': 'X',       'fw': 'F', # existential "there", foreign word
    'in': 'P',      'jj': 'J',       'jjr': 'J',
    'jjs': 'J',     'ls': 'L',       'md': 'M',  # list item marker
    'nn': 'N',      'nnp': 'NP',     'nnps': 'NP',
    'nns': 'N',     'pdt': 'D',      'pos': '',
    'prp': 'PR',    'prp$': 'PR',    'rb': 'R',
    'rbr': 'R',     'rbs': 'R',      'rp': 'P',
    'sym': 'S',     'to': 'TO',      'uh': 'UH',
    'vb': 'V',      'vbd': 'VD',     'vbg': 'VG',
    'vbn': 'VN',    'vbp': 'V',      'vbz': 'V',
    'wdt': 'W',     'wp': 'W',       'wp$': 'W',
    'wrb': 'W'
    }


def simplify_wsj_tag(tag):
    try:
        tag = wsj_mapping[tag.lower()]
    except KeyError:
        pass
    return tag

######################################################################
#{ Deprecated
######################################################################
@deprecated("Use nltk.tag.str2tuple(s, sep) instead.")
def tag2tuple(s, sep='/'):
    return str2tuple(s, sep)

@deprecated("Use [nltk.tag.str2tuple(t, sep) for t in s.split()] instead.")
def string2tags(s, sep='/'):
    return [str2tuple(t, sep) for t in s.split()]

@deprecated("Use ' '.join(nltk.tag.tuple2str(w, sep) for w in t) instead.")
def tags2string(t, sep='/'):
    return ' '.join(tuple2str(w, sep) for w in t)

@deprecated("Use [nltk.tag.str2tuple(t, sep)[0] for t in s.split()] instead.")
def string2words(s, sep='/'):
    return [str2tuple(t, sep)[0] for t in s.split()]


